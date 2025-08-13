from odoo import models, fields

class DiscountApprovalProfile(models.Model):
    _name = 'discount.approval.profile'
    _description = 'Discount Approval Profile'

    crm_team_id = fields.Many2one('crm.team', string="CRM Team", required=True, ondelete='cascade')
    software_discount = fields.Float(string="Software Discount (%)")
    hardware_discount = fields.Float(string="Hardware Discount (%)")
    service_discount = fields.Float(string="Service Discount (%)")
    max_discount = fields.Float(string="Max Allowed Discount (%)")

    