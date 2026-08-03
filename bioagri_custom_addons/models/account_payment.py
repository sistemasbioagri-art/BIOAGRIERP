import csv
import io
from datetime import date

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
    x_regimen_aplicado = fields.Many2one(
        'x_ganancias.regimen',
        string='Régimen Aplicado',
        compute='_compute_retenciones',
        store=True,
    )
    x_sire_exported = fields.Boolean(
        string='Exportado SIRE',
        help='Indica si este pago fue incluido en una exportación SIRE.',
    )
    x_acumulado_mes = fields.Float(
        string='Acumulado del Mes',
        compute='_compute_retenciones',
        store=True,
    )

    @api.depends('amount', 'partner_id', 'payment_type', 'date', 'state')
    def _compute_retenciones(self):
        for rec in self:
            rec.x_base_retencion = 0.0
            rec.x_retencion_ganancias = 0.0
            rec.x_regimen_aplicado = False
            rec.x_acumulado_mes = 0.0

            if rec.payment_type != 'outbound' or not rec.partner_id:
                continue

            company = rec.company_id
            if not company.x_agente_retencion_ganancias:
                continue

            partner = rec.partner_id.commercial_partner_id
            if partner.l10n_ar_afip_responsibility_type_id.code != '1':
                continue

            regimen = partner.x_regimen_ganancias
            if not regimen:
                continue

            if rec.state not in ('in_process', 'paid'):
                continue

            rec.x_regimen_aplicado = regimen

            month_start = rec.date.replace(day=1)
            if rec.date.month == 12:
                month_end = rec.date.replace(year=rec.date.year + 1, month=1, day=1)
            else:
                month_end = rec.date.replace(month=rec.date.month + 1, day=1)

            domain = [
                ('payment_type', '=', 'outbound'),
                ('partner_id', 'in', partner.child_ids.ids + partner.ids),
                ('date', '>=', month_start),
                ('date', '<', month_end),
                ('state', 'in', ('in_process', 'paid')),
                ('id', '!=', rec.id),
            ]
            previous_payments = self.env['account.payment'].search(domain)
            acumulado_neto = sum(previous_payments.mapped('amount'))

            retenciones_previas = sum(previous_payments.mapped('x_retencion_ganancias'))

            base = acumulado_neto + rec.amount

            if base <= regimen.minimo_no_imponible:
                continue

            excedente = base - regimen.minimo_no_imponible

            if regimen.usa_escala:
                escala = self._buscar_escala(regimen, excedente)
                if escala:
                    excedente_rango = excedente - escala.sobre_excedente
                    if excedente_rango < 0:
                        excedente_rango = 0
                    impuesto = escala.monto_fijo + (excedente_rango * escala.porcentaje / 100.0)
                else:
                    impuesto = 0.0
            else:
                impuesto = excedente * regimen.alicuota_fija / 100.0

            impuesto_pendiente = impuesto - retenciones_previas

            MINIMO_RETENIBLE = 1000.0
            if impuesto_pendiente < MINIMO_RETENIBLE:
                continue

            rec.x_base_retencion = excedente
            rec.x_retencion_ganancias = impuesto_pendiente
            rec.x_acumulado_mes = acumulado_neto

    def _buscar_escala(self, regimen, excedente):
        escala = self.env['x_ganancias.escala'].search([
            ('regimen_id', '=', regimen.id),
            ('monto_desde', '<=', excedente),
            ('monto_hasta', '>=', excedente),
        ], limit=1)
        if not escala:
            escala = self.env['x_ganancias.escala'].search([
                ('regimen_id', '=', regimen.id),
            ], order='monto_hasta desc', limit=1)
        return escala

    def action_post(self):
        res = super().action_post()

        for payment in self:
            if payment.payment_type != 'inbound':
                for line in payment.move_id.line_ids:
                    if line.matched_debit_ids:
                        for matched in line.matched_debit_ids:
                            inv = matched.move_id
                            if inv.move_type != 'out_invoice':
                                continue
                            inv_amount_company = inv.amount_total_signed
                            paid_amount_company = abs(matched.amount)
                            diff = paid_amount_company - inv_amount_company
                            if abs(diff) < 0.01:
                                continue
                            inv._create_debit_note_for_exchange_diff(abs(diff))

            if payment.payment_type == 'outbound' and payment.x_retencion_ganancias > 0:
                payment._inject_retencion_contable()

        return res

    def _inject_retencion_contable(self):
        self.ensure_one()
        if not self.move_id:
            return

        company = self.company_id
        account_retencion = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'liability_current'),
            ('name', 'ilike', '%retenciones%ganancias%'),
        ], limit=1)

        if not account_retencion:
            account_retencion = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'liability_current'),
            ], limit=1)

        if not account_retencion:
            return

        journal = self.journal_id
        if not journal:
            return

        pago_real = self.amount - self.x_retencion_ganancias

        lines_to_add = []

        bank_line = False
        for line in self.move_id.line_ids:
            if line.account_id.account_type in ('asset_cash', 'asset_bank'):
                bank_line = line
                break

        if bank_line:
            bank_line.write({
                'debit': pago_real if bank_line.debit > 0 else 0,
                'credit': pago_real if bank_line.credit > 0 else 0,
            })

        retencion_line = self.env['account.move.line'].create({
            'move_id': self.move_id.id,
            'account_id': account_retencion.id,
            'name': 'Retención de Ganancias - %s' % (self.partner_id.name or ''),
            'credit': self.x_retencion_ganancias,
            'debit': 0.0,
            'partner_id': self.partner_id.id,
        })

        return retencion_line

    def action_generate_sire_txt(self):
        payments = self.env['account.payment'].search([
            ('payment_type', '=', 'outbound'),
            ('state', 'in', ('in_process', 'paid')),
            ('x_sire_exported', '=', False),
            ('x_retencion_ganancias', '>', 0),
        ])
        if not payments:
            raise ValidationError(_('No hay pagos con retenciones pendientes de exportar SIRE.'))

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter='|')
        for pago in payments:
            regimen_code = pago.x_regimen_aplicado.code if pago.x_regimen_aplicado else ''
            writer.writerow([
                pago.partner_id.vat or '',
                pago.partner_id.name,
                fields.Date.to_string(pago.date),
                regimen_code,
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
