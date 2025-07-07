# -*- coding: utf-8 -*-
{
    "name": "Odoo Camunda Connector",
    "version": "18.0.1.0.0",
    "summary": "Integrate Odoo with Camunda BPMN Engine using bpmn-js for modeling.",
    "description": """
Odoo Camunda Connector
======================

This module provides integration between Odoo 18 and an external Camunda BPMN engine.

Features:
- Embeds the bpmn-js visual editor for modeling BPMN 2.0 diagrams within Odoo.
- Allows deploying process definitions from Odoo to Camunda via REST API.
- Enables starting Camunda process instances from Odoo.
- Handles Camunda User Tasks within the Odoo interface.
- Implements the External Task Pattern for Odoo to act as a worker for Camunda Service Tasks.
- Requires a running external Camunda instance (Platform 7 or 8).
    """,
    "author": "Manus",
    "website": "",
    "category": "Extra Tools/Integration",
    "depends": ["base", "mail", "web"], # Added web dependency for JS widget
    "data": [
        # Security first
        "security/ir.model.access.csv",
        # Configuration
        "views/camunda_config_settings_views.xml",
        # Core Views
        "views/camunda_workflow_definition_views.xml",
        "views/camunda_user_task_views.xml",
        # Menu Items
        "views/camunda_menus.xml",
        # Data
        "data/ir_cron_data.xml", # For worker polling
    ],
    "assets": {
        "web.assets_backend": [
            # Add bpmn-js library (needs to be downloaded/included)
            # "odoo_camunda_connector/static/lib/bpmn-js/dist/bpmn-modeler.development.js",
            # "odoo_camunda_connector/static/lib/bpmn-js/dist/assets/diagram-js.css",
            # "odoo_camunda_connector/static/lib/bpmn-js/dist/assets/bpmn-font/css/bpmn.css",
            # Custom JS widget
            "odoo_camunda_connector/static/src/js/bpmn_editor_widget.js",
        ],
        "web.assets_qweb": [
            "odoo_camunda_connector/static/src/xml/bpmn_editor_widget.xml",
        ],
    },
    "installable": True,
    "application": False, # It's more of a technical connector
    "auto_install": False,
    "license": "LGPL-3",
}

