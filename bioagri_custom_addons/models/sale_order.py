from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_es_consignacion = fields.Boolean(
        string='Venta de Consignación',
        help='Si está activo, indica que este pedido es para facturar producto que ya '
             'se encuentra en poder del cliente (consignación previa). '
             'No generará exigencia de datos de transporte en el remito.',
    )

    def action_confirm(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            if partner.x_situacion_5:
                raise ValidationError(
                    _('[BLOQUEO] Cliente en SITUACIÓN 5: No es posible confirmar pedidos. '
                      'Contacte al área de administración.')
                )
            if partner.credit_limit > 0:
                total_debt = partner.credit + order.amount_total
                if total_debt > partner.credit_limit:
                    raise ValidationError(
                        _('[BLOQUEO] El monto del pedido ($%s) excede el límite de crédito disponible ($%s). '
                          'Saldo actual deudor: $%s.')
                        % (
                            order.amount_total,
                            partner.credit_limit,
                            partner.credit,
                        )
                    )
        return super().action_confirm()
