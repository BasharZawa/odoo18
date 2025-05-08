{
    'name': 'Request Management',
    'version': '1.0',
    'summary': 'Parent module for managing requests and workflows',
    'description': 'A BPM engine for managing requests and their associated tasks.',
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/x_request_views.xml',
        'views/task_views.xml',
        'views/presales_request_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}