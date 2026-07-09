from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_situacion_5 = fields.Boolean(
        string='Situación 5 (Bloqueo Comercial)',
        help='Si está activo, bloquea absolutamente la creación de presupuestos, pedidos y facturas para este cliente.',
    )
    x_alicuota_percepcion = fields.Float(
        string='Alícuota Percepción IIBB (%)',
        help='Porcentaje de percepción de Ingresos Brutos según padrón ARBA.',
    )
    x_alicuota_retencion = fields.Float(
        string='Alícuota Retención IIBB (%)',
        help='Porcentaje de retención de Ingresos Brutos según padrón ARBA.',
    )
    x_padron_vigencia = fields.Date(
        string='Vigencia del Padrón',
        help='Fecha hasta la cual están vigentes las alícuotas del padrón.',
    )
    x_regimen_ganancias = fields.Many2one(
        'x_ganancias.regimen',
        string='Régimen Retención Ganancias',
        help='Régimen de Retención de Ganancias asignado al proveedor. '
             'Solo aplica para Responsables Inscriptos.',
    )
