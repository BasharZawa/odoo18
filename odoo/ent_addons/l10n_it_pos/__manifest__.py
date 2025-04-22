# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - Point of Sale',
    'version': '1.0',
    'description': '''Integration of Odoo PoS with the Italian Fiscal Printer''',
    'category': 'Accounting/Localizations/Point of Sale',
    'auto_install': True,
    'depends': [
        'l10n_it',
        'point_of_sale'
    ],
    'data': [
        'views/pos_payment_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_it_pos/static/src/**/*',
        ],
        'web.assets_tests': [
            'l10n_it_pos/static/tests/tours/**/*',
        ],
        'web.assets_frontend': [
            'l10n_it_pos/static/src/app/overrides/helpers/account_tax.js',
        ],
    },
    'license': 'OEEL-1',
}
