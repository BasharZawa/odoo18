# -*- coding: utf-8 -*-

{
    'name': 'Account Extended Ept',
    'category': 'Accounting/Accounting',
    'license': 'OPL-1',
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    'summary': """Extended version of Accounting module""",
    'depends': ['base', 'account', 'web'],
    'data': [
        'report/account_invoice_custom_report.xml',
        'views/res_company.xml',
        "views/res_partner_views.xml",
    ],
    'installable': True,
    'images': ['static/description/icon.png']
}
