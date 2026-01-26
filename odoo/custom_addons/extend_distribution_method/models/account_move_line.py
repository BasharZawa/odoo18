# -*- coding: utf-8 -*-

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_product_line_analytic_account(self):
        """Get analytic account matching the product's product line name."""
        self.ensure_one()
        if not self.product_id or not self.product_id.product_line_id:
            return self.env['account.analytic.account']
        
        product_line = self.product_id.product_line_id
        plan = self.env['account.analytic.plan'].search([
            ('name', '=ilike', 'Product Line')
        ], limit=1)
        
        if not plan:
            return self.env['account.analytic.account']
        
        return self.env['account.analytic.account'].search([
            '|',
            ('plan_id', '=', plan.id),
            ('plan_id.parent_id', '=', plan.id),
            '|',
            ('name', '=ilike', product_line.name),
            ('code', '=ilike', product_line.name),
        ], limit=1)

    def _get_country_analytic_account(self):
        """Get analytic account matching the partner's country name."""
        self.ensure_one()
        if not self.partner_id or not self.partner_id.country_id:
            return self.env['account.analytic.account']
        
        country = self.partner_id.country_id
        plan = self.env['account.analytic.plan'].search([
            ('name', '=ilike', 'Country')
        ], limit=1)
        
        if not plan:
            return self.env['account.analytic.account']
        
        return self.env['account.analytic.account'].search([
            '|',
            ('plan_id', '=', plan.id),
            ('plan_id.parent_id', '=', plan.id),
            '|', '|', '|',
            ('name', '=ilike', country.name),
            ('code', '=ilike', country.code),
            ('name', '=ilike', country.code),
            ('code', '=ilike', country.name),
        ], limit=1)

    def _has_account_from_plan(self, distribution, plan):
        """Check if distribution already has an account from the given plan."""
        if not distribution or not plan:
            return False
        account_ids = []
        for key in distribution.keys():
            # Handle both single IDs ("123") and comma-separated IDs ("1,2,3")
            for part in str(key).split(','):
                part = part.strip()
                if part.isdigit():
                    account_ids.append(int(part))
        if not account_ids:
            return False
        accounts = self.env['account.analytic.account'].browse(account_ids).exists()
        return any(
            acc.plan_id.id == plan.id or 
            acc.plan_id.parent_id.id == plan.id or
            acc.root_plan_id.id == plan.id
            for acc in accounts
        )

    def _related_analytic_distribution(self):
        """Override to add product line and country analytic accounts."""
        self.ensure_one()
        distribution = super()._related_analytic_distribution() or {}
        
        # Get plans for checking duplicates
        product_line_plan = self.env['account.analytic.plan'].search([
            ('name', '=ilike', 'Product Line')
        ], limit=1)
        country_plan = self.env['account.analytic.plan'].search([
            ('name', '=ilike', 'Country')
        ], limit=1)
        
        # Collect account IDs to add
        account_ids_to_add = []
        
        # Add product line account if plan not already covered
        if not self._has_account_from_plan(distribution, product_line_plan):
            product_line_account = self._get_product_line_analytic_account()
            if product_line_account:
                account_ids_to_add.append(str(product_line_account.id))
        
        # Add country account if plan not already covered
        if not self._has_account_from_plan(distribution, country_plan):
            country_account = self._get_country_analytic_account()
            if country_account:
                account_ids_to_add.append(str(country_account.id))
        
        # Add all accounts as a single combined key (one line)
        if account_ids_to_add:
            combined_key = ','.join(account_ids_to_add)
            distribution[combined_key] = 100.0
        
        return distribution
