{
    'name': 'BPM Engine',
    'version': '1.0',
    'summary': 'BPMN Modeler and Workflow Engine',
    'category': 'Tools',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/bpm_process_definition_views.xml',
        'views/bpmn_editor_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bpm_engine/static/lib/bpmn-js/bpmn-modeler.development.js',
            'bpm_engine/static/src/js/field_bpmn_editor.js',
            'bpm_engine/static/src/css/bpmn_modeler.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,  
    'license': 'LGPL-3',
}
