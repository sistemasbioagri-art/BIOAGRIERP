from odoo import fields, models


class ArbaPadronImport(models.Model):
    _name = 'arba.padron.import'
    _description = 'Importación de Padrón ARBA'
    _order = 'create_date desc'

    name = fields.Char('Archivo', required=True)
    fecha_vigencia = fields.Date('Fecha de Vigencia')
    tipo = fields.Selection([
        ('percepcion', 'Percepción'),
        ('retencion', 'Retención'),
    ], string='Tipo', required=True)
    line_ids = fields.One2many('arba.padron.line', 'import_id', string='Líneas')
    count_updated = fields.Integer('Registros Actualizados')
    count_total = fields.Integer('Total Lineas')


class ArbaPadronLine(models.Model):
    _name = 'arba.padron.line'
    _description = 'Línea de Padrón ARBA'

    import_id = fields.Many2one('arba.padron.import', string='Importación', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Contacto')
    cuit = fields.Char('CUIT')
    alicuota_anterior = fields.Float('Alícuota Anterior (%)')
    alicuota_nueva = fields.Float('Alícuota Nueva (%)')
    updated = fields.Boolean('Actualizado')
