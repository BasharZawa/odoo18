{
    'name': 'Smart Report Builder',
    'version': '18.0.1.0.0',
    'category': 'Reporting',
    'summary': 'AI-powered natural language report builder using Claude',
    'description': """
        Smart Report Builder
        ====================
        Ask for any report in plain English (or Arabic).
        Powered by Claude AI via n8n automation.
        
        Features:
        - Natural language to Odoo read_group queries
        - Auto-detects models and fields from your instance
        - Table + Chart rendering (Chart.js)
        - Export to CSV/Excel
        - Save & reuse report queries
    """,
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/smart_report_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'smart_report_builder/static/src/css/smart_report_builder.css',
            'smart_report_builder/static/src/xml/smart_report_builder.xml',
            'smart_report_builder/static/src/js/smart_report_builder.js',
        ],
    },
    'installable': True,
    'application': True,
    'icon': '/smart_report_builder/static/description/icon.png',
}
