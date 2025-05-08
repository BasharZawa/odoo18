from odoo import models, fields

class Task(models.Model):
    _name = 'task'
    _description = 'Task'

    name = fields.Char(string='Task Name', required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], default='pending', string='State')
    parent_task_id = fields.Many2one('task', string='Parent Task')
    child_task_ids = fields.One2many('task', 'parent_task_id', string='Child Tasks')
    condition = fields.Char(string='Condition', help='Condition to create this task')