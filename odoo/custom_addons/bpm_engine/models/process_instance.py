from odoo import models, fields

class ProcessInstance(models.Model):
    _name = 'bpmn.process.instance'
    _description = 'BPMN Process Instance'

    process_definition_id = fields.Many2one('bpmn.process.definition', required=True, ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='draft', required=True)
    started_at = fields.Datetime()
    ended_at = fields.Datetime()
    related_record_model = fields.Char()
    related_record_id = fields.Integer()
    task_instance_ids = fields.One2many('bpmn.task.instance', 'process_instance_id', string="Tasks")
    variable_ids = fields.One2many('bpmn.process.variable', 'process_instance_id', string="Variables")
    log_ids = fields.One2many('bpmn.activity.log', 'process_instance_id', string="Logs")
