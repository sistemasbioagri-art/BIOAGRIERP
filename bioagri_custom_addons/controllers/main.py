import logging
import re

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

UPLOAD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Importar Padron ARBA</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f4f6f8; margin: 0; padding: 40px 20px; color: #333; }
  .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px;
               box-shadow: 0 2px 12px rgba(0,0,0,.08); padding: 30px; }
  h2 { margin: 0 0 24px; font-size: 20px; }
  label { display: block; font-weight: 600; margin-bottom: 6px; font-size: 14px; }
  select, input[type=file] { width: 100%; padding: 8px 12px; border: 1px solid #ccc;
                              border-radius: 4px; font-size: 14px; box-sizing: border-box; }
  select { margin-bottom: 16px; }
  input[type=file] { margin-bottom: 20px; }
  .progress-wrap { display: none; margin-top: 16px; }
  .progress { background: #e9ecef; border-radius: 6px; height: 28px; overflow: hidden; }
  .progress-bar { background: #2E7D32; height: 100%; width: 0; transition: width .3s;
                  display: flex; align-items: center; justify-content: center;
                  color: #fff; font-size: 13px; font-weight: 600; }
  .msg { margin-top: 12px; font-size: 13px; color: #555; min-height: 20px; }
  .done { color: #2E7D32; font-weight: 600; }
  .error { color: #c62828; font-weight: 600; }
  .btn { display: inline-block; padding: 8px 20px; background: #2E7D32; color: #fff;
         border: none; border-radius: 4px; cursor: pointer; font-size: 14px;
         text-decoration: none; margin-top: 8px; }
  .btn:disabled { opacity: .5; cursor: not-allowed; }
  .back { display: inline-block; margin-top: 20px; color: #666; text-decoration: none; font-size: 13px; }
  .back:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="container">
  <h2>Importar Padron ARBA</h2>
  <label for="tipo">Tipo de Padron</label>
  <select id="tipo">
    <option value="percepcion">Percepcion (PadronRGSPer*.txt)</option>
    <option value="retencion">Retencion (PadronRGSRet*.txt)</option>
  </select>
  <label for="file">Archivo .txt del Padron</label>
  <input type="file" id="file" accept=".txt,.TXT">
  <div class="progress-wrap" id="progressWrap">
    <div class="progress"><div class="progress-bar" id="progressBar">0%</div></div>
    <div class="msg" id="msg"></div>
  </div>
</div>
<a class="back" href="/odoo">&laquo; Volver a Odoo</a>
<script>
(function() {
  var CHUNK_LINES = 50000;
  var fileInput = document.getElementById('file');
  var tipoSelect = document.getElementById('tipo');
  var progressWrap = document.getElementById('progressWrap');
  var progressBar = document.getElementById('progressBar');
  var msgEl = document.getElementById('msg');

  fileInput.addEventListener('change', function() {
    var file = fileInput.files[0];
    if (!file) return;
    var tipo = tipoSelect.value;
    progressWrap.style.display = 'block';
    setProgress(0, 'Leyendo archivo...');
    var reader = new FileReader();
    reader.onload = function(e) {
      var lines = e.target.result.split('\\n');
      var chunks = [];
      for (var i = 0; i < lines.length; i += CHUNK_LINES) {
        chunks.push(lines.slice(i, i + CHUNK_LINES).join('\\n'));
      }
      setProgress(0, 'Archivo: ' + lines.length.toLocaleString() + ' lineas, ' + chunks.length + ' partes. Iniciando...');
      uploadChunks(chunks, tipo, file.name, 0, null, lines.length);
    };
    reader.readAsText(file, 'UTF-8');
  });

  function setProgress(pct, text) {
    progressBar.style.width = pct + '%';
    progressBar.textContent = pct + '%';
    if (text) msgEl.textContent = text;
  }

  function uploadChunks(chunks, tipo, filename, idx, importId, totalLines) {
    if (idx >= chunks.length) {
      setProgress(100, 'Importacion completada.');
      msgEl.className = 'msg done';
      fileInput.disabled = true;
      tipoSelect.disabled = true;
      setTimeout(function() {
        window.location.href = '/odoo/action-arba_padron_import/' + importId;
      }, 1500);
      return;
    }
    var pct = Math.round(((idx + 1) / chunks.length) * 100);
    setProgress(pct, 'Procesando parte ' + (idx + 1) + ' de ' + chunks.length + '...');
    if (!importId) {
      rpcCall('/padron/import/init', {filename: filename, tipo: tipo, total_chunks: chunks.length}, function(res) {
        importId = res.import_id;
        sendChunk(chunks, tipo, filename, idx, importId, totalLines);
      }, function(err) {
        setProgress(0, 'Error: ' + err);
        msgEl.className = 'msg error';
      });
    } else {
      sendChunk(chunks, tipo, filename, idx, importId, totalLines);
    }
  }

  function sendChunk(chunks, tipo, filename, idx, importId, totalLines) {
    rpcCall('/padron/import/chunk', {import_id: importId, chunk_text: chunks[idx], tipo: tipo}, function(res) {
      uploadChunks(chunks, tipo, filename, idx + 1, importId, totalLines);
    }, function(err) {
      setProgress(0, 'Error en parte ' + (idx + 1) + ': ' + err);
      msgEl.className = 'msg error';
    });
  }

  function rpcCall(url, params, onSuccess, onError) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
      if (xhr.status === 200) {
        try {
          var result = JSON.parse(xhr.responseText);
          if (result.error) { onError(result.error); }
          else { onSuccess(result); }
        } catch(e) { onError(e.message); }
      } else if (xhr.status === 302 || xhr.responseURL) {
        window.location.href = '/web/login';
      } else {
        onError('HTTP ' + xhr.status);
      }
    };
    xhr.onerror = function() { onError('Network error'); };
    var odooCsrf = document.cookie.match(/session_id=([^;]+)/);
    var payload = JSON.stringify({jsonrpc: '2.0', method: 'call', id: Date.now(), params: params});
    xhr.send(payload);
  }
})();
</script>
</body>
</html>"""


class PadronImportController(http.Controller):

    @http.route('/padron/upload', type='http', auth='user', methods=['GET'])
    def padron_upload_page(self, **kw):
        return request.make_response(UPLOAD_HTML, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
        ])

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
        details = []

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
                details.append((cuit, pid, data['alicuota_nueva'], old_val))
            if len(updates) >= 5000:
                _flush_updates(request.env.cr, field, updates)
                updated += len(updates)
                updates = []

        if updates:
            _flush_updates(request.env.cr, field, updates)
            updated += len(updates)

        if import_id and details:
            for cuit, pid, val, old in details:
                request.env.cr.execute(
                    "INSERT INTO arba_padron_line (import_id, cuit, partner_id, alicuota_anterior, alicuota_nueva, updated) "
                    "VALUES (%s, %s, %s, %s, %s, true)",
                    (import_id, cuit, pid, old, val),
                )

        if import_id:
            request.env.cr.execute(
                "UPDATE arba_padron_import SET count_total = count_total + %s, "
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
