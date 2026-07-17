from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_percepcion_iibb = fields.Float(
        string='Percepcion IIBB',
        compute='_compute_percepcion_iibb',
    )
    x_picking_id = fields.Many2one(
        'stock.picking',
        string='Remito / Importacion',
        domain="[('picking_type_id.code', '=', 'incoming')]",
        help='Vincula esta factura de gasto a un remito de importacion para prorratear como Costo en Destino.',
    )

    @api.onchange('x_picking_id')
    def _onchange_x_picking_id(self):
        if not self.x_picking_id or self.move_type != 'in_invoice':
            return
        existing_products = self.invoice_line_ids.mapped('product_id').ids
        flete = self.env.ref('bioagri_custom_addons.product_flete_importacion', raise_if_not_found=False)
        if not flete:
            flete = self.env['product.product'].create({
                'name': 'Flete de Importacion',
                'type': 'service',
            })
        seguro = self.env.ref('bioagri_custom_addons.product_seguro_importacion', raise_if_not_found=False)
        if not seguro:
            seguro = self.env['product.product'].create({
                'name': 'Seguro de Importacion',
                'type': 'service',
            })
        lines_to_add = []
        if flete and flete.id not in existing_products:
            lines_to_add.append((0, 0, {
                'name': flete.name,
                'product_id': flete.id,
                'quantity': 1,
                'price_unit': 0,
            }))
        if seguro and seguro.id not in existing_products:
            lines_to_add.append((0, 0, {
                'name': seguro.name,
                'product_id': seguro.id,
                'quantity': 1,
                'price_unit': 0,
            }))
        if lines_to_add:
            self.invoice_line_ids = lines_to_add

    @api.depends('invoice_line_ids', 'partner_id', 'move_type',
                 'partner_id.x_alicuota_percepcion')
    def _compute_percepcion_iibb(self):
        for move in self:
            move.x_percepcion_iibb = 0.0
            if move.move_type != 'out_invoice':
                continue
            partner = move.partner_id.commercial_partner_id
            alicuota = partner.x_alicuota_percepcion
            if not alicuota or alicuota <= 0:
                continue
            gravado = sum(
                line.price_subtotal for line in move.invoice_line_ids
                if line.tax_ids and any(t.amount > 0 for t in line.tax_ids)
            )
            if gravado > 0:
                move.x_percepcion_iibb = gravado * (alicuota / 100.0)

    def action_post(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            partner = move.partner_id.commercial_partner_id
            if partner.x_situacion_5:
                raise ValidationError(
                    _('[BLOQUEO] Cliente en SITUACION 5: No es posible validar facturas. '
                      'Contacte al area de administracion.')
                )
            if partner.credit_limit > 0 and move.move_type == 'out_invoice':
                total_debt = partner.credit + move.amount_total_signed
                if total_debt > partner.credit_limit:
                    raise ValidationError(
                        _('[BLOQUEO] La factura por $%s excede el limite de credito del cliente ($%s). '
                          'Saldo actual deudor: $%s.')
                        % (
                            move.amount_total_signed,
                            partner.credit_limit,
                            partner.credit,
                        )
                    )
        res = super().action_post()

        for move in self:
            if move.move_type == 'in_invoice' and move.x_picking_id:
                move._create_landed_cost_from_bill()

        return res

    def _create_landed_cost_from_bill(self):
        self.ensure_one()
        if not self.x_picking_id:
            return

        picking = self.x_picking_id

        product = self.invoice_line_ids[:1].product_id
        if not product:
            product = self.env['product.product'].search([
                ('type', '=', 'service'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Costo en Destino - %s' % (self.partner_id.name or ''),
                'type': 'service',
                'list_price': 0,
                'company_id': self.company_id.id,
            })

        journal = self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('type', '=', 'general'),
        ], limit=1)

        landed_cost = self.env['stock.landed.cost'].create({
            'picking_ids': [(4, picking.id)],
            'cost_lines': [(0, 0, {
                'product_id': product.id,
                'price_unit': self.amount_total,
                'split_method': 'by_quantity',
            })],
            'account_journal_id': journal.id if journal else False,
        })

        return landed_cost

    def _create_debit_note_for_exchange_diff(self, amount_diff):
        self.ensure_one()
        if amount_diff < 0.01:
            return

        company = self.company_id
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', company.id),
        ], limit=1)

        invoice_lines = [(0, 0, {
            'name': 'Diferencia de Cambio (automatica)',
            'quantity': 1,
            'price_unit': amount_diff,
            'tax_ids': [(6, 0, [])],
        })]

        debit_move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id if journal else False,
            'invoice_line_ids': invoice_lines,
        })

        try:
            debit_move.action_post()
        except Exception:
            pass

        return debit_move
