/** @odoo-module **/

import { publicWidget } from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const CHUNK_LINES = 50000;

publicWidget.Widget.PadronUploader = publicWidget.Widget.extend({
    selector: '.o_padron_upload_area',
    events: {
        'change .o_padron_file_input input[type="file"]': '_onFileChange',
    },

    init() {
        this._super(...arguments);
        this._chunks = [];
        this._currentChunk = 0;
        this._totalChunks = 0;
        this._importId = null;
        this._tipo = 'percepcion';
        this._filename = '';
    },

    start() {
        this.$progressContainer = this.$('.o_padron_progress');
        this.$progressBar = this.$progressContainer.find('.progress-bar');
        this.$progressText = this.$progressContainer.find('.o_padron_progress_text');
        return this._super();
    },

    _onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        this._filename = file.name;
        this._tipo = this.$('select[name="tipo"]').val() || 'percepcion';

        this.$progressContainer.removeClass('d-none');
        this.$progressBar.css('width', '0%').attr('aria-valuenow', 0);
        this.$progressText.text(_t('Leyendo archivo...'));

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const lines = text.split('\n');
            this._chunks = [];
            for (let i = 0; i < lines.length; i += CHUNK_LINES) {
                this._chunks.push(lines.slice(i, i + CHUNK_LINES).join('\n'));
            }
            this._totalChunks = this._chunks.length;
            this._currentChunk = 0;
            this.$progressText.text(
                _t('Archivo leido: %(total)s lineas, %(chunks)s partes. Iniciando subida...', {
                    total: lines.length.toLocaleString(),
                    chunks: this._totalChunks,
                })
            );
            this._uploadNextChunk();
        };
        reader.readAsText(file, 'UTF-8');
    },

    async _uploadNextChunk() {
        if (this._currentChunk >= this._totalChunks) {
            this.$progressBar.css('width', '100%').attr('aria-valuenow', 100);
            this.$progressText.text(_t('Importacion completada. Abriendo resultado...'));
            setTimeout(() => {
                window.location.href = '/odoo/action-arba_padron_import/' + this._importId;
            }, 1500);
            return;
        }

        const pct = Math.round(((this._currentChunk + 1) / this._totalChunks) * 100);
        this.$progressBar.css('width', pct + '%').attr('aria-valuenow', pct);
        this.$progressText.text(
            _t('Procesando... %(pct)s%%', { pct: pct })
        );

        const chunkText = this._chunks[this._currentChunk];

        if (!this._importId) {
            try {
                const initResult = await rpc('/padron/import/init', {
                    filename: this._filename,
                    tipo: this._tipo,
                    total_chunks: this._totalChunks,
                });
                this._importId = initResult.import_id;
            } catch (e) {
                this.$progressText.text(_t('Error al crear registro: ') + e.message);
                return;
            }
        }

        try {
            await rpc('/padron/import/chunk', {
                import_id: this._importId,
                chunk_text: chunkText,
                tipo: this._tipo,
            });
        } catch (e) {
            this.$progressText.text(_t('Error en chunk %(n)s: ', { n: this._currentChunk + 1 }) + e.message);
            return;
        }

        this._currentChunk++;
        this._uploadNextChunk();
    },
});

export default publicWidget.Widget.PadronUploader;
