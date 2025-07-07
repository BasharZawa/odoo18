from odoo import models, fields

class TodoTask(models.Model):
    _name = 'todo.task'
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
    
