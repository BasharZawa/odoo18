# -*- coding: utf-8 -*-
{
    'name': "sedco_management",
    'summary': "A module for managing hospital operations",
    'description': " This module provides a comprehensive solution for managing hospital operations, including patient management, appointment scheduling, and billing. It aims to streamline the workflow of healthcare professionals and improve patient care.",

    'author': "Sedco",
    'website': "https://www.sedco.co",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Tools',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/patient_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

