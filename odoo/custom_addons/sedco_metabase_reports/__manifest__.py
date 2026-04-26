# -*- coding: utf-8 -*-
{
    'name': 'SEDCO Metabase Reports',
    'version': '18.0.5.0.0',
    'category': 'Reporting',
    'summary': 'Embed Metabase dashboards inside Odoo with per-user permissions',
    'description': """
SEDCO Metabase Reports
======================

Surfaces Metabase dashboards inside Odoo under a dedicated **Reports** menu,
with two permission layers:

1. Menu-level access — Odoo res.groups gate each report entry.
2. Row-level access — a short-lived signed JWT with locked parameters filters
   dashboard data to the current Odoo user (e.g. a salesperson sees only
   their own orders).

Uses Metabase OSS signed static embedding; no Pro/Enterprise features required.
    """,
    'author': 'SEDCO',
    'depends': ['base', 'web'],
    'data': [
        'security/metabase_groups.xml',
        'security/ir.model.access.csv',
        'views/metabase_templates.xml',
        'views/metabase_dashboard_views.xml',
        'views/metabase_sync_schedule_views.xml',
        'views/menus.xml',
        'data/ir_config_parameter.xml',
        'data/metabase_sync_schedule_cron.xml',
        'data/metabase_sync_models.xml',
        'data/metabase_dashboards.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
