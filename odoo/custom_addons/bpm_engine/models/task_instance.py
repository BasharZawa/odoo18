from odoo import models, fields

class TaskInstance(models.Model):
    _name = 'bpmn.task.instance'
    _description = 'BPMN Task Instance'

    process_instance_id = fields.Many2one('bpmn.process.instance', required=True, ondelete='cascade')
    task_type = fields.Selection([('user', 'User'), ('service', 'Service')], required=True)
    assigned_user_id = fields.Many2one('res.users')
    assigned_group_id = fields.Many2one('res.groups')
    status = fields.Selection([
        ('ready', 'Ready'), ('claimed', 'Claimed'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='ready', required=True)
    started_at = fields.Datetime()
    completed_at = fields.Datetime()
    task_name = fields.Char(required=True)
    task_data = fields.Text()
