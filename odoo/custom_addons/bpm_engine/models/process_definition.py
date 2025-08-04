from odoo import models, fields, api

class ProcessDefinition(models.Model):
    _name = 'bpmn.process.definition'
    _description = 'BPMN Process Definition'

    name = fields.Char(required=True)
    version = fields.Char(default='1.0')
    xml_data = fields.Text('BPMN XML', required=True)
    description = fields.Text()
    is_active = fields.Boolean(default=True)
    created_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    created_at = fields.Datetime(default=fields.Datetime.now)
    process_instance_ids = fields.One2many('bpmn.process.instance', 'process_definition_id', string="Instances")

    @api.model
    def get_active_process_by_name(self, name):
        return self.search([('name', '=', name), ('is_active', '=', True)], limit=1)
