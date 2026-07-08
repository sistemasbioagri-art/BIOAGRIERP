from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_percepcion_iibb = fields.Float(
        string='Percepción IIBB',
        compute='_compute_percepcion_iibb',
        store=True,
    )

    @api.depends('invoice_line_ids', 'partner_id', 'move_type')
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
                    _('[BLOQUEO] Cliente en SITUACIÓN 5: No es posible validar facturas. '
                      'Contacte al área de administración.')
                )
            if partner.credit_limit > 0 and move.move_type == 'out_invoice':
                total_debt = partner.credit + move.amount_total_signed
                if total_debt > partner.credit_limit:
                    raise ValidationError(
                        _('[BLOQUEO] La factura por $%s excede el límite de crédito del cliente ($%s). '
                          'Saldo actual deudor: $%s.')
                        % (
                            move.amount_total_signed,
                            partner.credit_limit,
                            partner.credit,
                        )
                    )
            if move.move_type == 'out_invoice' and move.x_percepcion_iibb:
                self._apply_percepcion_line(move)
        return super().action_post()

    def _apply_percepcion_line(self, move):
        perception_line = move.invoice_line_ids.filtered(
            lambda l: l.display_type == 'line_note' and 'PERCEPCIÓN IIBB' in (l.name or '')
        )
        if perception_line:
            return
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 0),
            ('company_id', '=', move.company_id.id),
            ('name', 'ilike', 'percepción'),
        ], limit=1)
        if not tax:
            tax = self.env['account.tax'].search([
                ('type_tax_use', '=', 'sale'),
                ('amount', '=', 0),
                ('company_id', '=', move.company_id.id),
            ], limit=1)
        if not tax:
            return
        partner = move.partner_id.commercial_partner_id
        move.write({
            'invoice_line_ids': [(0, 0, {
                'name': 'PERCEPCIÓN IIBB (alíc. %s%%)' % partner.x_alicuota_percepcion,
                'quantity': 1,
                'price_unit': move.x_percepcion_iibb,
                'display_type': 'line_note',
                'tax_ids': [(6, 0, tax.ids)],
            })],
        })

    def _create_debit_note_for_exchange_diff(self, amount_diff):
        if amount_diff < 0.01:
            return
        iva_tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 21),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        invoice_lines = [(0, 0, {
            'name': 'Diferencia de Cambio (Nota de Débito automática)',
            'quantity': 1,
            'price_unit': amount_diff,
            'tax_ids': [(6, 0, iva_tax.ids)] if iva_tax else [],
        })]
        debit_move = self.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        })
        debit_move.action_post()
        return debit_move
