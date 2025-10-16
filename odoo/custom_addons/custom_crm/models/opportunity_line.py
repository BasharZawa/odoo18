from odoo import models, fields, api


class OpportunityLine(models.Model):
    _name = 'opportunity.line'
    _description = 'Opportunity Line'

    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price', required=True)
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)
    is_product_overriden = fields.Boolean(string='Is Write-In Product', default=False)
    is_price_overriden = fields.Boolean(string='Is Price Overriden', default=False)
    product_name = fields.Char(string='Product Name')

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price
