# -*- coding: utf-8 -*-
from odoo import fields, models


class MetabaseSyncModel(models.Model):
    _name = 'metabase.sync.model'
    _description = 'Metabase Sync Model Registry'
    _order = 'name'

    name = fields.Char(
        required=True,
        help="Odoo model technical name, e.g. sale.order. "
             "Must match a key in OdooSyncConfig.MODELS.",
    )
    display = fields.Char(help="Human-readable label shown in the dashboard config form.")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Each Odoo model may only appear once in the sync registry.'),
    ]
