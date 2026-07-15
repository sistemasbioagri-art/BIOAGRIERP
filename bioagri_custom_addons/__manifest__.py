{
    'name': 'Bioagri Custom Addons',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Personalizaciones para Bioagri S.A. — Gestión de consignaciones, retenciones, logística e informes',
    'description': """
Módulo personalizado para Bioagri S.A. (Odoo 18)
=================================================
- Doble bloqueo de límite de crédito y Situación 5 en ventas/facturación
- Campos logísticos obligatorios en remitos de salida (chofer, DNI, patente, transportista)
- Remito de proveedor obligatorio en recepciones de compra
- Código de producto del proveedor en PDF de orden de compra
- Precarga de costos de importación (Landed Costs) para FOB/CIF
- Retención de Ganancias RG 830 con regímenes configurables + SIRE .txt + Certificado PDF
- Informe cruzado de stock, ventas y facturación
- Actualización automática de cotización USD (BCRA)
""",
    'author': 'Bioagri S.A.',
    'website': '',
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'stock',
        'purchase',
        'sale_stock',
        'stock_landed_costs',
        'l10n_ar',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/stock_picking_views.xml',
        'views/cross_analysis_view.xml',
        'wizards/arba_padron_import_wizard.xml',
        'reports/purchase_order_report.xml',
        'reports/invoice_report.xml',
        'views/purchase_supplierinfo_views.xml',
        'views/currency_rate_updater_views.xml',
        'views/ganancias_regimen_views.xml',
        'views/ganancias_escala_views.xml',
        'views/res_company_views.xml',
        'reports/retencion_ganancias_certificado.xml',
        'reports/stock_delivery_report.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bioagri_custom_addons/static/src/js/padron_uploader.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
