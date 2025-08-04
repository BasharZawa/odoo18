from odoo import models, fields

class ActivityLog(models.Model):
    _name = 'bpmn.activity.log'
    _description = 'BPMN Activity Log'

    process_instance_id = fields.Many2one('bpmn.process.instance', required=True, ondelete='cascade')
    action_type = fields.Char(required=True)
    timestamp = fields.Datetime(default=fields.Datetime.now)
    actor_id = fields.Many2one('res.users')
    details = fields.Text()
