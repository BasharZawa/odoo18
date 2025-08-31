from odoo import models, fields

class BpmTimer(models.Model):
    _name = "bpm.timer"
    _description = "BPM Timer"

    proc_id = fields.Many2one("bpm.process.instance", required=True, ondelete="cascade")
    node_id = fields.Char(required=True)
    due_at = fields.Datetime(required=True, index=True)
    payload = fields.Json(default=dict)
    status = fields.Selection([('scheduled','Scheduled'),('fired','Fired'),('cancelled','Cancelled')], default='scheduled', index=True)
