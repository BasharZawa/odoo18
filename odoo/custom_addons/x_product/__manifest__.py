# -*- coding: utf-8 -*-
{
    'name': "X Product",

    'summary': "This module adds custom product features",

    'description': """
    This module extends the product template with additional fields such as
    Product Line, Product Nature, HS Code, and Country of Origin to enhance
    product management functionalities.
       """,

    'author': "SEDCO",
    'website': "https://www.sedco.co",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Sales/Products',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/x_product_nature_views.xml',
        'views/x_product_line_views.xml',
        'views/product_template_views.xml',
        'views/menu_views.xml',
        'data/product_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}

