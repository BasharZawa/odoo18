{
    "name": "Sale Extended EPT",
    "summary": "Put sale orders On Hold if customer has overdue invoices; approval required to confirm.",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "http://www.emiprotechnologies.com/",
    "author": "Emipro Technologies Pvt. Ltd.",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "depends": [
        "sale_management",
        "account",
        "approvals",
    ],
    "data": [
        "data/approval_category_data.xml",
        "views/sale_order_views.xml",
    ],
}
