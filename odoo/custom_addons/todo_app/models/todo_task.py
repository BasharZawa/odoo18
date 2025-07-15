from odoo import models, fields, api
from odoo.exceptions import UserError

class TodoTask(models.Model):
    _name = 'todo.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Todo Task'

    name = fields.Char(string='Task Name', required=True)
    due_date = fields.Date(string='Due Date')
    description = fields.Text(string='Description')
    assigned_to = fields.Many2one(
        'res.partner',
        string='Assigned To',
    )
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')  
    ], string='State', default='new', required=True)
    estimated_hours = fields.Float(string='Estimated Hours')
    actual_hours = fields.Float(string='Actual Hours', compute='_compute_actual_hours', store=True)
    timesheet_ids = fields.One2many(
        'todo.timesheet',  
        'task_id',
        string='Timesheets',
        help='Timesheets for this task'
    )
    active = fields.Boolean(string='Active', default=True)

    is_due_today = fields.Boolean(string='Is Due Today', compute='_compute_is_due_today', store=True)

    @api.depends('due_date')
    def _compute_is_due_today(self):
        today = fields.Date.context_today(self)
        for task in self:
            task.is_due_today = (task.due_date == today)

    @api.model
    def create(self, vals):
        task = super(TodoTask, self).create(vals)
        task.state = 'new'
        return task
    
    def action_set_in_progress(self):
        for task in self:
            task.state = 'in_progress'
        

    def action_set_completed(self):
        for task in self:
            task.state = 'completed'

    #archive the task
    def action_set_closed(self):
        for task in self:
            task.active = False

    @api.depends('timesheet_ids.hours_spent')
    def _compute_actual_hours(self):
        for task in self:
            task.actual_hours = sum(timesheet.hours_spent for timesheet in task.timesheet_ids)


class Timesheet(models.Model):
    _name = 'todo.timesheet'
    _description = 'Timesheet for Todo Tasks'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    task_id = fields.Many2one('todo.task', string='Task', required=True)
    date = fields.Date(string='Date', required=True)
    hours_spent = fields.Float(string='Hours Spent', required=True)
    description = fields.Text(string='Description')

