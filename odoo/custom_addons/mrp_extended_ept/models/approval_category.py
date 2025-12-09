from odoo import models, fields



class ApprovalCategoryExtended(models.Model):
    _inherit = 'approval.category'

    has_supervisor = fields.Selection([
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('no', 'None')], string="Time Tracking Supervisor", default="no")
    approval_type = fields.Selection(selection_add=[('time_tracking_req', 'Time Tracking Request')])
