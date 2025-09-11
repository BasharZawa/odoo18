{
    "name": "SEDCO BPM Engine (EE18)",
    "summary": "Durable workflow engine with BPMN modeler, human tasks, timers, events, branching, joins, and outbox",
    "version": "18.0.6.0.0",
    "category": "Productivity/Workflow",
    "license": "LGPL-3",
    "author": "SEDCO + ChatGPT",
    "website": "https://sedco.com",
    "depends": ["base", "mail", "web", "base_automation", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/process_definition_views.xml",
        "views/process_definition_activity_views.xml",
        "views/bpm_role_views.xml",
        "views/process_instance_views.xml",
        "views/activity_instance_views.xml",
        "views/outbox_views.xml",
        "views/registry_views.xml",
        "views/menu.xml",
        "templates/bpmn_editor.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sedco_bpm_engine/static/src/js/bpm_registry.js",
            "sedco_bpm_engine/static/src/js/bpmn_editor.js",
            "sedco_bpm_engine/static/lib/bpmn-modeler.development.js",
            "sedco_bpm_engine/static/lib/bpmn-js/dist/assets/diagram-js.css",
            "sedco_bpm_engine/static/lib/bpmn-js/dist/assets/bpmn-font/css/bpmn.css"
        ]
    },
    "installable": True,
    "application": True
}
