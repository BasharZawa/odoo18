# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('account_id', 'partner_id', 'partner_id.country_id', 'product_id', 'product_id.product_line_id')
    def _compute_analytic_distribution(self):
        """
        Override to include product_line_id in the distribution computation.
        This ensures that analytic distribution models configured with a 
        product line condition are automatically applied.
        
        Additionally, dynamically maps:
        - Product lines to analytic accounts under the "Product Line" plan
        - Customer countries to analytic accounts under the "Country" plan
        by matching names, even if no distribution model is configured.
        """
        cache = {}
        # Caches for dynamic mappings
        product_line_analytic_cache = {}
        country_analytic_cache = {}
        # Lazy-loaded plans
        product_line_plan = None
        country_plan = None
        
        for line in self:
            if line.display_type == 'product' or not line.move_id.is_invoice(include_receipts=True):
                # Get product_line_id from the product
                product_line = line.product_id.product_line_id if line.product_id else False
                product_line_id = product_line.id if product_line else False
                
                # Get country from the partner (customer)
                country = line.partner_id.country_id if line.partner_id else False
                country_id = country.id if country else False
                
                # Arguments for standard distribution model lookup
                # Note: product_line_id and country are handled dynamically below,
                # not through distribution models
                arguments = frozendict({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.partner_id.id,
                    "partner_category_id": line.partner_id.category_id.ids,
                    "account_prefix": line.account_id.code,
                    "company_id": line.company_id.id,
                })
                
                if arguments not in cache:
                    distribution = self.env['account.analytic.distribution.model']._get_distribution(arguments)
                    
                    # Ensure distribution is a mutable dict for adding dynamic mappings
                    if distribution is not None:
                        distribution = dict(distribution) if distribution else {}
                        
                        # Get existing accounts to check which plans are already covered
                        existing_account_ids = [int(k) for k in distribution.keys()] if distribution else []
                        existing_accounts = self.env['account.analytic.account'].browse(existing_account_ids).exists() if existing_account_ids else self.env['account.analytic.account']
                        
                        # === Dynamic Product Line Mapping ===
                        if product_line:
                            if product_line_plan is None:
                                product_line_plan = self.env['account.analytic.plan'].search([
                                    ('name', '=ilike', 'Product Line')
                                ], limit=1)
                            
                            if product_line_plan:
                                has_product_line_account = any(
                                    acc.plan_id.id == product_line_plan.id or 
                                    acc.root_plan_id.id == product_line_plan.id 
                                    for acc in existing_accounts
                                )
                                
                                if not has_product_line_account:
                                    if product_line_id not in product_line_analytic_cache:
                                        analytic_account = self.env['account.analytic.account'].search([
                                            '|',
                                            ('plan_id', '=', product_line_plan.id),
                                            ('plan_id.parent_id', '=', product_line_plan.id),
                                            '|',
                                            ('name', '=ilike', product_line.name),
                                            ('code', '=ilike', product_line.name),
                                        ], limit=1)
                                        product_line_analytic_cache[product_line_id] = analytic_account
                                    
                                    analytic_account = product_line_analytic_cache[product_line_id]
                                    if analytic_account:
                                        distribution[str(analytic_account.id)] = 100.0
                        
                        # === Dynamic Country Mapping ===
                        if country:
                            if country_plan is None:
                                country_plan = self.env['account.analytic.plan'].search([
                                    ('name', '=ilike', 'Country')
                                ], limit=1)
                            
                            if country_plan:
                                # Re-check existing accounts (may have been updated by product line)
                                current_account_ids = [int(k) for k in distribution.keys()] if distribution else []
                                current_accounts = self.env['account.analytic.account'].browse(current_account_ids).exists() if current_account_ids else self.env['account.analytic.account']
                                
                                has_country_account = any(
                                    acc.plan_id.id == country_plan.id or 
                                    acc.root_plan_id.id == country_plan.id 
                                    for acc in current_accounts
                                )
                                
                                if not has_country_account:
                                    if country_id not in country_analytic_cache:
                                        # Match by country name or code
                                        analytic_account = self.env['account.analytic.account'].search([
                                            '|',
                                            ('plan_id', '=', country_plan.id),
                                            ('plan_id.parent_id', '=', country_plan.id),
                                            '|', '|', '|',
                                            ('name', '=ilike', country.name),
                                            ('code', '=ilike', country.code),
                                            ('name', '=ilike', country.code),
                                            ('code', '=ilike', country.name),
                                        ], limit=1)
                                        country_analytic_cache[country_id] = analytic_account
                                    
                                    analytic_account = country_analytic_cache[country_id]
                                    if analytic_account:
                                        distribution[str(analytic_account.id)] = 100.0
                    
                    cache[arguments] = distribution
                
                line.analytic_distribution = cache[arguments] or line.analytic_distribution
