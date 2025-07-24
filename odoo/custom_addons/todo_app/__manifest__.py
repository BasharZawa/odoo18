{
    'name': 'To-Do App',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Simple To-Do Task Management Application',
    'description': """
        To-Do App
        =========
        
        A simple and efficient to-do task management application for Odoo.
        
        Features:
        ---------
        * Create and manage tasks
        * Mark tasks as completed
        * Organize tasks by priority
        * Track task progress
        * User-friendly interface
        
        This module provides a clean and intuitive way to manage daily tasks
        and improve productivity within the Odoo environment.
    """,
    'author': 'SEDCO',
    'website': 'https://www.sedco.co',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/todo_task_view.xml',
        'views/todo_menus.xml',
        'reports/todo_report.xml',
    ],
    'demo': [
        # 'demo/todo_demo.xml',
    ],
    'assets': {
        # 'web.assets_backend': [
        #     'to_do_app/static/src/css/todo_style.css',
        #     'to_do_app/static/src/js/todo_widget.js',
        # ],
    },
    'images': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}
