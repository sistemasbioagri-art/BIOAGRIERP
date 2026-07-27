/** @odoo-module **/

import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

const originalFormatMonetary = TaxTotalsComponent.prototype.formatMonetary;

patch(TaxTotalsComponent.prototype, {
    formatMonetary(value) {
        const formatted = originalFormatMonetary.call(this, value);
        
        let currencyName = '';
        
        // 1. Intentar obtener de session.currencies (más confiable)
        if (session.currencies && this.totals && this.totals.currency_id) {
            const currency = session.currencies[this.totals.currency_id];
            if (currency && currency.name) {
                currencyName = currency.name;
            }
        }
        
        // 2. Fallback: obtener del record (Many2one [id, name])
        if (!currencyName && this.props && this.props.record && this.props.record.data) {
            const currencyField = this.props.record.data.currency_id;
            if (Array.isArray(currencyField) && currencyField.length >= 2) {
                currencyName = currencyField[1];
            }
        }
        
        if (currencyName) {
            return formatted + ' ' + currencyName;
        }
        return formatted;
    }
});
