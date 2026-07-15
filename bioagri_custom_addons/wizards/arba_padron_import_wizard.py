import base64
import logging
import re

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ArbaPadronImportWizard(models.TransientModel):
    _name = 'arba.padron.import.wizard'
    _description = 'Asistente de Importacion de Padron ARBA'

    archivo = fields.Binary('Archivo .txt del Padron', required=True)
    filename = fields.Char('Nombre del archivo')
    tipo = fields.Selection([
        ('percepcion', 'Percepcion (PadronRGSPer*.txt)'),
        ('retencion', 'Retencion (PadronRGSRet*.txt)'),
    ], string='Tipo de Padron', required=True, default='percepcion')
    separador = fields.Selection([
        ('auto', 'Auto-detectar'),
        ('punto_coma', 'Punto y coma (;)'),
        ('posicional', 'Posicional (ancho fijo)'),
    ], string='Formato', default='auto')

    def action_import(self):
        self.ensure_one()
        if not self.archivo:
            raise UserError(_('Debe seleccionar un archivo.'))

        raw = base64.b64decode(self.archivo)
        content = self._decode(raw)

        field = 'x_alicuota_percepcion' if self.tipo == 'percepcion' else 'x_alicuota_retencion'

        self.env.cr.execute(
            "SELECT id, vat FROM res_partner WHERE vat IS NOT NULL AND vat != ''"
        )
        vat_map = {}
        for pid, vat in self.env.cr.fetchall():
            clean = re.sub(r'[^0-9]', '', vat or '')
            if len(clean) == 11:
                vat_map[clean] = pid

        total = 0
        found = 0
        updated = 0
        updates = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            total += 1
            data = self._parse_line(line)
            if not data:
                continue
            cuit = data['cuit']
            pid = vat_map.get(cuit)
            if pid:
                found += 1
                updates.append((data['alicuota_nueva'], pid))
            if len(updates) >= 5000:
                self._flush_updates(field, updates)
                updated += len(updates)
                updates = []

        if updates:
            self._flush_updates(field, updates)
            updated += len(updates)

        import_record = self.env['arba.padron.import'].create({
            'name': self.filename or 'import_{}'.format(fields.Datetime.now()),
            'tipo': self.tipo,
            'fecha_vigencia': fields.Date.today(),
        })

        _logger.info(
            'PADRON IMPORT: total=%d found=%d updated=%d',
            total, found, updated,
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'arba.padron.import',
            'res_id': import_record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _flush_updates(self, field, updates):
        for val, pid in updates:
            self.env.cr.execute(
                "UPDATE res_partner SET %s = %%s WHERE id = %%s" % field,
                (val, pid),
            )

    def _decode(self, raw):
        for enc in ('utf-8', 'latin-1', 'windows-1252'):
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return raw.decode('utf-8', errors='replace')

    def _parse_line(self, line):
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

        return {'cuit': cuit, 'alicuota_nueva': alicuota}

    def _try_semicolon(self, line):
        parts = line.split(';')
        if len(parts) < 5:
            return None
        alicuota = None
        cuit = None
        for part in parts:
            part = part.strip()
            if re.match(r'^\d{11}$', part):
                cuit = part
            elif re.match(r'^\d{1,3}[,\.]\d{1,2}$', part):
                alicuota = part
        if cuit and alicuota:
            return {'cuit': cuit, 'alicuota': alicuota}
        if len(parts) >= 8:
            cuit_candidate = parts[3].strip()
            alicuota_candidate = parts[7].strip()
            if re.match(r'^\d{11}$', cuit_candidate) and re.match(r'^[\d\.,]+$', alicuota_candidate):
                return {'cuit': cuit_candidate, 'alicuota': alicuota_candidate}
        return None

    def _try_positional(self, line):
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
