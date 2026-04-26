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
    open_sync_mode = fields.Selection(
        [
            ('none', 'No sync on open'),
            ('full', 'Use per-model sync rules'),
            ('incremental', 'Legacy incremental sync'),
        ],
        default='full',
        required=True,
        help="Technical fallback mode. Use sync rules to choose full or incremental sync per model.",
    )
    sync_model_ids = fields.Many2many(
        'metabase.sync.model',
        'metabase_dashboard_sync_model_rel',
        'dashboard_id', 'sync_model_id',
        string='Legacy models to refresh on open',
        help="Odoo models synced to SQL Server before this dashboard's embed is rendered. "
             "Leave empty to skip on-demand sync (e.g. Migration KPIs, Sync Health).",
    )
    sync_line_ids = fields.One2many(
        'metabase.sync.line',
        'dashboard_id',
        string='Models to refresh on open',
        help="Preferred production setup: choose each model and whether it uses full or incremental sync.",
    )
    sync_timeout_seconds = fields.Integer(
        default=25,
        help="Maximum seconds to wait for UXServer to complete the sync. "
             "On timeout the iframe still renders with a stale-data warning.",
    )

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Dashboard code must be unique.'),
    ]

    def _sync_state_domain(self, sync_model):
        self.ensure_one()
        return [
            ('dashboard_id', '=', self.id),
            ('sync_model_id', '=', sync_model.id),
        ]

    def _get_sync_since_by_model(self):
        self.ensure_one()
        since = {}
        State = self.env['metabase.sync.state'].sudo()
        for sync_model in self._get_sync_groups().get('incremental', self.env['metabase.sync.model']):
            state = State.search(self._sync_state_domain(sync_model), limit=1)
            if state.last_synced_at:
                since[sync_model.name] = fields.Datetime.to_string(state.last_synced_at)
        return since

    def _mark_sync_success(self, sync_models, synced_at, message=None):
        self.ensure_one()
        State = self.env['metabase.sync.state'].sudo()
        for sync_model in sync_models:
            state = State.search(self._sync_state_domain(sync_model), limit=1)
            values = {
                'dashboard_id': self.id,
                'sync_model_id': sync_model.id,
                'last_synced_at': synced_at,
                'last_status': 'success',
                'last_message': message,
            }
            if state:
                state.write(values)
            else:
                State.create(values)

    def _get_sync_groups(self):
        self.ensure_one()
        SyncModel = self.env['metabase.sync.model']
        groups = {
            'full': SyncModel.browse(),
            'incremental': SyncModel.browse(),
        }
        lines = self.sync_line_ids.filtered(lambda line: line.sync_model_id.active)
        if lines:
            for line in lines:
                groups[line.sync_mode] |= line.sync_model_id
        return groups

    def _run_dashboard_sync(self):
        self.ensure_one()
        sync_groups = self._get_sync_groups()
        sync_models = sync_groups['full'] | sync_groups['incremental']
        if not sync_models:
            return True, 'No dashboard sync models selected.'

        started_at = fields.Datetime.now()
        since = self._get_sync_since_by_model()
        messages = []
        all_success = True
        Schedule = self.env['metabase.sync.schedule'].sudo()
        for mode in ('full', 'incremental'):
            mode_models = sync_groups[mode]
            if not mode_models:
                continue
            success, message, _payload = Schedule._request_uxserver_sync(
                mode_models.mapped('name'),
                self.sync_timeout_seconds,
                mode=mode,
                since_by_model=since if mode == 'incremental' else {},
            )
            messages.append(message)
            if success:
                self._mark_sync_success(mode_models, started_at, message)
            else:
                all_success = False
        message = Schedule._join_sync_messages(messages)
        return all_success, message
