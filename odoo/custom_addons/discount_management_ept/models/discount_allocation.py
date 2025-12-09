# -*- coding: utf-8 -*-
from odoo import fields, models


class DiscountAllocation(models.Model):
    _name = 'discount.allocation'
    _description = 'Discount Allocation by Category and Product Type'

    job_id = fields.Many2one('hr.job', string='Job Position', required=True, ondelete='cascade')
    category_id = fields.Many2one('product.category', string='Product Category', required=True)
    max_service_discount_percent = fields.Float(string='Service Type Max Discount (%)', default=0.0)
    max_storable_discount_percent = fields.Float(string='Combo Type Max Discount (%)', default=0.0)
    max_consumable_discount_percent = fields.Float(string='Goods Type Max Discount (%)', default=0.0)

    _sql_constraints = [
        ('job_category_unique', 'unique(job_id, category_id)', 'Only one allocation per job and category is allowed.'),
    ]

    def get_max_discount_for_product_type(self, product_type):
        """Get max discount percentage based on product type"""
        type_mapping = {
            'service': self.max_service_discount_percent,
            'combo': self.max_storable_discount_percent,
            'consu': self.max_consumable_discount_percent,
        }
        return type_mapping.get(product_type, 0.0)
