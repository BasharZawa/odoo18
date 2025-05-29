from odoo import models, fields

class BpmProcessDefinition(models.Model):
    _name = 'bpm.process.definition'
    _description = 'BPM Process Definition'

    name = fields.Char(required=True)
    bpmn_xml = fields.Text(string="BPMN XML")
