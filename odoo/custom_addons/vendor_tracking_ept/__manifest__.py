# -*- coding: utf-8 -*-
{
    'name': 'Vendor Tracking EPT',
    'version': '18.0.1.0.0',
    'website': 'https://www.emiprotechnologies.com',
    'category': 'Contacts',
    'summary': 'Custom Vendor Code tracking with sequence and report display',
    'description': 'Adds Contact Type and auto-generated immutable Vendor Code visible across documents.',
    'author': 'Emipro Technologies (P) Ltd.',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'account', 'purchase'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/res_partner_views.xml',
        'views/account_journal.xml',
        'views/purchase_order.xml',
        'views/res_country.xml',
    ],
    'installable': True,
    'application': False,
}