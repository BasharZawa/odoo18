# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('account_id', 'partner_id', 'product_id', 'product_id.product_line_id')
    def _compute_analytic_distribution(self):
        """
        Override to include product_line_id in the distribution computation.
        This ensures that analytic distribution models configured with a 
        product line condition are automatically applied.
        """
        cache = {}
        for line in self:
            if line.display_type == 'product' or not line.move_id.is_invoice(include_receipts=True):
                # Get product_line_id from the product (it's a related field from product.product)
                product_line_id = False
                if line.product_id and line.product_id.product_line_id:
                    product_line_id = line.product_id.product_line_id.id
                
                arguments = frozendict({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "product_line_id": product_line_id,  # Add product line
                    "partner_id": line.partner_id.id,
                    "partner_category_id": line.partner_id.category_id.ids,
                    "account_prefix": line.account_id.code,
                    "company_id": line.company_id.id,
                })
                if arguments not in cache:
                    cache[arguments] = self.env['account.analytic.distribution.model']._get_distribution(arguments)
                line.analytic_distribution = cache[arguments] or line.analytic_distribution
