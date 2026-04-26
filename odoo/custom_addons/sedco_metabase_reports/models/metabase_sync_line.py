# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


SYNC_MODE_SELECTION = [
    ('full', 'Full Reload'),
    ('incremental', 'Incremental'),
]


class MetabaseSyncLine(models.Model):
    _name = 'metabase.sync.line'
    _description = 'Metabase Sync Model Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    dashboard_id = fields.Many2one('metabase.dashboard', ondelete='cascade')
    schedule_id = fields.Many2one('metabase.sync.schedule', ondelete='cascade')
    sync_model_id = fields.Many2one('metabase.sync.model', required=True, ondelete='cascade')
    sync_mode = fields.Selection(SYNC_MODE_SELECTION, default='full', required=True)
    active = fields.Boolean(related='sync_model_id.active', store=False)

    _sql_constraints = [
        (
            'dashboard_model_unique',
            'unique(dashboard_id, sync_model_id)',
            'Each dashboard can contain a sync model only once.',
        ),
        (
            'schedule_model_unique',
            'unique(schedule_id, sync_model_id)',
            'Each schedule can contain a sync model only once.',
        ),
    ]

    @api.constrains('dashboard_id', 'schedule_id')
    def _check_single_owner(self):
        for line in self:
            owners = bool(line.dashboard_id) + bool(line.schedule_id)
            if owners != 1:
                raise ValidationError("A sync line must belong to exactly one dashboard or schedule.")
