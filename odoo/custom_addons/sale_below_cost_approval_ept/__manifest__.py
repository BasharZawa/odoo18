{
    'name': 'Sale Below Cost Approval Ept',
    'summary': 'Require manager approval when selling below product cost',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'https://emiprotechnologies.com',
    'license': 'LGPL-3',
    'depends': ['sale_extended_ept', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'data/approval_data.xml',
        'views/sale_order_views.xml',
        'wizard/sale_below_cost_wizard_views.xml',
    ],
    'application': False,
    'installable': True,
}
