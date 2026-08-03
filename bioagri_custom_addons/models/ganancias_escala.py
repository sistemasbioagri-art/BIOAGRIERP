from odoo import fields, models


class GananciasEscala(models.Model):
    _name = 'x_ganancias.escala'
    _description = 'Escala Progresiva de Retención de Ganancias'
    _order = 'monto_desde'

    regimen_id = fields.Many2one(
        'x_ganancias.regimen', string='Régimen', required=True, ondelete='cascade'
    )
    monto_desde = fields.Float(string='Monto Desde', required=True)
    monto_hasta = fields.Float(string='Monto Hasta', required=True)
    monto_fijo = fields.Float(string='Monto Fijo Impositivo', required=True)
    porcentaje = fields.Float(string='% a Aplicar', required=True)
    sobre_excedente = fields.Float(string='Sobre el Excedente de', required=True)
