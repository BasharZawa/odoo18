# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MetabaseSyncState(models.Model):
    _name = 'metabase.sync.state'
    _description = 'Metabase Sync State'
    _rec_name = 'sync_model_id'

    sync_model_id = fields.Many2one('metabase.sync.model', required=True, ondelete='cascade')
    dashboard_id = fields.Many2one('metabase.dashboard', ondelete='cascade')
    schedule_id = fields.Many2one('metabase.sync.schedule', ondelete='cascade')
    last_synced_at = fields.Datetime()
    last_status = fields.Selection(
        [
            ('success', 'Success'),
            ('failed', 'Failed'),
        ],
        default='success',
    )
    last_message = fields.Char()

    @api.constrains('dashboard_id', 'schedule_id')
    def _check_single_owner(self):
        for state in self:
            owners = bool(state.dashboard_id) + bool(state.schedule_id)
            if owners != 1:
                raise ValidationError("A sync state must belong to exactly one dashboard or schedule.")
