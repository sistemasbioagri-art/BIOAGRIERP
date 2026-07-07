from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.incoterm_id and order.incoterm_id.code in ('FOB', 'CIF'):
                # ponytail: precarga borrador de landed costs
                # add when: se necesiten cálculos detallados multi-gasto
                self._create_draft_landed_cost(order)
        return res

    def _create_draft_landed_cost(self, order):
        stock_landed_cost = self.env['stock.landed.cost']
        picking = order.picking_ids[:1]
        if not picking:
            return
        lines = []
        for move in picking.move_ids_without_package:
            lines.append((0, 0, {
                'product_id': move.product_id.id,
                'quantity': move.product_uom_qty,
                'move_id': move.id,
            }))
        if not lines:
            return
        # ponytail: gasto fijo estimado de flete, add when: gastos reales variables
        # ponytail: usa cualquier producto de tipo servicio como flete estimado
        flete_product = self.env['product.product'].search([
            ('type', '=', 'service'), ('company_id', '=', order.company_id.id)
        ], limit=1)
        cost_lines = []
        if flete_product:
            cost_lines.append((0, 0, {
                'product_id': flete_product.id,
                'price_unit': order.amount_untaxed * 0.05,
                'split_method': 'by_quantity',
            }))
        journal = self.env['account.journal'].search([
            ('company_id', '=', order.company_id.id), ('type', '=', 'general')
        ], limit=1)
        vals = {
            'picking_ids': [(4, picking.id)],
            'cost_lines': cost_lines,
            'account_journal_id': journal.id if journal else False,
        }
        landed_cost = stock_landed_cost.create(vals)
        return landed_cost
