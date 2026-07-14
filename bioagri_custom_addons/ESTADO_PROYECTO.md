# Bioagri Custom Addons - Odoo 18

## Informacion del Proyecto

- **Modulo:** bioagri_custom_addons
- **Version:** 18.0.1.0.0
- **Branch:** pruebas-bioagri
- **Staging URL:** https://sistemasbioagri-art-bioagrierp1-pruebas-bioagri-34695029.dev.odoo.com
- **Base de datos:** p_sistemasbioagri_art_bioagrierp1_pruebas_bioagri_34695029

---

## Status General

| # | Modulo | Estado | Ultimo Commit |
|---|--------|--------|---------------|
| 1 | Limite de Credito | LISTO | — |
| 2 | Percepcion IIBB | LISTO | — |
| 3 | Campos Logisticos | LISTO | — |
| 4 | Retencion de Ganancias | LISTO | — |
| 5 | Informe de Factura | LISTO | — |
| 6 | Cotizacion USD | LISTO | — |
| 7 | Remito PDF | PENDIENTE PRUEBA | 053cb8c |
| 8 | Landed Costs | PENDIENTE PRUEBA | 053cb8c |
| 9 | Nota Debito Cambio | PENDIENTE PRUEBA | — |
| 10 | Codigo Proveedor OC | PENDIENTE | — |

---

## 1. Limite de Credito (Situacion 5)

### Que hace
Bloquea la confirmacion de pedidos y publicacion de facturas si el cliente supera su limite de credito o esta en Situacion 5.

### Archivos involucrados
- `models/sale_order.py` — Hereda `action_confirm`
- `models/account_move.py` — Hereda `action_post`
- `views/res_partner_views.xml` — Campo `x_situacion_5` y `credit_limit` en ficha de cliente

### Como probar
1. Ir a **Contactos** > buscar un cliente > **Editar**
2. En la pestaña **Ventas**, poner un **Limite de credito** (ej: $10.000)
3. Ir a **Ventas** > **Nuevo** > crear pedido para ese cliente con monto mayor al limite
4. Confirmar — debe saltar error: **[BLOQUEO] El monto del pedido excede el limite de credito**
5. Si el cliente tiene **Situacion 5** activada, tambien bloquea

---

## 2. Percepcion IIBB

### Que hace
Calcula automaticamente la percepcion de Ingresos Brutos en facturas de venta segun la alicuota configurada en el cliente.

### Archivos involucrados
- `models/account_move.py` — Campo calculado `x_percepcion_iibb`
- `models/res_partner.py` — Campo `x_alicuota_percepcion`
- `reports/invoice_report.xml` — Fila de Percepcion IIBB en PDF de factura
- `views/res_partner_views.xml` — Campo visible en ficha de cliente
- `wizards/arba_padron_import_wizard.py` — Importacion de padron ARBA

### Como probar
1. Ir a **Contactos** > buscar cliente > **Editar**
2. En **Ventas**, poner un valor en **Alicuota Percepcion IIBB** (ej: 2.5)
3. Crear una **Factura de Venta** para ese cliente con productos gravados
4. Validar — debe aparecer el calculo de Percepcion IIBB
5. Imprimir PDF — debe aparecer la fila "Percepcion IIBB" en los totales

---

## 3. Campos Logisticos

### Que hace
Agrega campos de Chofer, DNI, Patente y Transportista en remitos de salida, y Remito del Proveedor en recepciones de compra. Son obligatorios al validar.

### Archivos involucrados
- `models/stock_picking.py` — Campos y validacion en `button_validate`
- `views/stock_picking_views.xml` — Campos en formulario de picking

### Como probar
1. Ir a **Inventario** > **Ordenes de entrega** > abrir un remito
2. Verificar que los campos **Nombre del Chofer**, **DNI del Chofer**, **Patente del Vehiculo** y **Transportista** estan visibles
3. Intentar validar sin completar los campos — debe saltar error
4. Completar los campos y validar — debe permitir
5. Para recepciones: ir a **Recepciones** > el campo **Remito del Proveedor** debe estar visible y ser obligatorio

---

## 4. Retencion de Ganancias RG 830

### Que hace
Calcula retenciones de Ganancias en pagos a proveedores segun regimenes de AFIP, con escalas progresivas, acumulado mensual, exportacion SIRE y certificado PDF.

### Archivos involucrados
- `models/account_payment.py` — Motor de calculo, SIRE, inyeccion contable
- `models/ganancias_regimen.py` — Modelo de regimenes
- `models/ganancias_escala.py` — Modelo de escalas
- `models/res_company.py` — Campo `x_agente_retencion_ganancias`
- `views/ganancias_regimen_views.xml` — ABM de regimenes
- `views/ganancias_escala_views.xml` — ABM de escalas
- `views/account_payment_views.xml` — Campos readonly en pagos
- `views/res_company_views.xml` — Checkbox de agente en empresa
- `reports/retencion_ganancias_certificado.xml` — Certificado PDF
- `data/regimenes_ganancias.xml` — Regimenes pre-cargados
- `data/escalas_ganancias.xml` — Escalas pre-cargadas

### Como probar
1. Ir a **Contabilidad** > **Configuracion** > **Empresa** > verificar que **Agente de Retencion de Ganancias** esta activado
2. Ir a **Contabilidad** > **Retencion Ganancias** > **Regimenes** > revisar los regimenes cargados
3. Ir a **Contabilidad** > **Retencion Ganancias** > **Escalas** > revisar las escalas
4. Ir a **Contactos** > buscar un proveedor (Responsable Inscripto) > en **Contabilidad**, seleccionar un **Regimen de Ganancias**
5. Ir a **Contabilidad** > **Pagos** > **Crear** > seleccionar el proveedor > poner un monto
6. Validar — debe calcular la retencion automaticamente
7. Verificar en **Contabilidad** > **Pagos con Retencion** que aparece el pago
8. Imprimir **Certificado de Retencion de Ganancias** — debe generar el PDF
9. Exportar **SIRE** — debe descargar un .txt

---

## 5. Informe de Factura

### Que hace
Modifica el PDF de factura para mostrar titulo verde "FACTURA" con numero y agregar fila de Percepcion IIBB.

### Archivos involucrados
- `reports/invoice_report.xml` — Hereda `account.report_invoice_document`

### Como probar
1. Ir a **Contabilidad** > **Facturas** > abrir una factura de venta validada
2. Imprimir — verificar que dice **FACTURA** en verde con el numero
3. Verificar que aparece la fila **Percepcion IIBB** en los totales (si el cliente tiene alicuota)

---

## 6. Cotizacion USD Automatica

### Que hace
Actualiza diariamente la cotizacion del dolar usando la API del BCRA (con fallback a DolarAPI).

### Archivos involucrados
- `models/currency_rate_updater.py` — Logica de actualizacion
- `data/ir_cron.xml` — Cron diario a las 15:00
- `views/currency_rate_updater_views.xml` — Campo en empresa

### Como probar
1. Ir a **Ajustes** > **Empresa** > verificar que aparece el campo **Cotizacion USD**
2. Ir a **Configuracion** > **Technical** > **Scheduled Actions** > buscar **Actualizar cotizacion USD BCRA**
3. Ejecutar manualmente — debe actualizar el valor
4. Verificar en **Empresa** que el valor cambio

---

## 7. Remito PDF Personalizado

### Que hace
Sobreescribe el reporte estandar de entrega con un layout estilo Rizobacter: header con logo, datos de empresa, cliente, transporte, tabla de productos, lotes, terminos y firma.

### Archivos involucrados
- `reports/stock_delivery_report.xml` — Template QWeb + paperformat

### Como probar
1. Ir a **Inventario** > **Ordenes de entrega** > abrir un remito validado (ej: WH/OUT/00002)
2. Ir a **Imprimir** > **Recibo de entrega**
3. Verificar que el PDF muestra:
   - Logo de la empresa + datos
   - Cuadro "REMITO" con numero y "Cod. 91"
   - Seccion Cliente + Direccion de envio
   - Seccion Transporte (Camion, Chofer, DNI)
   - Barra de Emergencias Toxicologicas
   - Tabla de productos con Posicion, Material, Descripcion, Cantidad
   - Lotes y vencimientos
   - Terminos y condiciones
   - Area de firma

---

## 8. Landed Costs (Costos en Destino)

### Que hace
Permite vincular facturas de gastos (despachante, flete, etc.) a remitos de importacion para crear Costos en Destino automaticamente.

### Archivos involucrados
- `models/account_move.py` — Campo `x_picking_id` y metodo `_create_landed_cost_from_bill`
- `views/account_move_views.xml` — Campo visible en facturas de proveedor

### Como probar
1. Ir a **Inventario** > **Productos** > **Configuracion** > **Categorias de productos** > abrir "All"
2. Verificar que **Metodo de costo** esta en **Costo promedio (AVCO)** o **PEPS** (requerido para Landed Costs)
3. Ir a **Compras** > **Nuevo** > crear orden de compra > confirmar para que se cree el picking
4. Ir a **Contabilidad** > **Facturas** > **Crear**
5. Seleccionar proveedor del despachante/flete
6. En el campo **Remito / Importacion**, seleccionar el picking creado en paso 3
7. Agregar linea con el gasto (ej: "Flete interno" - $5.000)
8. Poner fecha y numero de factura
9. **Validar** — debe crearse un Landed Cost en borrador
10. Ir a **Inventario** > **Costos en destino** > verificar que aparece el registro en borrador
11. Abrir y **Validar** para prorratear el costo sobre los productos

### Nota importante
- El producto en la factura debe estar en una categoria con **Costo Promedio o PEPS**
- Los Costos en Destino NO funcionan con **Costo Estandar**

---

## 9. Nota de Debito por Diferencias de Cambio

### Que hace
Al validar un pago de un cliente en una moneda diferente, si hay diferencia de tipo de cambio, crea automaticamente una nota de debito.

### Archivos involucrados
- `models/account_move.py` — Metodo `_create_debit_note_for_exchange_diff`
- `models/account_payment.py` — Hook en `action_post`

### Como probar
1. Crear una factura de venta en USD
2. Registrar un pago en ARS con tipo de cambio diferente
3. Si hay diferencia, debe crearse una nota de debito automatica
4. Verificar en **Contabilidad** > **Facturas** que aparece la nota de debito

### Estado
**PENDIENTE PRUEBA END-TO-END**

---

## 10. Codigo de Producto del Proveedor en PDF de OC

### Que hace
Muestra el codigo del producto del proveedor en el PDF de la orden de compra.

### Archivos involucrados
- `reports/purchase_order_report.xml`

### Estado
**PENDIENTE IMPLEMENTACION**

---

## Comandos Utiles

### Actualizar modulo en staging
```bash
# Desde terminal local
cd C:\Users\duvan\Documents\Bioagri\repo\bioagri_custom_addons
git add -A
git commit -m "descripcion del cambio"
git push
```

### Upgradear modulo en Odoo
1. Ir a **Ajustes** > **Activar modo desarrollador**
2. Ir a **Ajustes** > **Modulos**
3. Buscar **Bioagri Custom Addons**
4. Clic en **Actualizar**

### Ejecutar desde shell de Odoo (Odoo.sh)
```bash
odoo-bin -u bioagri_custom_addons -d p_sistemasbioagri_art_bioagrierp1_pruebas_bioagrierp1_pruebas_bioagri_34695029 --stop-after-init
```

---

## Notas Importantes

- **Encoding en XML:** No usar acentos ni caracteres especiales en templates QWeb. wkhtmltopdf no los maneja bien. Usar solo ASCII puro.
- **Costos en Destino:** Solo funcionan con productos en categorias con Costo Promedio o PEPS. NO con Costo Estandar.
- **Staging:** Se auto-elimina el 8 de agosto 2026. No guardar datos importantes ahi.
- **Modo desarrollador:** Activarlo para ver campos tecnicos y funcionalidades avanzadas.
