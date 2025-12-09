# -*- coding: utf-8 -*-
{
    'name': 'Customer Management Ept',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Customer contact validation workflow with Finance team approval',
    'description': """
        Customer Contact & Validation Module with Sales Order Scheduling
        
        Features:
        - Unique Customer ID generation for contacts
        - Validation workflow for customer contacts
        - Finance team approval process
        - Field-level access control based on validation status
        - Sales order blocking for unvalidated customers
        - Automatic notifications to Finance team
        - End Customer tracking for license management
        - Invoicing Schedule with milestone-based billing
        - Recognition Schedule for revenue recognition
        - Distribution Schedule for salesperson commission allocation
        - Comprehensive reporting for all schedules
    """,
    'author': 'Emipro Technologies Pvt Ltd',
    'website': 'https://www.emiprotechnologies.com',
    'depends': [
        'vendor_tracking_ept',
        'sale_extended_ept',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/approval_data.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/schedule_reports.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
