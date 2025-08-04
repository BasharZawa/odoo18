from odoo import models, fields, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    bpmn_instance_id = fields.Many2one('bpmn.process.instance', string="BPMN Process")

    def action_start_bpmn_process(self):
        process_def = self.env['bpmn.process.definition'].get_active_process_by_name('CRM Lead Approval')
        if not process_def:
            raise UserError("No active CRM Lead Approval BPMN process found!")
        instance = self.env['bpmn.engine'].start_process(process_def.id, 'crm.lead', self.id)
        self.bpmn_instance_id = instance.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Process Instance',
            'res_model': 'bpmn.process.instance',
            'view_mode': 'form',
            'res_id': instance.id,
        }
