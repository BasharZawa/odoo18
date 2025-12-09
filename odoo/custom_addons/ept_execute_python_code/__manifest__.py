{
    "name": "Execute Python Code",
    "category": "Hidden/Tools",
    "description": """Installing this module, user will able to execute python code from Odoo""",
    "author": "Emipro Technologies Pvt. Ltd.",
    "version": "18.0.1.0",
    "license": "OPL-1",
    "depends": ["base"],
    "init_xml": [],
    "data": [
        'views/python_code_view.xml',
        'views/cron_code_execute.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'ept_execute_python_code/static/src/css/ept_font.scss'
        ],
    },
    "demo_xml": [],
    "installable": True,
    'application': True,
}
