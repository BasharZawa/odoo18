from odoo import models, fields, api

class CrmStage(models.Model):
    _inherit = 'crm.stage'
    
    stage_type = fields.Selection([
        ('lead', 'Lead'),
        ('opportunity', 'Opportunity'),
        ('none', 'None'),

    ], string='Stage Type', default='none', required=True, 
       help='Determines if this stage is for Leads, Opportunities, or none')
