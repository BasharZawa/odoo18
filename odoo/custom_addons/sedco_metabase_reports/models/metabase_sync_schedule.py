# -*- coding: utf-8 -*-
import json
import logging
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MetabaseSyncSchedule(models.Model):
    _name = 'metabase.sync.schedule'
    _description = 'Metabase Scheduled Sync Job'
    _order = 'active desc, next_run, name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sync_mode = fields.Selection(
        [
            ('full', 'Full Reload'),
            ('incremental', 'Incremental'),
        ],
        default='full',
        required=True,
        string='Default Sync Mode',
        help="Used for legacy model tags. Sync lines can override the mode per model.",
    )
    sync_model_ids = fields.Many2many(
        'metabase.sync.model',
        'metabase_sync_schedule_model_rel',
        'schedule_id',
        'sync_model_id',
        string='Legacy models to refresh',
        help="Backward-compatible model list. Prefer sync lines to choose full/incremental per model.",
    )
    sync_line_ids = fields.One2many(
        'metabase.sync.line',
        'schedule_id',
        string='Models to refresh',
        help="Preferred production setup: choose each model and whether it uses full or incremental sync.",
    )
    interval_number = fields.Integer(default=15, required=True)
    interval_type = fields.Selection(
        [
            ('minutes', 'Minutes'),
            ('hours', 'Hours'),
            ('days', 'Days'),
        ],
        default='minutes',
        required=True,
    )
    next_run = fields.Datetime(default=fields.Datetime.now, required=True)
    sync_timeout_seconds = fields.Integer(
        default=120,
        required=True,
        help="Maximum seconds to wait for UXServer to accept/complete this sync request.",
    )
    last_run = fields.Datetime(readonly=True, copy=False)
    last_status = fields.Selection(
        [
            ('never', 'Never Run'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
        ],
        default='never',
        readonly=True,
        copy=False,
    )
    last_message = fields.Text(readonly=True, copy=False)
    last_duration_seconds = fields.Float(readonly=True, copy=False)

    _sql_constraints = [
        ('interval_number_positive', 'check(interval_number > 0)', 'Interval must be greater than zero.'),
        ('sync_timeout_positive', 'check(sync_timeout_seconds > 0)', 'Sync timeout must be greater than zero.'),
    ]

    def _validate_visible_sync_lines(self):
        for schedule in self:
            if not schedule.sync_line_ids:
                raise ValidationError(_("Select at least one model to refresh."))

    @api.constrains('sync_line_ids')
    def _check_sync_model_ids(self):
        self._validate_visible_sync_lines()

    @api.model_create_multi
    def create(self, vals_list):
        schedules = super().create(vals_list)
        schedules._validate_visible_sync_lines()
        return schedules

    def write(self, vals):
        result = super().write(vals)
        if 'sync_line_ids' in vals or vals.get('active') is True:
            self._validate_visible_sync_lines()
        return result

    def _next_run_after(self, base_dt=None):
        self.ensure_one()
        base_dt = fields.Datetime.to_datetime(base_dt or fields.Datetime.now())
        return fields.Datetime.add(base_dt, **{self.interval_type: self.interval_number})

    def _sync_state_domain(self, sync_model):
        self.ensure_one()
        return [
            ('schedule_id', '=', self.id),
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
                'schedule_id': self.id,
                'sync_model_id': sync_model.id,
                'last_synced_at': synced_at,
                'last_status': 'success',
                'last_message': message,
            }
            if state:
                state.write(values)
            else:
                State.create(values)

    @api.model
    def _join_sync_messages(self, messages):
        unique_messages = []
        for message in messages:
            if message and message not in unique_messages:
                unique_messages.append(message)
        return ' '.join(unique_messages)

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

    def action_run_now(self):
        for schedule in self:
            schedule._run_schedule()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Scheduled Sync'),
                'message': _('Sync job executed. Check the status fields for details.'),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _cron_run_due_schedules(self):
        now = fields.Datetime.now()
        schedules = self.sudo().search([
            ('active', '=', True),
            ('next_run', '<=', now),
        ])
        for schedule in schedules:
            try:
                schedule._run_schedule()
            except Exception as exc:
                _logger.exception("Scheduled Metabase sync crashed for %s", schedule.name)
                schedule.write({
                    'last_run': now,
                    'last_status': 'failed',
                    'last_message': _("Unexpected sync error: %s") % exc,
                    'next_run': schedule._next_run_after(now),
                })
        return True

    def _run_schedule(self):
        self.ensure_one()
        started_at = fields.Datetime.now()
        start_time = time.monotonic()
        sync_groups = self._get_sync_groups()
        sync_models = sync_groups['full'] | sync_groups['incremental']

        if not sync_models:
            self.write({
                'last_run': started_at,
                'last_status': 'skipped',
                'last_message': _('No active sync models selected.'),
                'last_duration_seconds': 0.0,
                'next_run': self._next_run_after(started_at),
            })
            return False

        since = self._get_sync_since_by_model()
        messages = []
        success = True
        for mode in ('full', 'incremental'):
            mode_models = sync_groups[mode]
            if not mode_models:
                continue
            mode_success, message, _payload = self._request_uxserver_sync(
                mode_models.mapped('name'),
                self.sync_timeout_seconds,
                mode=mode,
                since_by_model=since if mode == 'incremental' else {},
            )
            messages.append(message)
            if mode_success:
                self._mark_sync_success(mode_models, started_at, message)
            else:
                success = False
        message = self._join_sync_messages(messages)
        self.write({
            'last_run': started_at,
            'last_status': 'success' if success else 'failed',
            'last_message': message,
            'last_duration_seconds': round(time.monotonic() - start_time, 3),
            'next_run': self._next_run_after(started_at),
        })
        return success

    @api.model
    def _request_uxserver_sync(self, model_names, timeout_seconds=25, mode='full', since_by_model=None):
        model_names = [name for name in model_names if name]
        if not model_names:
            return True, _('No models selected for sync.'), {}

        ICP = self.env['ir.config_parameter'].sudo()
        uxserver_url = (ICP.get_param('sedco_metabase_reports.uxserver_url') or '').strip()
        api_key = (ICP.get_param('sedco_metabase_reports.uxserver_sync_api_key') or '').strip()
        if not uxserver_url or not api_key:
            return False, _('UXServer sync is not configured.'), {}
        parsed_url = urlparse(uxserver_url)
        if parsed_url.scheme not in ('http', 'https') or not parsed_url.netloc:
            return False, _('UXServer URL must start with http:// or https://.'), {}

        url = uxserver_url.rstrip('/') + '/api/OdooSyncReload'
        payload = {
            'models': model_names,
            'mode': mode,
        }
        if mode == 'incremental':
            payload['since'] = since_by_model or {}
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-API-KEY': api_key,
            },
            method='POST',
        )
        timeout = max(1, int(timeout_seconds or 25))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw_response = response.read() or b''
        except urllib.error.HTTPError as exc:
            _logger.warning("UXServer sync failed with HTTP %s: %s", exc.code, exc.reason)
            return False, _("UXServer sync failed (HTTP %s).") % exc.code, {}
        except Exception as exc:
            _logger.warning("UXServer sync error: %s", exc)
            return False, _('UXServer sync timed out or could not be reached.'), {}

        if not raw_response:
            return True, _('Sync request sent successfully.'), {}

        try:
            response_payload = json.loads(raw_response.decode())
        except ValueError:
            return True, _('Sync request sent successfully.'), {}

        if isinstance(response_payload, dict) and response_payload.get('success') is False:
            return False, response_payload.get('error') or response_payload.get('message') or _('UXServer reported sync failure.'), response_payload

        if isinstance(response_payload, dict):
            failed_results = [
                result for result in response_payload.get('results', [])
                if isinstance(result, dict) and result.get('status') not in ('done', 'success')
            ]
            if failed_results:
                return False, _('One or more models failed to sync.'), response_payload

            job_id = response_payload.get('job_id')
            completed_at = response_payload.get('completed_at')
            if job_id and completed_at:
                return True, _('Sync completed. Job: %s. Completed at: %s') % (job_id, completed_at), response_payload
            if job_id:
                return True, _('Sync completed. Job: %s') % job_id, response_payload

        return True, _('Sync request sent successfully.'), response_payload if isinstance(response_payload, dict) else {}
