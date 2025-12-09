# -*- coding: utf-8 -*-
{
    'name': "MRP Extended Ept",
    'summary': """Manufacturing Modifications""",
    'description': """Manufacturing related modifications""",
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com/',
    'depends': ['mrp', 'hr', 'mrp_workorder', 'approvals', 'purchase'],
    'data': [
        # 'data/approval_category_rec.xml',
        'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        # 'security/res_groups.xml',
        'views/mrp_workorder.xml',
        # 'views/approval_category.xml',
        # 'views/approval_request.xml',
        'wizards/component_availability_wizard.xml',
        'wizards/scrap_product_confirmation_wizard.xml'
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
