{
    "name": "Quotation Management",
    "version": "1.0",
    "author": "SEDCO",
    "depends": ["sale_management", "crm", "mail"],
    "data": [
        "security/quotation_security.xml",  # must come first!
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/sale_order_line_views.xml",
        "views/discount_approval_profile_views.xml",
        "views/sale_order_line_filter_views.xml"
    ],
    "installable": True,
    "application": False
}

