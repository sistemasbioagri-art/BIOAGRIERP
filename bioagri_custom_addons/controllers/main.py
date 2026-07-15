import logging
import re

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PadronImportController(http.Controller):

    @http.route('/padron/import/init', type='json', auth='user', methods=['POST'])
    def padron_import_init(self, filename='', tipo='percepcion', total_chunks=0, **kw):
        import_record = request.env['arba.padron.import'].sudo().create({
            'name': filename or 'import_{}'.format(fields.Datetime.now()),
            'tipo': tipo,
            'fecha_vigencia': fields.Date.today(),
            'count_total': 0,
            'count_updated': 0,
        })
        return {'import_id': import_record.id}

    @http.route('/padron/import/chunk', type='json', auth='user', methods=['POST'])
    def padron_import_chunk(self, import_id=0, chunk_text='', tipo='percepcion', **kw):
        field = 'x_alicuota_percepcion' if tipo == 'percepcion' else 'x_alicuota_retencion'

        if not chunk_text:
            return {'error': 'empty chunk'}

        request.env.cr.execute(
            "SELECT id, vat FROM res_partner WHERE vat IS NOT NULL AND vat != ''"
        )
        vat_map = {}
        for pid, vat in request.env.cr.fetchall():
            clean = re.sub(r'[^0-9]', '', vat or '')
            if len(clean) == 11:
                vat_map[clean] = pid

        total = 0
        found = 0
        updated = 0
        updates = []

        for line in chunk_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            total += 1
            data = _parse_line(line)
            if not data:
                continue
            cuit = data['cuit']
            pid = vat_map.get(cuit)
            if pid:
                found += 1
                request.env.cr.execute(
                    "SELECT %s FROM res_partner WHERE id = %s" % (field, '%s'),
                    (pid,),
                )
                old_row = request.env.cr.fetchone()
                old_val = old_row[0] if old_row else 0.0
                updates.append((data['alicuota_nueva'], pid))
            if len(updates) >= 5000:
                _flush_updates(request.env.cr, field, updates)
                updated += len(updates)
                updates = []

        if updates:
            _flush_updates(request.env.cr, field, updates)
            updated += len(updates)

        if import_id:
            request.env.cr.execute(
                "UPDATE arba.padron_import SET count_total = count_total + %s, "
                "count_updated = count_updated + %s WHERE id = %s",
                (total, updated, import_id),
            )

        _logger.info('PADRON CHUNK: import_id=%s total=%d found=%d updated=%d', import_id, total, found, updated)

        return {'total': total, 'found': found, 'updated': updated}


def _flush_updates(cr, field, updates):
    for val, pid in updates:
        cr.execute(
            "UPDATE res_partner SET %s = %%s WHERE id = %%s" % field,
            (val, pid),
        )


def _parse_line(line):
    parts = line.split(';')
    if len(parts) >= 5:
        alicuota = None
        cuit = None
        for part in parts:
            part = part.strip()
            if re.match(r'^\d{11}$', part):
                cuit = part
            elif re.match(r'^\d{1,3}[,\.]\d{1,2}$', part):
                alicuota = part
        if cuit and alicuota:
            try:
                return {'cuit': cuit, 'alicuota_nueva': float(alicuota.replace(',', '.'))}
            except (ValueError, TypeError):
                pass
        if len(parts) >= 8:
            cuit_candidate = parts[3].strip()
            alicuota_candidate = parts[7].strip()
            if re.match(r'^\d{11}$', cuit_candidate) and re.match(r'^[\d\.,]+$', alicuota_candidate):
                try:
                    return {'cuit': cuit_candidate, 'alicuota_nueva': float(alicuota_candidate.replace(',', '.'))}
                except (ValueError, TypeError):
                    pass
    if len(line) >= 50:
        try:
            cuit = line[27:38].strip()
            alicuota = line[45:49].strip()
            if re.match(r'^\d{11}$', cuit):
                return {'cuit': cuit, 'alicuota_nueva': float(alicuota.replace(',', '.'))}
        except (IndexError, ValueError):
            pass
    return None
