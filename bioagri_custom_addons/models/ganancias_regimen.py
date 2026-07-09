from odoo import api, fields, models


class GananciasRegimen(models.Model):
    _name = 'x_ganancias.regimen'
    _description = 'Régimen de Retención de Ganancias'
    _order = 'code'

    code = fields.Integer(string='Código', required=True, index=True)
    name = fields.Char(string='Descripción', required=True)
    minimo_no_imponible = fields.Float(string='Mínimo No Imponible (Anual)', required=True)
    alicuota_fija = fields.Float(string='Alícuota Fija (%)')
    usa_escala = fields.Boolean(string='Usa Escala Progresiva', default=False)
    active = fields.Boolean(string='Activo', default=True)

    escala_ids = fields.One2many(
        'x_ganancias.escala', 'regimen_id', string='Escalas'
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código del régimen debe ser único.')
    ]

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, '%s - %s' % (rec.code, rec.name)))
        return result
