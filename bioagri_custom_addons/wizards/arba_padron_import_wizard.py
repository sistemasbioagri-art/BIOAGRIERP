import base64
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ArbaPadronImportWizard(models.TransientModel):
    _name = 'arba.padron.import.wizard'
    _description = 'Asistente de Importación de Padrón ARBA'

    archivo = fields.Binary('Archivo .txt del Padrón', required=True)
    filename = fields.Char('Nombre del archivo')
    tipo = fields.Selection([
        ('percepcion', 'Percepción (PadronRGSPer*.txt)'),
        ('retencion', 'Retención (PadronRGSRet*.txt)'),
    ], string='Tipo de Padrón', required=True,
        default='percepcion',
        help='Seleccione el tipo según el archivo descargado de ARBA.')
    separador = fields.Selection([
        ('auto', 'Auto-detectar'),
        ('punto_coma', 'Punto y coma (;)'),
        ('posicional', 'Posicional (ancho fijo)'),
    ], string='Formato', default='auto',
        help='Formato del archivo. ARBA usa punto y coma o posicional.')

    def action_import(self):
        self.ensure_one()
        if not self.archivo:
            raise UserError(_('Debe seleccionar un archivo.'))

        raw = base64.b64decode(self.archivo)
        content = self._decode(raw)
        lines = content.strip().split('\n')

        partners = self._parse_lines(lines)
        stats = self._update_partners(partners)

        import_record = self.env['arba.padron.import'].create({
            'name': self.filename or 'import_{}'.format(fields.Datetime.now()),
            'tipo': self.tipo,
            'fecha_vigencia': fields.Date.today(),
        })
        for p in partners:
            self.env['arba.padron.line'].create({
                'import_id': import_record.id,
                'cuit': p['cuit'],
                'partner_id': p.get('partner_id'),
                'alicuota_anterior': p.get('alicuota_anterior', 0),
                'alicuota_nueva': p.get('alicuota_nueva', 0),
                'updated': p.get('updated', False),
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'arba.padron.import',
            'res_id': import_record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _decode(self, raw):
        for enc in ('utf-8', 'latin-1', 'windows-1252'):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return raw.decode('utf-8', errors='replace')

    def _parse_lines(self, lines):
        partners = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            data = self._parse_line(line)
            if data:
                partners.append(data)
        return partners

    def _parse_line(self, line):
        # ponytail: soporta formato punto y coma o posicional
        # add when: ARBA cambie el diseño del padrón
        fields_map = self._try_semicolon(line)
        if not fields_map:
            fields_map = self._try_positional(line)
        if not fields_map:
            return None

        cuit = fields_map.get('cuit', '')
        cuit = re.sub(r'[^0-9]', '', cuit)
        if not cuit.startswith('0'):
            cuit = cuit.zfill(11)
        if len(cuit) != 11:
            return None

        alicuota_str = fields_map.get('alicuota', '0')
        try:
            alicuota = float(alicuota_str.replace(',', '.'))
        except (ValueError, TypeError):
            alicuota = 0.0

        return {
            'cuit': cuit,
            'alicuota_nueva': alicuota,
        }

    def _try_semicolon(self, line):
        parts = line.split(';')
        if len(parts) < 5:
            return None
        # formato típico: fecha;fecha;fecha;cuit;tipo;marca;marca;alicuota;...
        # la alícuota suele estar en la posición 7 u 8 (0-indexed)
        alicuota = None
        cuit = None
        for i, part in enumerate(parts):
            part = part.strip()
            if re.match(r'^\d{11}$', part):
                cuit = part
            elif re.match(r'^\d{1,3}[,\.]\d{1,2}$', part):
                alicuota = part
        if cuit and alicuota:
            return {'cuit': cuit, 'alicuota': alicuota}
        # fallback: buscar por posición conocida
        if len(parts) >= 8:
            cuit_candidate = parts[3].strip()
            alicuota_candidate = parts[7].strip()
            if re.match(r'^\d{11}$', cuit_candidate) and re.match(r'^[\d\.,]+$', alicuota_candidate):
                return {'cuit': cuit_candidate, 'alicuota': alicuota_candidate}
        return None

    def _try_positional(self, line):
        # ponytail: formato posicional estándar ARBA
        # add when: ARBA publique un nuevo diseño de registro
        if len(line) < 50:
            return None
        try:
            cuit = line[27:38].strip() if len(line) >= 38 else ''
            alicuota = line[45:49].strip() if len(line) >= 49 else '0'
            if not re.match(r'^\d{11}$', cuit):
                return None
            return {'cuit': cuit, 'alicuota': alicuota}
        except (IndexError, ValueError):
            return None

    def _update_partners(self, partners):
        for p in partners:
            partner = self.env['res.partner'].search([
                ('vat', '=', p['cuit']),
            ], limit=1)
            if not partner:
                partner = self.env['res.partner'].search([
                    ('vat', 'ilike', p['cuit']),
                ], limit=1)
            p['partner_id'] = partner.id if partner else False
            if not partner:
                p['updated'] = False
                continue
            if self.tipo == 'percepcion':
                old = partner.x_alicuota_percepcion
                partner.write({'x_alicuota_percepcion': p['alicuota_nueva']})
            else:
                old = partner.x_alicuota_retencion
                partner.write({'x_alicuota_retencion': p['alicuota_nueva']})
            p['alicuota_anterior'] = old
            p['updated'] = True
        return partners
