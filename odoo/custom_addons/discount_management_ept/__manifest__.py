# -*- coding: utf-8 -*-
{
    'name': 'Discount Management EPT',
    'version': '18.0.1.0.0',
    'summary': 'Role-based discount limits, approvals, and SO blocking',
    'description': 'Manage discounts by job position with approval escalation and sales order blocking until approved.',
    'author': 'Emipro Technologies Pvt. Ltd.',
    'license': 'LGPL-3',
    'depends': ['sale_extended_ept', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/approval_data.xml',
        'views/hr_job_views.xml',
        'views/sale_order_views.xml',
        'views/discount_allocation_views.xml',
        'views/approval_request_views.xml',
    ],
    'installable': True,
    'application': False,
}
