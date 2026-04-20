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
            ('salesperson', 'Salesperson (always filter by user)'),
            ('salesperson_bypass_manager', 'Salesperson (bypass for managers)'),
        ],
        default='none',
        required=True,
    )
    bypass_group_id = fields.Many2one(
        'res.groups',
        help="Only used when filter_mode = salesperson_bypass_manager. "
             "Users in this group receive an empty locked-param array, "
             "effectively disabling the row-level filter.",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Dashboard code must be unique.'),
    ]
