from odoo import models, fields, api
from odoo.exceptions import UserError

class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    total_actual_cost = fields.Float(string='Total Actual Cost')
    budgent_cost = fields.Float(string='Budget Cost')

    