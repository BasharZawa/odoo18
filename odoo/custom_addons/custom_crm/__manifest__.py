# -*- coding: utf-8 -*-
{
    'name': "Custom CRM",
    'summary': "Short (1 phrase/line) summary of the module's purpose",
    'description': "This module is extending the CRM module to add custom features and functionalities.",
    'author': "SEDCO",
    'website': "https://www.sedco.co",
    'category': 'Tools',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base'],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

