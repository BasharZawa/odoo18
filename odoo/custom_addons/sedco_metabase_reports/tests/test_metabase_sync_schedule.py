# -*- coding: utf-8 -*-
import json
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


class _FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


@tagged('post_install', '-at_install')
class TestMetabaseSyncSchedule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Schedule = cls.env['metabase.sync.schedule']
        cls.SyncModel = cls.env['metabase.sync.model']
        cls.sale_order_model = cls.env.ref('sedco_metabase_reports.sync_model_sale_order')
        cls.partner_model = cls.env.ref('sedco_metabase_reports.sync_model_res_partner')
        cls.icp = cls.env['ir.config_parameter'].sudo()

    def setUp(self):
        super().setUp()
        self.icp.set_param('sedco_metabase_reports.uxserver_url', 'https://uxserver.example.test')
        self.icp.set_param('sedco_metabase_reports.uxserver_sync_api_key', 'test-key')

    def _create_schedule(self, **values):
        vals = {
            'name': 'Sales warm data',
            'sync_line_ids': [
                (0, 0, {'sync_model_id': self.sale_order_model.id, 'sync_mode': 'full'}),
                (0, 0, {'sync_model_id': self.partner_model.id, 'sync_mode': 'full'}),
            ],
            'interval_number': 15,
            'interval_type': 'minutes',
        }
        vals.update(values)
        return self.Schedule.create(vals)

    def test_action_run_now_posts_selected_models_and_updates_status(self):
        schedule = self._create_schedule()

        with patch(
            'odoo.addons.sedco_metabase_reports.models.metabase_sync_schedule.urllib.request.urlopen',
            return_value=_FakeHTTPResponse({'success': True, 'job_id': 'job-123'}),
        ) as urlopen:
            schedule.action_run_now()

        self.assertEqual(schedule.last_status, 'success')
        self.assertIn('job-123', schedule.last_message)
        self.assertTrue(schedule.last_run)
        self.assertTrue(schedule.next_run)
        self.assertEqual(urlopen.call_count, 1)

        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, 'https://uxserver.example.test/api/OdooSyncReload')
        self.assertEqual(json.loads(request.data.decode()), {'models': ['sale.order', 'res.partner'], 'mode': 'full'})
        self.assertEqual(request.headers['X-api-key'], 'test-key')

    def test_incremental_schedule_posts_mode_and_since_values(self):
        schedule = self._create_schedule(sync_line_ids=[
            (0, 0, {'sync_model_id': self.sale_order_model.id, 'sync_mode': 'incremental'}),
            (0, 0, {'sync_model_id': self.partner_model.id, 'sync_mode': 'incremental'}),
        ])
        self.env['metabase.sync.state'].create({
            'schedule_id': schedule.id,
            'sync_model_id': self.sale_order_model.id,
            'last_synced_at': '2026-04-25 09:00:00',
        })

        with patch(
            'odoo.addons.sedco_metabase_reports.models.metabase_sync_schedule.urllib.request.urlopen',
            return_value=_FakeHTTPResponse({'success': True, 'job_id': 'job-456'}),
        ) as urlopen:
            schedule.action_run_now()

        request = urlopen.call_args[0][0]
        body = json.loads(request.data.decode())
        self.assertEqual(body['mode'], 'incremental')
        self.assertEqual(body['models'], ['sale.order', 'res.partner'])
        self.assertIn('sale.order', body['since'])
        self.assertNotIn('res.partner', body['since'])

    def test_cron_runs_only_active_due_schedules(self):
        due = self._create_schedule(next_run=fields.Datetime.now())
        future = self._create_schedule(
            name='Future sync',
            next_run=fields.Datetime.add(fields.Datetime.now(), hours=1),
        )
        inactive = self._create_schedule(name='Inactive sync', active=False, next_run=fields.Datetime.now())

        with patch.object(
            self.Schedule.__class__,
            '_request_uxserver_sync',
            return_value=(True, 'ok', {}),
        ) as sync:
            self.Schedule._cron_run_due_schedules()

        self.assertEqual(sync.call_count, 1)
        sync_model_names = sync.call_args[0][0]
        self.assertEqual(sync_model_names, ['sale.order', 'res.partner'])
        self.assertEqual(sync.call_args.kwargs['mode'], 'full')
        self.assertEqual(due.last_status, 'success')
        self.assertEqual(future.last_status, 'never')
        self.assertEqual(inactive.last_status, 'never')

    def test_dashboard_incremental_sync_uses_dashboard_state(self):
        dashboard = self.env.ref('sedco_metabase_reports.dashboard_sales_orders')
        dashboard.write({
            'open_sync_mode': 'incremental',
            'sync_model_ids': [(6, 0, [self.sale_order_model.id])],
            'sync_line_ids': [
                (5, 0, 0),
                (0, 0, {'sync_model_id': self.sale_order_model.id, 'sync_mode': 'incremental'}),
            ],
        })
        self.env['metabase.sync.state'].create({
            'dashboard_id': dashboard.id,
            'sync_model_id': self.sale_order_model.id,
            'last_synced_at': '2026-04-25 08:00:00',
        })

        with patch(
            'odoo.addons.sedco_metabase_reports.models.metabase_sync_schedule.urllib.request.urlopen',
            return_value=_FakeHTTPResponse({'success': True, 'job_id': 'job-dashboard'}),
        ) as urlopen:
            success, message = dashboard._run_dashboard_sync()

        self.assertTrue(success)
        self.assertIn('job-dashboard', message)
        body = json.loads(urlopen.call_args[0][0].data.decode())
        self.assertEqual(body['mode'], 'incremental')
        self.assertEqual(body['models'], ['sale.order'])
        self.assertIn('sale.order', body['since'])

    def test_schedule_can_mix_full_and_incremental_models(self):
        schedule = self.Schedule.create({
            'name': 'Mixed sales warm data',
            'interval_number': 15,
            'interval_type': 'minutes',
            'sync_line_ids': [
                (0, 0, {'sync_model_id': self.sale_order_model.id, 'sync_mode': 'full'}),
                (0, 0, {'sync_model_id': self.partner_model.id, 'sync_mode': 'incremental'}),
            ],
        })
        self.env['metabase.sync.state'].create({
            'schedule_id': schedule.id,
            'sync_model_id': self.partner_model.id,
            'last_synced_at': '2026-04-25 09:00:00',
        })

        with patch(
            'odoo.addons.sedco_metabase_reports.models.metabase_sync_schedule.urllib.request.urlopen',
            return_value=_FakeHTTPResponse({'success': True, 'job_id': 'job-mixed'}),
        ) as urlopen:
            schedule.action_run_now()

        bodies = [json.loads(call.args[0].data.decode()) for call in urlopen.call_args_list]
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn({'models': ['sale.order'], 'mode': 'full'}, bodies)
        incremental_body = next(body for body in bodies if body['mode'] == 'incremental')
        self.assertEqual(incremental_body['models'], ['res.partner'])
        self.assertIn('res.partner', incremental_body['since'])

    def test_dashboard_can_mix_full_and_incremental_models(self):
        dashboard = self.env.ref('sedco_metabase_reports.dashboard_sales_orders')
        dashboard.write({
            'open_sync_mode': 'none',
            'sync_model_ids': [(5, 0, 0)],
            'sync_line_ids': [
                (5, 0, 0),
                (0, 0, {'sync_model_id': self.sale_order_model.id, 'sync_mode': 'full'}),
                (0, 0, {'sync_model_id': self.partner_model.id, 'sync_mode': 'incremental'}),
            ],
        })
        self.env['metabase.sync.state'].create({
            'dashboard_id': dashboard.id,
            'sync_model_id': self.partner_model.id,
            'last_synced_at': '2026-04-25 10:00:00',
        })

        with patch(
            'odoo.addons.sedco_metabase_reports.models.metabase_sync_schedule.urllib.request.urlopen',
            return_value=_FakeHTTPResponse({'success': True, 'job_id': 'job-dashboard-mixed'}),
        ) as urlopen:
            success, message = dashboard._run_dashboard_sync()

        self.assertTrue(success)
        self.assertIn('job-dashboard-mixed', message)
        bodies = [json.loads(call.args[0].data.decode()) for call in urlopen.call_args_list]
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn({'models': ['sale.order'], 'mode': 'full'}, bodies)
        incremental_body = next(body for body in bodies if body['mode'] == 'incremental')
        self.assertEqual(incremental_body['models'], ['res.partner'])
        self.assertIn('res.partner', incremental_body['since'])

    def test_dashboard_ignores_hidden_legacy_sync_models(self):
        dashboard = self.env.ref('sedco_metabase_reports.dashboard_sales_orders')
        dashboard.write({
            'open_sync_mode': 'full',
            'sync_model_ids': [(6, 0, [self.sale_order_model.id])],
            'sync_line_ids': [(5, 0, 0)],
        })

        with patch(
            'odoo.addons.sedco_metabase_reports.models.metabase_sync_schedule.urllib.request.urlopen',
            return_value=_FakeHTTPResponse({'success': True, 'job_id': 'should-not-run'}),
        ) as urlopen:
            success, message = dashboard._run_dashboard_sync()

        self.assertTrue(success)
        self.assertEqual(message, 'No dashboard sync models selected.')
        self.assertEqual(urlopen.call_count, 0)

    def test_schedule_requires_visible_sync_lines(self):
        with self.assertRaises(Exception):
            self.Schedule.create({
                'name': 'Legacy-only schedule',
                'sync_model_ids': [(6, 0, [self.sale_order_model.id])],
                'interval_number': 15,
                'interval_type': 'minutes',
            })

    def test_dashboard_deduplicates_repeated_sync_failure_messages(self):
        dashboard = self.env.ref('sedco_metabase_reports.dashboard_sales_orders')
        dashboard.write({
            'sync_model_ids': [(5, 0, 0)],
            'sync_line_ids': [
                (5, 0, 0),
                (0, 0, {'sync_model_id': self.sale_order_model.id, 'sync_mode': 'full'}),
                (0, 0, {'sync_model_id': self.partner_model.id, 'sync_mode': 'incremental'}),
            ],
        })

        with patch.object(
            self.Schedule.__class__,
            '_request_uxserver_sync',
            return_value=(False, 'UXServer sync timed out or could not be reached.', {}),
        ):
            success, message = dashboard._run_dashboard_sync()

        self.assertFalse(success)
        self.assertEqual(message, 'UXServer sync timed out or could not be reached.')

    def test_request_uxserver_sync_rejects_url_without_http_scheme(self):
        self.icp.set_param('sedco_metabase_reports.uxserver_url', 'localhost:8052/')

        success, message, payload = self.Schedule._request_uxserver_sync(['res.partner'])

        self.assertFalse(success)
        self.assertEqual(payload, {})
        self.assertIn('must start with http:// or https://', message)
