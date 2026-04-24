# -*- coding: utf-8 -*-
from odoo import fields, models


class MetabaseDashboard(models.Model):
    _name = 'metabase.dashboard'
    _description = 'Embedded Metabase Dashboard'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help="Stable route key used in /metabase/embed/<code>. "
             "Portable across environments — never reuse or renumber.",
    )
    metabase_id = fields.Integer(
        default=0,
        help="Numeric ID of the dashboard in the Metabase application DB. "
             "Set to 0 until the Metabase dashboard is published.",
    )
    allowed_group_ids = fields.Many2many(
        'res.groups',
        'metabase_dashboard_group_rel',
        'dashboard_id', 'group_id',
        string='Allowed Groups',
        required=True,
    )
    filter_mode = fields.Selection(
        [
            ('none', 'No filter'),
            ('salesperson', 'Owner (always filter by current user)'),
            ('salesperson_bypass_manager', 'Owner (bypass for managers)'),
        ],
        default='none',
        required=True,
    )
    locked_parameter_name = fields.Char(
        default='owner_id',
        help="Name of the locked Metabase parameter sent in the embed JWT. "
             "Use the same name in the SQL variable, dashboard filter slug, "
             "and Metabase embed parameter. Examples: owner_id, salesperson_id, assigned_user_id.",
    )
    bypass_group_id = fields.Many2one(
        'res.groups',
        help="Only used by bypass filter modes. "
             "Users in this group receive an empty locked-param array, "
             "effectively disabling the row-level filter.",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    # Stage E — on-demand sync
    sync_model_ids = fields.Many2many(
        'metabase.sync.model',
        'metabase_dashboard_sync_model_rel',
        'dashboard_id', 'sync_model_id',
        string='Models to refresh on open',
        help="Odoo models synced to SQL Server before this dashboard's embed is rendered. "
             "Leave empty to skip on-demand sync (e.g. Migration KPIs, Sync Health).",
    )
    sync_timeout_seconds = fields.Integer(
        default=25,
        help="Maximum seconds to wait for UXServer to complete the sync. "
             "On timeout the iframe still renders with a stale-data warning.",
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Dashboard code must be unique.'),
    ]
