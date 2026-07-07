from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _post_confirm(self):
        res = super()._post_confirm()
        for order in self:
            if order.incoterm_id and order.incoterm_id.code in ('FOB', 'CIF'):
                self._create_draft_landed_cost(order)
        return res

    def _create_draft_landed_cost(self, order):
        stock_landed_cost = self.env['stock.landed.cost']
        picking = order.picking_ids[:1]
        if not picking:
            return
        flete_product = self.env['product.product'].search([
            ('type', '=', 'service'), ('company_id', '=', order.company_id.id)
        ], limit=1)
        if not flete_product:
            flete_product = self.env['product.product'].create({
                'name': 'Flete Internacional',
                'type': 'service',
                'list_price': 0,
                'company_id': order.company_id.id,
            })
        cost_lines = [(0, 0, {
            'product_id': flete_product.id,
            'price_unit': order.amount_untaxed * 0.05,
            'split_method': 'by_quantity',
        })]
        journal = self.env['account.journal'].search([
            ('company_id', '=', order.company_id.id), ('type', '=', 'general')
        ], limit=1)
        vals = {
            'picking_ids': [(4, picking.id)],
            'cost_lines': cost_lines,
            'account_journal_id': journal.id if journal else False,
        }
        return stock_landed_cost.create(vals)
