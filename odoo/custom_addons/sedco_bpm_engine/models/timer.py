from odoo import models, fields

class Timer(models.Model):
    _name = "timer"
    _description = "BPM Timer"

    proc_id = fields.Many2one("process.instance", required=True, ondelete="cascade")
    node_id = fields.Char(required=True)
    due_at = fields.Datetime(required=True, index=True)
    payload = fields.Json(default=dict)
    status = fields.Selection([('scheduled','Scheduled'),('fired','Fired'),('cancelled','Cancelled')], default='scheduled', index=True)
