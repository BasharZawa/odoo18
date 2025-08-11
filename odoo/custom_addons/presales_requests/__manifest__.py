{
    'name': 'Presales Request Management',
    'version': '1.0',
    'category': 'CRM',
    'summary': 'Manage presales requests linked to CRM opportunities',
    'depends': ['crm', 'mail', 'hr_timesheet'],
    'data': [
        'security/presales_security.xml',
        'security/ir.model.access.csv',
        'views/presales_request_views.xml',
        'views/crm_lead_views.xml',
        'data/presales_request_cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}