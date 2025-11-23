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
    
    # Add currency for monetary widget
    currency_id = fields.Many2one(
        'res.currency',
        related='opportunity_id.company_currency',
        store=True,
        readonly=True
    )

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-populate price and name from product"""
        if self.product_id and not self.is_price_overriden:
            self.unit_price = self.product_id.list_price
            self.product_name = self.product_id.name
            self.is_product_overriden = False

    @api.onchange('is_product_overriden')
    def _onchange_is_product_overriden(self):
        """When toggling write-in, clear or populate product_name"""
        if self.is_product_overriden:
            # User wants to write custom product name
            if self.product_id:
                self.product_name = self.product_id.name
        else:
            # Use product's name
            if self.product_id:
                self.product_name = self.product_id.name

    @api.onchange('is_price_overriden')
    def _onchange_is_price_overriden(self):
        """Reset price when toggling price override off"""
        if not self.is_price_overriden and self.product_id:
            self.unit_price = self.product_id.list_price