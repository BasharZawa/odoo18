{
    'name': 'Odoo Backdate Toolkit – Sales, Purchase, Inventory, Accounting, MRP',
    'version': '18.0',
    'category': 'Extra Tools',
    'author': 'SuitePark Info Tech',
    'website': 'suitepark.com',
    'category': 'Extra Tools',
    'summary': 'Backdate confirmation for Sales, Purchase, Accounting, MRP & Inventory. Supports mass backdating, custom backdate, invoice & bill backdate, stock & product move backdate, internal transfer, and more.',
    'description': """
        Manage & Modify Effective Dates Across Odoo Modules

        This module enables users to set and modify backdates for Sales, Purchase, Accounting, MRP, and Inventory operations. Whether you need to backdate invoices, bills, stock transfers, or manufacturing records, this tool provides a seamless, one-click solution with detailed remarks.

        Key Features:
        Mass Backdate Assignments – Change effective dates across multiple records in one click.
        Sales & Purchase Backdate – Backdate sales orders (SO), quotations, and purchase orders (PO).
        Accounting Backdate – Modify invoices, bills, payments, credit & debit notes.
        Inventory & Stock Backdate – Adjust stock moves, product moves, internal transfers, deliveries, and incoming orders.
        MRP & Manufacturing Backdate – Update production and manufacturing records with custom effective dates.
        Backdate with Remarks – Ensure clear tracking with date-based remarks.
        Seamless Journal Entry Updates – Reflects backdated changes in journal entries.

        This module is perfect for businesses that require accurate historical data adjustments in Odoo while maintaining full transparency.

        Enhance your control over effective dates and streamline your Odoo operations today!
    """,
    'depends': [
        'stock','account','sale','purchase'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/backdate_wiz_view.xml',
        'views/backdate_action.xml'
    ],
    'license': 'AGPL-3',
    'images': ['static/description/banner_dark.png'],
    'price': 50.78,
    'currency': 'USD',
    'auto_install': False,
    'installable': True,
    'application': True,
}
