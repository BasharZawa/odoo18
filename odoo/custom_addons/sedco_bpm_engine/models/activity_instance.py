from odoo import models, fields

class ActivityInstance(models.Model):
    _name = "activity.instance"
    _description = "BPM Activity Instance"

    proc_id = fields.Many2one("process.instance", required=True, ondelete="cascade")
    node_id = fields.Char(required=True)
    type = fields.Selection([
        ('start','Start'),('if','IF'),('task','Task'),('sys','SystemAction'),
        ('pbranch','ParallelBranch'),('pwait','ParallelWait'),
        ('wevent','WaitEvent'),('wcond','WaitCondition'),('wtime','WaitTime'),
        ('end','End')
    ], required=True)
    status = fields.Selection([('ready','Ready'),('waiting','Waiting'),('done','Done'),('failed','Failed')], default='ready', index=True)
    assignee_id = fields.Many2one('res.users', string="Assigned User")
    assignee_role_id = fields.Many2one('bpm.role', string="Assigned Role")
    started_at = fields.Datetime()
    ended_at = fields.Datetime()
    data = fields.Json(default=dict)

    _sql_constraints = [('proc_node_unique', 'unique(proc_id, node_id)', 'Activity for this node already exists in this process.')]
