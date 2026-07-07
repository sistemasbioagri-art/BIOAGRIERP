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
- Retención de Ganancias por escala AFIP + exportación SIRE .txt
- Informe cruzado de stock, ventas y facturación
""",
    'author': 'Bioagri S.A.',
    'website': '',
    'depends': [
        'base',
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
        'views/purchase_supplierinfo_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
