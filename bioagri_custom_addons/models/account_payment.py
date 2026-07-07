import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    x_retencion_ganancias = fields.Float(
        string='Retención Ganancias',
        compute='_compute_retenciones',
        store=True,
    )
    x_base_retencion = fields.Float(
        string='Base Imponible Retención',
        compute='_compute_retenciones',
        store=True,
    )
    x_sire_exported = fields.Boolean(
        string='Exportado SIRE',
        help='Indica si este pago fue incluido en una exportación SIRE.',
    )

    # ponytail: escalas fijas del Régimen 78 (RG 830 AFIP)
    # add when: ARCA actualice las tablas de retención, convertirlas a configurables
    REGIMENES = {
        78: {
            'name': 'Régimen 78 - Bienes Muebles (RG 830)',
            'minimo': 1000.0,
            'tramos': [
                (0, 99999999.99, 0.02),
            ],
        },
    }

    @api.depends('amount', 'partner_id', 'payment_type')
    def _compute_retenciones(self):
        for rec in self:
            rec.x_base_retencion = 0.0
            rec.x_retencion_ganancias = 0.0
            if rec.payment_type != 'outbound' or not rec.partner_id:
                continue
            regimen = self.REGIMENES.get(78)
            if not regimen:
                continue
            base = rec.amount
            if base <= regimen['minimo']:
                continue
            excedente = base - regimen['minimo']
            alicuota = regimen['tramos'][0][2]
            rec.x_base_retencion = excedente
            rec.x_retencion_ganancias = excedente * alicuota

    def action_generate_sire_txt(self):
        payments = self.env['account.payment'].search([
            ('payment_type', '=', 'outbound'),
            ('state', '=', 'posted'),
            ('x_sire_exported', '=', False),
            ('x_retencion_ganancias', '>', 0),
        ])
        if not payments:
            raise ValidationError(_('No hay pagos con retenciones pendientes de exportar SIRE.'))

        # ponytail: formato SIRE simplificado
        # add when: ARCA publique un nuevo diseño de registro
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter='|')
        for pago in payments:
            writer.writerow([
                pago.partner_id.vat or '',
                pago.partner_id.name,
                fields.Date.to_string(pago.date),
                '%.2f' % pago.x_base_retencion,
                '%.2f' % pago.x_retencion_ganancias,
                pago.id,
            ])
        payments.write({'x_sire_exported': True})
        content = buffer.getvalue()
        buffer.close()
        filename = 'SIRE_Retenciones_%s.txt' % fields.Date.to_string(fields.Date.today())
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'raw': content.encode('utf-8'),
            'mimetype': 'text/plain',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
