{
    "name": "Serial Quality Inspection (Vendor Receipt)",
    "version": "18.0.1.0.0",
    "category": "Inventory/Quality",
    "summary": "Serial-based quality gate for vendor receipts",
    "depends": [
        "stock",
        "purchase",
        "quality",
        "barcodes"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/serial_quality_wizard_view.xml",
        "views/stock_picking_view.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "quality_serial_receipt/static/src/js/serial_quality_scan.js"
        ]
    },
    "installable": True,
    "application": False
}
