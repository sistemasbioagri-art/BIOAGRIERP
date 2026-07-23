from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError, URLError
    from socket import timeout as SocketTimeout
except ImportError:
    urlopen = None

_logger = logging.getLogger(__name__)

BCRA_API_URL = "https://api.bcra.gob.ar/CentralDeDeudores/v1.0/Deudas/{}"
BCRA_TIMEOUT = 10


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

    # --- Campos API BCRA Central de Deudores ---
    x_bcra_situacion = fields.Selection(
        [
            ('1', '1 - Normal'),
            ('2', '2 - Seguimiento especial'),
            ('3', '3 - Con problemas'),
            ('4', '4 - Alto riesgo de insolvencia'),
            ('5', '5 - Irrecuperable'),
        ],
        string='Situación BCRA',
        help='Peor situación crediticia detectada en la Central de Deudores del BCRA.',
        readonly=True,
    )
    x_bcra_monto = fields.Float(
        string='Monto adeudado (miles ARS)',
        help='Monto total adeudado en miles de pesos argentinos.',
        readonly=True,
    )
    x_bcra_dias_atraso = fields.Integer(
        string='Días de atraso',
        help='Máximo días de atraso detectado.',
        readonly=True,
    )
    x_bcra_ultima_consulta = fields.Datetime(
        string='Última consulta BCRA',
        help='Fecha y hora de la última consulta a la API del BCRA.',
        readonly=True,
    )
    x_bcra_tipo_consulta = fields.Selection(
        [('manual', 'Manual'), ('cron', 'Cron')],
        string='Tipo de consulta',
        help='Indica si la última consulta fue manual o automática (cron).',
        readonly=True,
    )
    x_bcra_entidades = fields.Text(
        string='Entidades detectadas',
        help='Listado de entidades financieras donde el cliente tiene deuda.',
        readonly=True,
    )
    x_bcra_dias_sin_consultar = fields.Integer(
        string='Días sin consultar',
        compute='_compute_bcra_dias_sin_consultar',
        store=False,
        help='Días transcurridos desde la última consulta a la API del BCRA. '
             'Si es mayor a 7, el cron debería haber corrido ya.',
    )

    # --- Métodos API BCRA ---

    @api.depends('x_bcra_ultima_consulta')
    def _compute_bcra_dias_sin_consultar(self):
        for partner in self:
            if not partner.x_bcra_ultima_consulta:
                partner.x_bcra_dias_sin_consultar = 999
            else:
                delta = fields.Datetime.now() - partner.x_bcra_ultima_consulta
                partner.x_bcra_dias_sin_consultar = delta.days

    def _limpiar_cuit(self):
        """Extrae solo dígitos del VAT y devuelve 11 dígitos o False."""
        self.ensure_one()
        if not self.vat:
            return False
        cuit = ''.join(ch for ch in self.vat if ch.isdigit())
        return cuit if len(cuit) == 11 else False

    def _consultar_bcra_api(self, cuit):
        """Consulta la API del BCRA y devuelve (situacion_peor, monto_total, dias_max, entidades_list, error_msg)."""
        if urlopen is None:
            return None, None, None, None, 'Librería urllib no disponible'

        url = BCRA_API_URL.format(cuit)
        req = Request(url, headers={'Accept': 'application/json'})

        try:
            with urlopen(req, timeout=BCRA_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, SocketTimeout, json.JSONDecodeError) as e:
            _logger.warning('BCRA API error para CUIT %s: %s', cuit, e)
            return None, None, None, None, str(e)

        if data.get('status') != 200:
            msg = data.get('errorMessages', ['Error desconocido'])[0]
            return None, None, None, None, msg

        results = data.get('results', {})
        periodos = results.get('periodos', [])
        if not periodos:
            return None, None, None, None, 'Sin datos de deuda'

        # Tomar el período más reciente (último)
        ultimo_periodo = periodos[-1]
        entidades = ultimo_periodo.get('entidades', [])
        if not entidades:
            return None, None, None, None, 'Sin entidades reportadas'

        situacion_peor = 1
        monto_total = 0.0
        dias_max = 0
        entidades_nombres = []

        for ent in entidades:
            sit = ent.get('situacion', 1)
            if sit > situacion_peor:
                situacion_peor = sit
            monto_total += ent.get('monto', 0.0)
            dias = ent.get('diasAtrasoPago', 0)
            if dias > dias_max:
                dias_max = dias
            entidades_nombres.append(ent.get('entidad', 'Desconocida'))

        return str(situacion_peor), monto_total, dias_max, entidades_nombres, None

    def action_consultar_bcra(self):
        """Botón manual: consulta BCRA para este partner."""
        self.ensure_one()
        cuit = self._limpiar_cuit()
        if not cuit:
            raise UserError(_('El contacto no tiene un CUIT válido de 11 dígitos.'))

        situacion, monto, dias, entidades, error = self._consultar_bcra_api(cuit)

        if error:
            _logger.warning('Consulta BCRA manual falló para %s: %s', self.name, error)
            raise UserError(_('Error al consultar BCRA: %s') % error)

        self.write({
            'x_bcra_situacion': situacion,
            'x_bcra_monto': monto,
            'x_bcra_dias_atraso': dias,
            'x_bcra_ultima_consulta': fields.Datetime.now(),
            'x_bcra_tipo_consulta': 'manual',
            'x_bcra_entidades': ', '.join(entidades) if entidades else '',
        })

        # Si situacion 5, activar bloqueo comercial (pero no desactivar nunca)
        if situacion == '5':
            self.write({'x_situacion_5': True})

        # ponytail: recargar vista para mostrar campos actualizados sin manual refresh
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _cron_consultar_bcra_todos(self):
        """Cron semanal: consulta todos los clientes con CUIT."""
        partners = self.search([
            ('vat', '!=', False),
            '|',
            ('customer_rank', '>', 0),
            ('supplier_rank', '>', 0),
        ])

        _logger.info('BCRA Cron: consultando %s contactos...', len(partners))

        activados = 0
        errores = 0

        for partner in partners:
            cuit = partner._limpiar_cuit()
            if not cuit:
                continue

            situacion, monto, dias, entidades, error = partner._consultar_bcra_api(cuit)

            if error:
                errores += 1
                continue

            vals = {
                'x_bcra_situacion': situacion,
                'x_bcra_monto': monto,
                'x_bcra_dias_atraso': dias,
                'x_bcra_ultima_consulta': fields.Datetime.now(),
                'x_bcra_tipo_consulta': 'cron',
                'x_bcra_entidades': ', '.join(entidades) if entidades else '',
            }

            if situacion == '5' and not partner.x_situacion_5:
                vals['x_situacion_5'] = True
                activados += 1
                _logger.warning(
                    'BCRA Cron: Cliente %s (ID %s) activado en Situación 5. '
                    'Monto: %s, Entidades: %s',
                    partner.name, partner.id, monto, entidades
                )

            partner.write(vals)

        _logger.info(
            'BCRA Cron finalizado. Contactos procesados: %s, '
            'Situación 5 activados: %s, Errores: %s',
            len(partners), activados, errores
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cron BCRA completado'),
                'message': _(
                    '%s contactos consultados. %s activados en Situación 5. %s errores.'
                ) % (len(partners), activados, errores),
                'type': 'info',
                'sticky': False,
            }
        }
