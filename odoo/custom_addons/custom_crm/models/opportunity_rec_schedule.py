from odoo import models, fields


class OpportunityRecSchedule(models.Model):
    _name = 'opportunity.rec.schedule'
    _description = 'Opportunity Recurring Schedule'

    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', required=True, ondelete='cascade')
    est_date = fields.Date(string='Schedule Date', required=True)
    est_revenue = fields.Float(string='Amount', required=True)
    description = fields.Text(string='Description')
