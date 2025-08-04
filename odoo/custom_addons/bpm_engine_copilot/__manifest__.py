# -*- coding: utf-8 -*-
{
    'name': 'BPMN Engine Copilot',
    'version': '18.0.1.0.0',
    'category': 'Business Process Management',
    'sequence': 15,
    'summary': 'Complete BPMN 2.0 Engine for Odoo 18 - Business Process Automation',
    'description': '''
BPMN Engine Copilot
===================

A complete, production-ready BPMN (Business Process Model and Notation) engine for Odoo 18.

Key Features:
* Complete BPMN 2.0 specification support
* Visual process modeling with bpmn-js integration
* Robust execution engine with token-based navigation
* User task management with dynamic forms
* Service task automation with Python execution
* Process monitoring and analytics
* SLA tracking and escalation
* Odoo model integration
* Enterprise-grade security and permissions

This module provides a comprehensive business process management solution
that seamlessly integrates with Odoo's existing functionality.
    ''',
    'website': 'https://www.odoo.com',
    'author': 'Odoo Community',
    'depends': [
        'base',
        'web',
        'mail',
        'auth_signup',
        'base_automation',
        'calendar',
        'contacts',
        'hr',
        'project',
        'resource',
        'portal',
    ],
    'data': [
        # Security
        'security/bmp_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/bmp_demo_data.xml',
        'data/bmp_cron_jobs.xml',
        'data/bmp_email_templates.xml',
        
        # Views
        'views/bmp_process_definition_views.xml',
        'views/bmp_process_instance_views.xml',
        'views/bmp_task_instance_views.xml',
        'views/bmp_activity_log_views.xml',
        'views/bmp_dashboard_views.xml',
        'views/bmp_menus.xml',
        
        # Wizards
        'wizards/bmp_process_start_views.xml',
        'wizards/bmp_task_complete_views.xml',
    ],
    'demo': [
        'data/bmp_demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bmp_engine_copilot/static/src/**/*.js',
            'bmp_engine_copilot/static/src/**/*.xml',
            'bmp_engine_copilot/static/src/**/*.scss',
            'bmp_engine_copilot/static/lib/bpmn-js/**/*.js',
        ],
        'web.assets_frontend': [
            'bmp_engine_copilot/static/src/components/task_dashboard/**/*',
        ],
        'web.assets_tests': [
            'bmp_engine_copilot/static/tests/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['lxml'],
    },
}