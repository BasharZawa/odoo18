{
    'name': 'Pilot Orders Management',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage pilot orders with approval workflows',
    'description': """
        Pilot Orders Management
        ======================
        * Trial deliveries without immediate invoicing
        * Sales Manager approval workflow
        * Block invoicing until customer confirmation
        * Convert pilot orders to normal orders
        * Configurable approval workflows
    """,
    'author': 'Emipro Technologies (P) Ltd.',
    'website': 'https://www.emiprotechnologies.com',
    'depends': ['sale_extended_ept', 'approvals'],
    'data': [
        # 'security/pilot_order_security.xml',
        'data/approval_workflow_data.xml',
        'views/sale_order_views.xml',
        'views/crm_tags_views.xml'
    ],
    'assets': {
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
