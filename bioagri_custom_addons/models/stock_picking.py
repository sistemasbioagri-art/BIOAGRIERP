from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_chofer_nombre = fields.Char('Nombre del Chofer')
    x_chofer_dni = fields.Char('DNI del Chofer')
    x_patente = fields.Char('Patente del Vehículo')
    x_transportista_id = fields.Many2one(
        'res.partner', string='Transportista',
        domain="[('company_type', '=', 'company')]",
    )
    x_remito_proveedor = fields.Char(
        'Remito del Proveedor',
        help='Número de remito del proveedor para recepciones de compra.',
    )

    def button_validate(self):
        for picking in self:
            code = picking.picking_type_id.code
            if code == 'outgoing':
                if not picking.x_chofer_nombre or not picking.x_chofer_dni or not picking.x_patente:
                    raise ValidationError(
                        _('Complete los datos del chofer (Nombre, DNI, Patente) '
                          'antes de validar el remito de salida.')
                    )
            if code == 'incoming':
                if not picking.x_remito_proveedor:
                    raise ValidationError(
                        _('Complete el número de Remito del Proveedor '
                          'antes de validar la recepción.')
                    )
        return super().button_validate()
