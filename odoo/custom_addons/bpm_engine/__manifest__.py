{
    'name': 'BPM Engine',
    'version': '1.0',
    'summary': 'BPMN Modeler and Workflow Engine',
    'category': 'Tools',
    'depends': ['base', 'web'],
    'data': [
        'views/bpm_process_definition_views.xml',
        'security/ir.model.access.csv'
    ],
    'assets': {
        'web.assets_backend': [
            'bpm_engine/static/src/js/bpmn_modeler.js',
            'bpm_engine/static/src/css/bpmn_modeler.css',
        ],
    },
    'installable': True,
}
