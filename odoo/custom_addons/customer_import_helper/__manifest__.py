# -*- coding: utf-8 -*-
{
    'name': 'Import Helper',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Temporary module to allow importing readonly fields',
    'description': """
        This module temporarily enables importing readonly fields:
        
        res.partner:
        - customer_id
        - validation_date
        - validated_by
        
        stock.quant:
        - in_date (Incoming Date)
        
        Install before import, uninstall after import is complete.
    """,
    'author': 'SEDCO',
    'depends': ['customer_management_ept', 'stock'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
