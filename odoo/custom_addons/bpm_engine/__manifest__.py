{
    'name': "BPMN Workflow Engine",
    'version': "1.0.0",
    'author': "Your Company",
    'category': 'Workflow',
    'summary': "BPMN process engine with graphical modeler and Odoo integration.",
    'depends': ['base', 'web', 'crm'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/action_bpmn_process_definition.xml',
        'views/menus.xml',
        'views/process_definition_views.xml',
        'views/process_instance_views.xml',
        'views/task_views.xml',
        'views/activity_log_views.xml',
        'views/crm_lead_extension.xml',
        'data/crm_lead_approval.bpmn.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bpmn_engine/static/lib/bpmn-modeler.deps.js',
            'bpmn_engine/static/src/js/bpmn_modeler_widget.js',
            'bpmn_engine/static/src/xml/bpmn_modeler_template.xml',
        ],
    },
    'installable': True,
    'application': True,
}
