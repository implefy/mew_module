{
    'name': 'Ecommerce Partial Payment',
    'version': '19.0.1.3.0',
    'category': 'Website/Website',
    'summary': 'Add partial payment option to ecommerce checkout',
    'description': """
        Ecommerce Partial Payment for Odoo 19
        ======================================
        This module adds the ability for customers to make partial payments
        during the ecommerce checkout process.

        Features:
        - Partial payment option on checkout payment page
        - Custom amount input with validation
        - Payment tracking (amount paid / remaining) on sale orders
        - Register manual payments from backend
        - Auto-confirm orders on payment (including wire transfer)
        - View payment transactions from sale order
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'website_sale',
        'payment',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/wizard_views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mew_module/static/src/js/checkout_partial_pay.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
