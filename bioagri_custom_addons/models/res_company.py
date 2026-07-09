from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    x_agente_retencion_ganancias = fields.Boolean(
        string='Es Agente de Retención de Ganancias (RG 830)',
        default=False,
        help='Si está activo, el sistema calculará retenciones de Ganancias '
             'al validar pagos a proveedores.',
    )
