# Cotización USD BCRA - Implementación

## Descripción

Módulo que actualiza automáticamente la cotización del dólar oficial (BCRA) en Odoo, utilizada para facturación y contabilidad de Bioagri S.A.

## Archivos involucrados

| Archivo | Función |
|---------|---------|
| `models/currency_rate_updater.py` | Modelo con métodos de consulta y actualización |
| `views/currency_rate_updater_views.xml` | Botón manual + menú en Contabilidad > Configuración |
| `data/ir_cron.xml` | Cron job diario a las 15:00 (hora bancaria) |
| `__manifest__.py` | Registro de archivos nuevos |

## APIs utilizadas

### Principal: API Oficial BCRA

```
GET https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/usd
```

- Gratuita, sin API key
- Retorna cotización oficial del dólar en pesos argentinos
- Fuente: Banco Central de la República Argentina

### Fallback: DolarAPI

```
GET https://dolarapi.com/v1/dolares/oficial
```

- Gratuita, sin API key
- Se usa solo si la API del BCRA no responde
- Fuente: DolarHoy / Ámbito Financiero

## Uso

### Actualización manual

1. Ir a **Contabilidad > Configuración**
2. Hacer clic en **"Actualizar cotización BCRA"**
3. Se actualiza la tasa de USD en el sistema

### Actualización automática

El cron job se ejecuta **una vez por día a las 15:00** (horario bancario argentino).

## Cómo funciona

1. Consulta la API del BCRA
2. Extrae la cotización `tipoCotizacion` para USD
3. Busca si ya existe una tasa para esa fecha en `res.currency.rate`
4. Si existe → la actualiza
5. Si no existe → crea un nuevo registro
6. Si el BCRA falla → intenta con DolarAPI como respaldo

## Datos de ejemplo (junio 2026)

```json
{
  "results": {
    "fecha": "2026-06-30",
    "detalle": [{
      "codigoMoneda": "USD",
      "tipoCotizacion": 1428.50
    }]
  }
}
```

## Dependencias

- `base` (Odoo core)
- `requests` (Python library, incluida en Odoo)

## Notas técnicas

- El campo `rate` en Odoo almacena: ARS por 1 USD
- Ejemplo: si 1 USD = 1428.50 ARS, el rate es 1428.50
- La fecha se guarda en formato `YYYY-MM-DD`
- Si la cotización del día ya existe, se sobreescribe
