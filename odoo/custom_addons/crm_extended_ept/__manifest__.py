# -*- coding: utf-8 -*-
{
    'name': 'CRM Extended Ept',
    'category': 'Sales/CRM',
    'license': 'OPL-1',
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',
    'summary': """Extended version of CRM module""",
    'depends': ['base', 'crm', 'product', 'sale', 'purchase', 'account_accountant', 'stock',
                'mrp_extended_ept'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_line.xml',
        'views/product_nature.xml',
        'views/product.xml',
        'views/sale_order.xml',
        'views/purchase_order.xml',
        'views/stock_move.xml',
        'views/mrp_production.xml',
        'views/account_move.xml',

        'report/sale_report.xml',
        'report/purchase_report.xml',
        'report/account_move_report.xml',
        'report/stock_picking_report.xml'
    ],
    'installable': True,
    'images': ['static/description/icon.png']
}
