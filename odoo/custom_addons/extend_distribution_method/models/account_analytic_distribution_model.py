#-*- coding: utf-8 -*-

from odoo import models, fields


class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    product_line_id = fields.Many2one(
        'product.line.ept',
        string='Product Line',
        ondelete='cascade',
        help="Select a product line for which the analytic distribution will be used"
    )
    def _get_default_search_domain_vals(self):
        return super()._get_default_search_domain_vals() | {
            'product_line_id': False,
        }
    
    