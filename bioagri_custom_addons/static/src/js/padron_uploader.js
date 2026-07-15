/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

const CHUNK_LINES = 50000;

class PadronUploader extends Component {
    setup() {
        this.state = useState({
            uploading: false,
            progress: 0,
            message: "",
            done: false,
            importId: null,
        });
        this.fileInput = useRef("fileInput");
    }

    onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        const tipoEl = document.querySelector('select[name="tipo"]');
        const tipo = tipoEl ? tipoEl.value : 'percepcion';

        this.state.uploading = true;
        this.state.progress = 0;
        this.state.done = false;
        this.state.importId = null;
        this.state.message = 'Leyendo archivo...';

        const reader = new FileReader();
        reader.onload = () => this._processFile(reader.result, file.name, tipo);
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
                    const res = await rpc("/padron/import/init", {
                        filename: filename,
                        tipo: tipo,
                        total_chunks: chunks.length,
                    });
                    importId = res.import_id;
                    this.state.importId = importId;
                } catch (e) {
                    this.state.message = 'Error: ' + (e.message || e);
                    this.state.uploading = false;
                    return;
                }
            }

            try {
                await rpc("/padron/import/chunk", {
                    import_id: importId,
                    chunk_text: chunks[i],
                    tipo: tipo,
                });
            } catch (e) {
                this.state.message = `Error en parte ${i + 1}: ` + (e.message || e);
                this.state.uploading = false;
                return;
            }
        }

        this.state.progress = 100;
        this.state.message = 'Importacion completada.';
        this.state.done = true;
        this.state.uploading = false;
    }
}

PadronUploader.template = "bioagri_custom_addons.PadronUploader";

registry.category("fields").add("padron_uploader", PadronUploader);
