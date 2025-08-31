from odoo import models, fields, api, _
from odoo.tools import html_escape

class BpmProcessInstance(models.Model):
    _name = "bpm.process.instance"
    _description = "BPM Process Instance"
    _inherit = ['mail.thread']

    definition_id = fields.Many2one("bpm.process.definition", required=True, ondelete="restrict")
    business_key = fields.Char(index=True)
    status = fields.Selection([('running','Running'),('done','Done'),('failed','Failed')], default='running', tracking=True)
    ctx_json = fields.Json(default=dict, help="Business context carried through the process.")
    activity_ids = fields.One2many("bpm.activity.instance", "proc_id", string="Activities")

    def post_note(self, msg):
        for rec in self:
            rec.message_post(body=html_escape(msg))

    def mark_done(self):
        self.write({'status': 'done'})
        self.post_note("Process completed.")

    def mark_failed(self, error):
        self.write({'status': 'failed'})
        self.post_note("Process failed: %s" % error)
