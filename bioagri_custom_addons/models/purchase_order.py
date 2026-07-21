import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Moneda de la empresa', readonly=True)
    x_amount_total_ars = fields.Monetary(
        string='Total en ARS',
        compute='_compute_amount_total_ars',
        currency_field='company_currency_id',
        store=True,
    )
    x_currency_rate = fields.Float(
        string='Tipo de cambio',
        compute='_compute_amount_total_ars',
        digits=(12, 4),
        store=True,
    )

    @api.depends('amount_total', 'currency_id', 'company_id.currency_id', 'date_order')
    def _compute_amount_total_ars(self):
        for order in self:
            if order.currency_id == order.company_id.currency_id:
                order.x_amount_total_ars = order.amount_total
                order.x_currency_rate = 1.0
                _logger.info('PO %s: same currency %s, rate=1.0', order.name, order.currency_id.name)
            else:
                # ponytail: manual rate calculation
                # Odoo stores rate as: 1 base_currency = rate foreign_currency
                # Example: rate=0.000677 means 1 ARS = 0.000677 USD
                # So 1 USD = 1/0.000677 = 1477.50 ARS
                # To convert: amount / rate
                raw_rate = order.currency_id.rate
                _logger.info('PO %s: raw_rate=%s, currency=%s, base=%s',
                             order.name, raw_rate, order.currency_id.name, order.company_id.currency_id.name)
                
                if raw_rate and raw_rate > 0:
                    # rate_for_display = how many ARS per 1 USD
                    rate_for_display = 1.0 / raw_rate
                    ars_amount = order.amount_total / raw_rate
                    order.x_currency_rate = rate_for_display
                    order.x_amount_total_ars = ars_amount
                    _logger.info('PO %s: rate_display=%s, ars_amount=%s',
                                 order.name, rate_for_display, ars_amount)
                else:
                    _logger.warning('PO %s: no rate found!', order.name)
                    order.x_currency_rate = 1.0
                    order.x_amount_total_ars = order.amount_total

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            if not order.picking_ids:
                order._create_picking()
        return res
