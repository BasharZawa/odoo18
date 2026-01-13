{
    "name": "Quality Bulk Pass / Fail",
    "version": "18.0.1.0.0",
    "category": "Quality",
    "summary": "Bulk Pass / Fail actions for Quality Checks",
    "depends": [
        "quality",
        "stock",
        "purchase"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/quality_check_view.xml",
        "wizard/quality_check_bulk_wizard.xml",
    ],
    "installable": True,
    "application": False,
}
