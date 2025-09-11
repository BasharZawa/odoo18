from odoo import models, fields, _
from odoo.exceptions import UserError

class BpmOutbox(models.Model):
    _name = "outbox"
    _description = "BPM Outbox (exactly-once effects)"

    kind = fields.Selection([('email','Email'),('webhook','Webhook'),('sys','SystemAction')], required=True, index=True)
    dedup_key = fields.Char(required=True, index=True)
    payload = fields.Json(default=dict)
    created_at = fields.Datetime(default=lambda self: fields.Datetime.now())
    dispatched_at = fields.Datetime()
    status = fields.Selection([('pending','Pending'),('done','Done'),('error','Error')], default='pending', index=True)
    last_error = fields.Text()

    _sql_constraints = [('dedup_unique', 'unique(dedup_key)', 'Duplicate outbox entry.')]

    def dispatch_pending(self, limit=100):
        pending = self.search([('status','=','pending')], limit=limit, order="created_at asc")
        for rec in pending:
            try:
                if rec.kind == 'email':
                    self._send_email(rec.payload)
                elif rec.kind == 'webhook':
                    self._send_webhook(rec.payload)
                elif rec.kind == 'sys':
                    self._exec_system_action(rec.payload)
                rec.write({'status':'done','dispatched_at': fields.Datetime.now()})
            except Exception as e:
                rec.write({'status':'error','last_error': str(e)})
        return len(pending)

    def _send_email(self, payload):
        mail = self.env['mail.mail'].create({
            'subject': payload.get('subject') or 'BPM Notification',
            'body_html': payload.get('body') or '<p>No content</p>',
            'email_to': payload.get('to'),
        })
        mail.send()

    def _send_webhook(self, payload):
        pass

    def _exec_system_action(self, payload):
        dotted = payload.get('action'); ctx = payload.get('ctx') or {}
        if not dotted: raise UserError(_("System action missing 'action'"))
        reg = self.env['registry'].sudo()
        reg.call(dotted, ctx)
