from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_amount_total_ars = fields.Monetary(string='Total en ARS', compute='_compute_amount_total_ars', currency_field='company_id.currency_id')
    x_currency_rate = fields.Float(string='Tipo de cambio', compute='_compute_amount_total_ars', digits=(12, 4))

    @api.depends('amount_total', 'currency_id', 'company_id.currency_id', 'date_order')
    def _compute_amount_total_ars(self):
        for order in self:
            if order.currency_id == order.company_id.currency_id:
                order.x_amount_total_ars = order.amount_total
                order.x_currency_rate = 1.0
            else:
                # ponytail: uses Odoo's built-in rate conversion
                rate = order.currency_id._get_conversion_rate(
                    order.currency_id, 
                    order.company_id.currency_id, 
                    order.company_id, 
                    order.date_order or fields.Date.today()
                )
                order.x_currency_rate = rate
                order.x_amount_total_ars = order.currency_id.round(order.amount_total * rate)

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            if not order.picking_ids:
                order._create_picking()
        return res
