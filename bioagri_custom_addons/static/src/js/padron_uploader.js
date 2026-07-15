/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const CHUNK_LINES = 50000;

class PadronUploadAction extends Component {
    setup() {
        this.action = useService("action");
        this.state = useState({
            uploading: false,
            progress: 0,
            message: "",
            done: false,
            error: false,
            importId: null,
        });
    }

    onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const tipoEl = document.querySelector('#padron_tipo');
        const tipo = tipoEl ? tipoEl.value : 'percepcion';

        this.state.uploading = true;
        this.state.progress = 0;
        this.state.done = false;
        this.state.error = false;
        this.state.importId = null;
        this.state.message = 'Leyendo archivo...';

        const reader = new FileReader();
        reader.onload = () => this._processFile(reader.result, file.name, tipo);
        reader.onerror = () => {
            this.state.message = 'Error al leer el archivo.';
            this.state.error = true;
            this.state.uploading = false;
        };
        reader.readAsText(file, 'UTF-8');
    }

    async _processFile(text, filename, tipo) {
        const lines = text.split('\n');
        const chunks = [];
        for (let i = 0; i < lines.length; i += CHUNK_LINES) {
            chunks.push(lines.slice(i, i + CHUNK_LINES).join('\n'));
        }

        this.state.message = `Archivo: ${lines.length.toLocaleString()} lineas, ${chunks.length} partes. Iniciando...`;

        let importId = null;

        for (let i = 0; i < chunks.length; i++) {
            const pct = Math.round(((i + 1) / chunks.length) * 100);
            this.state.progress = pct;
            this.state.message = `Procesando parte ${i + 1} de ${chunks.length}...`;

            if (!importId) {
                try {
                    const res = await this._rpc("/padron/import/init", {
                        filename: filename,
                        tipo: tipo,
                        total_chunks: chunks.length,
                    });
                    if (res && res.import_id) {
                        importId = res.import_id;
                        this.state.importId = importId;
                    } else {
                        throw new Error('No se pudo crear el registro de importacion.');
                    }
                } catch (e) {
                    this.state.message = 'Error al iniciar: ' + (e.data?.message || e.message || String(e));
                    this.state.error = true;
                    this.state.uploading = false;
                    return;
                }
            }

            try {
                const res = await this._rpc("/padron/import/chunk", {
                    import_id: importId,
                    chunk_text: chunks[i],
                    tipo: tipo,
                });
                if (res && res.error) {
                    throw new Error(res.error);
                }
            } catch (e) {
                this.state.message = `Error en parte ${i + 1}: ` + (e.data?.message || e.message || String(e));
                this.state.error = true;
                this.state.uploading = false;
                return;
            }
        }

        this.state.progress = 100;
        this.state.message = 'Importacion completada.';
        this.state.done = true;
        this.state.uploading = false;
    }

    _rpc(url, params) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = function () {
                if (xhr.status === 200) {
                    try {
                        const result = JSON.parse(xhr.responseText);
                        if (result.error) {
                            reject(new Error(result.error.data?.message || result.error));
                        } else {
                            resolve(result.result || result);
                        }
                    } catch (e) {
                        reject(e);
                    }
                } else if (xhr.status === 302) {
                    window.location.href = '/web/login';
                    reject(new Error('Sesion expirada'));
                } else {
                    reject(new Error('HTTP ' + xhr.status));
                }
            };
            xhr.onerror = function () {
                reject(new Error('Error de red'));
            };
            xhr.send(JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                id: Date.now(),
                params: params,
            }));
        });
    }

    onViewResult() {
        if (!this.state.importId) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'arba.padron.import',
            res_id: this.state.importId,
            views: [[false, 'form']],
            target: 'current',
        });
    }
}

PadronUploadAction.template = "bioagri_custom_addons.PadronUploadAction";

registry.category("actions").add("padron_upload_action", PadronUploadAction);
