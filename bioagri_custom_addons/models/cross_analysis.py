from odoo import api, fields, models


class BioagriCrossAnalysis(models.Model):
    _name = 'bioagri.cross.analysis'
    _description = 'Informe Cruzado de Stock, Ventas y Facturación'
    _auto = False
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    qty_ordered = fields.Float('Cant. Pedida', readonly=True)
    qty_delivered = fields.Float('Cant. Entregada', readonly=True)
    qty_invoiced = fields.Float('Cant. Facturada', readonly=True)
    qty_pending_delivery = fields.Float('Pendiente de Entrega', readonly=True)
    qty_pending_invoice = fields.Float('Pendiente de Facturar', readonly=True)

    def _get_sql_view(self):
        return """
        CREATE OR REPLACE VIEW bioagri_cross_analysis AS (
            WITH
            pedidos AS (
                SELECT
                    sol.order_partner_id AS partner_id,
                    sol.product_id,
                    SUM(sol.product_uom_qty) AS qty_ordered
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id
                WHERE so.state IN ('sale', 'done')
                GROUP BY sol.order_partner_id, sol.product_id
            ),
            entregas AS (
                SELECT
                    sm.partner_id,
                    sm.product_id,
                    SUM(sm.product_uom_qty) AS qty_delivered
                FROM stock_move sm
                JOIN stock_picking sp ON sp.id = sm.picking_id
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE sm.state = 'done'
                  AND spt.code = 'outgoing'
                GROUP BY sm.partner_id, sm.product_id
            ),
            facturado AS (
                SELECT
                    aml.partner_id,
                    aml.product_id,
                    SUM(aml.quantity) AS qty_invoiced
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE am.state = 'posted'
                  AND am.move_type IN ('out_invoice', 'out_refund')
                  AND aml.product_id IS NOT NULL
                GROUP BY aml.partner_id, aml.product_id
            )
            SELECT
                ROW_NUMBER() OVER () AS id,
                COALESCE(p.partner_id, e.partner_id, f.partner_id) AS partner_id,
                COALESCE(p.product_id, e.product_id, f.product_id) AS product_id,
                COALESCE(p.qty_ordered, 0) AS qty_ordered,
                COALESCE(e.qty_delivered, 0) AS qty_delivered,
                COALESCE(f.qty_invoiced, 0) AS qty_invoiced,
                COALESCE(p.qty_ordered, 0) - COALESCE(e.qty_delivered, 0) AS qty_pending_delivery,
                COALESCE(e.qty_delivered, 0) - COALESCE(f.qty_invoiced, 0) AS qty_pending_invoice
            FROM pedidos p
            FULL JOIN entregas e ON e.partner_id = p.partner_id AND e.product_id = p.product_id
            FULL JOIN facturado f ON f.partner_id = COALESCE(p.partner_id, e.partner_id)
                                AND f.product_id = COALESCE(p.product_id, e.product_id)
        )
        """

    def init(self):
        self.env.cr.execute(self._get_sql_view())
