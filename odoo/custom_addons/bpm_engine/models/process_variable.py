from odoo import models, fields

class ProcessVariable(models.Model):
    _name = 'bpmn.process.variable'
    _description = 'BPMN Process Variable'

    process_instance_id = fields.Many2one('bpmn.process.instance', required=True, ondelete='cascade')
    key = fields.Char(required=True)
    value = fields.Char()
    type = fields.Selection([
        ('str', 'String'), ('int', 'Integer'), ('float', 'Float'), ('bool', 'Boolean'), ('date', 'Date')],
        required=True, default='str')
    scope = fields.Selection([('process', 'Process'), ('task', 'Task')], default='process')
