import logging
from datetime import date

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BCRA_URL = 'https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD'
DOLARAPI_URL = 'https://dolarapi.com/v1/dolares/oficial'


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    @api.model
    def _fetch_bcra_rate(self):
        try:
            resp = requests.get(BCRA_URL, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get('results', {})
            detalle = results.get('detalle', [])
            for item in detalle:
                if item.get('codigoMoneda') == 'A3500':
                    rate_val = item.get('tipoCotizacion', 0)
                    return {
                        'rate': rate_val,
                        'date': results.get('fecha', date.today().isoformat()),
                    }
        except Exception as e:
            _logger.warning('BCRA API failed: %s', e)
        return None

    @api.model
    def _fetch_dolarapi_rate(self):
        try:
            resp = requests.get(DOLARAPI_URL, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            venta = data.get('venta', 0)
            if venta:
                return {
                    'rate': venta,
                    'date': data.get('fechaActualizacion', date.today().isoformat())[:10],
                }
        except Exception as e:
            _logger.warning('DolarAPI failed: %s', e)
        return None

    @api.model
    def action_actualizar_cotizacion_bcra(self):
        usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        if not usd:
            raise UserError('No se encontró la moneda USD en el sistema.')

        rate_data = self._fetch_bcra_rate()
        if not rate_data:
            rate_data = self._fetch_dolarapi_rate()
        if not rate_data:
            raise UserError('No se pudo obtener la cotización del BCRA ni de DolarAPI.')

        rate_value = rate_data['rate']
        rate_date = rate_data['date']

        if rate_value <= 0:
            raise UserError('La cotización recibida es inválida.')

        existing = self.search([
            ('currency_id', '=', usd.id),
            ('name', '=', rate_date),
        ], limit=1)

        if existing:
            existing.write({'rate': rate_value})
        else:
            self.create({
                'currency_id': usd.id,
                'name': rate_date,
                'rate': rate_value,
            })

        _logger.info('Cotización USD actualizada: %s = %s (fecha: %s)', usd.name, rate_value, rate_date)
        return True

    @api.model
    def _cron_actualizar_cotizacion(self):
        self.action_actualizar_cotizacion_bcra()
