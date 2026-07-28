from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_requiere_chofer = fields.Boolean(
        'Requiere información del chofer', default=True,
    )
    x_chofer_nombre = fields.Char('Nombre del Chofer')
    x_chofer_dni = fields.Char('DNI del Chofer')
    x_patente = fields.Char('Patente del Vehículo')
    x_transportista_id = fields.Many2one(
        'res.partner', string='Transportista',
        domain="[('is_company', '=', True)]",
    )
    x_remito_proveedor = fields.Char(
        'Remito del Proveedor',
        help='Número de remito del proveedor para recepciones de compra.',
    )

    def button_validate(self):
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                if not picking.x_remito_proveedor:
                    raise ValidationError(
                        _('Complete el número de Remito del Proveedor '
                          'antes de validar la recepción.')
                    )
        return super().button_validate()
