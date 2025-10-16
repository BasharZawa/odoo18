from odoo import models, fields, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead' #inherit is to extend existing model not create new one

    #Prospect
    

    # Common 
    product_line_id = fields.Many2one('product.line', string='Product Category')
    is_service = fields.Boolean(string='Is Service', default=False)
    vertical_id = fields.Many2one('vertical', string='Vertical')
    sales_notes = fields.Text(string='Sales Notes')

    #lead
    contact_id = fields.Many2one('res.partner', string='Contact', domain="[('is_company','=',False)]")
    forwarded_to_partner = fields.Many2one('res.partner', string='Forwarded To Partner', domain="[('is_company','=',True)]")
    forwarded_to_partner_date = fields.Datetime(string='Forwarded To Partner Date')
    lead_type = fields.Selection([
        #Customer, Supplier, Partner, CVM Cloud – Demo, CVM Cloud Trial, CVM Cloud – Call
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('partner', 'Partner'),
        ('cvm_cloud_demo', 'CVM Cloud – Demo'),
        ('cvm_cloud_trial', 'CVM Cloud Trial'),
        ('cvm_cloud_call', 'CVM Cloud – Call'),
    ], string='Lead Type')
    disqualification_reason = fields.Selection([
        ('lost', 'Lost'),
        ('unreachable', 'Unreachable'),
        ('not_interested', 'Not Interested'),
        ('canceled', 'Canceled'),
        ('not_a_lead', 'Not a Lead'),
        ('duplicate_lead', 'Duplicate Lead'),
        ('no_action_from_partner', 'No Action from Partner'),
        ('candidate_cv', 'Candidate (CV)'),
        ('supplier', 'Supplier'),
        ('fraud', 'Fraud'),
        ('not_related_to_our_business', 'Not related to our business.'),
        ('others', 'Others'),
    ], string='Disqualification Reason')
    why_not_a_lead = fields.Text(string='Why Not a Lead')
    interested_solution_id = fields.Many2one('interested.solution', string='Interested Solution')

    #Opportunity
    end_user_id = fields.Many2one('res.partner', string='End User', domain="[('is_company','=',True)]")
    cancellation_reason = fields.Selection([
        ('other_reason', 'Other Reason'),
        ('over_budget', 'Over Budget'),
        ('request_for_info', 'Request for Info'),
        ('management_change', 'Management Change'),
        ('one_single_offer', 'One Single Offer'),
        ('re_tendering', 'Re-Tendering'),
        ('merged_with_another_opportunity', 'Merged with another opportunity'),
    ], string='Cancellation Reason')
    lost_reason = fields.Selection([
        ('price', 'Price'),
        ('product_features', 'Product Feature(s)/Compliance'),
        ('partner_weakness', 'Partner Weakness'),
        ('politics', 'Politics'),
        ('delivery_time', 'Delivery Time'),
        ('extension_to_existing_solution', 'Extension to Existing Solution'),
        ('technical_proposal', 'Technical Proposal'),
        ('late_submission', 'Late Submission'),
        ('other_reason', 'Other Reason'),
    ], string='Lost Reason (OutSold)')
    lost_to_id = fields.Many2one('res.partner', string='Lost To', domain="[('is_company','=',True)]")
    lost_note = fields.Text(string='Lost Notes')
    renewal_for_sc_id = fields.Many2one('sale.order', string='Renewal for SC#', help='Link to the original Sale Order for the Service Contract being renewed')
    parent_opportunity_id = fields.Many2one('crm.lead', string='Parent Opportunity', domain="[('type','=','opportunity')]", help='Parent Opportunity in case this is a upsell')
    Oppy_rec_schedule_ids = fields.One2many('opportunity.rec.schedule', 'opportunity_id', string='Recurring Schedule')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Override to filter stages based on lead/opportunity type"""
        # Get the context to check if we're filtering by type
        lead_type = self.env.context.get('default_type')
        
        # First call the parent method to get the base filtered stages
        stages = super(CrmLead, self)._read_group_stage_ids(stages, domain)
        
        # Apply additional stage_type filter if we're in a filtered view
        if lead_type == 'lead':
            stages = stages.filtered(lambda s: s.stage_type in ['lead'])
        elif lead_type == 'opportunity':
            stages = stages.filtered(lambda s: s.stage_type in ['opportunity'])
        
        return stages





