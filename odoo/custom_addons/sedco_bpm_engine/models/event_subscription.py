from odoo import models, fields

class BpmEventSubscription(models.Model):
    _name = "event.subscription"
    _description = "BPM Event Subscription"

    proc_id = fields.Many2one("process.instance", required=True, ondelete="cascade")
    node_id = fields.Char(required=True)
    event_name = fields.Char(required=True)
    correlation_key = fields.Char(required=True, index=True)
    status = fields.Selection([('active','Active'),('consumed','Consumed'),('cancelled','Cancelled')], default='active', index=True)
    created_at = fields.Datetime(default=lambda self: fields.Datetime.now())
