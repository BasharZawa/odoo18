# -*- coding: utf-8 -*-
{
    'name': "Custom CRM",
    'summary': "Extended of CRM to bridge the gaps ",
    'description': "This module is extending the CRM module to add custom features and functionalities.",
    'author': "SEDCO",
    'website': "https://www.sedco.co",
    'category': 'Tools',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'sale'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/contact_views.xml',
        'reports/QuoteReport.xml',
        'reports/QuoteReportTemplate.xml',
        'views/sale_order_report_button.xml',
        'data/crm_stage_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_crm/static/src/components/listView/listView.js',
            'custom_crm/static/src/components/listView/listView.css',
            'custom_crm/static/src/components/listView/listView.xml',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

