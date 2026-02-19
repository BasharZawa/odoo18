{
    'name': 'Purchase Extended Ept',
    'version': '18.0.1.0.0',
    'summary': 'Automated Landed Cost Selection from Vendor Bill',
    'description': """
        This module automates the selection of stock transfers in the Landed Cost process.
        When creating a Landed Cost from a Vendor Bill, it automatically links the correct stock transfers based on the Vendor Bill.
        
        Features:
        - Auto-selects stock transfers (Receipts) related to Purchase Orders on the Vendor Bill.
        - Picks only the latest receipt if multiple exist for a Purchase Order.
        - Excludes transfers already linked to other Landed Costs.
    """,
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'https://www.emiprotechnologies.com',
    'depends': ['stock_landed_costs', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_change_wizard_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_change_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
