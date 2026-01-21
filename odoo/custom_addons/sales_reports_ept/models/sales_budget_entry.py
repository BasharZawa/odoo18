# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime


class SalesBudgetEntry(models.Model):
    _name = 'sales.budget.entry'
    _description = 'Sales Budget Entry'
    _order = 'year desc, salesperson_id, country_id, product_line_id, analytic_country_account_id, analytic_salesperson_account_id, analytic_product_line_account_id'
    _rec_name = 'display_name'

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: str(datetime.date.today().year)
    )

    analytic_country_plan_id = fields.Many2one(
        'account.analytic.plan',
        compute='_compute_analytic_plan_ids',
        store=False,
    )
    analytic_salesperson_plan_id = fields.Many2one(
        'account.analytic.plan',
        compute='_compute_analytic_plan_ids',
        store=False,
    )
    analytic_product_line_plan_id = fields.Many2one(
        'account.analytic.plan',
        compute='_compute_analytic_plan_ids',
        store=False,
    )

    analytic_country_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Country',
        domain="[('root_plan_id', '=', analytic_country_plan_id), ('company_id', 'in', [company_id, False])]",
        help='Analytic Country (Plan: Country)'
    )
    analytic_salesperson_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Salesperson',
        domain="[('root_plan_id', '=', analytic_salesperson_plan_id), ('company_id', 'in', [company_id, False])]",
        help='Analytic Salesperson (Plan: Salesperson)'
    )
    analytic_product_line_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Product Line',
        domain="[('root_plan_id', '=', analytic_product_line_plan_id), ('company_id', 'in', [company_id, False])]",
        help='Analytic Product Line (Plan: Product Line)'
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        required=False,
        domain=[('share', '=', False)]
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=False
    )
    product_line_id = fields.Many2one(
        'product.line.ept',
        string='Product Line',
        required=False,
        help='Product Line (Legacy Products, CVM, Self Service, Media Analytics, Services)'
    )
    budget_amount = fields.Monetary(
        string='Budget Amount',
        required=True,
        currency_field='currency_id',
        help='Total annual budget value for this combination'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    notes = fields.Text(string='Notes')
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('company_id')
    def _compute_analytic_plan_ids(self):
        for record in self:
            record.analytic_country_plan_id = self.env.ref('sales_reports_ept.analytic_plan_country', raise_if_not_found=False)
            record.analytic_salesperson_plan_id = self.env.ref('sales_reports_ept.analytic_plan_salesperson', raise_if_not_found=False)
            record.analytic_product_line_plan_id = self.env.ref('sales_reports_ept.analytic_plan_product_line', raise_if_not_found=False)

    @api.onchange('analytic_country_account_id', 'analytic_salesperson_account_id', 'analytic_product_line_account_id')
    def _onchange_analytic_dimensions(self):
        for record in self:
            if record.analytic_country_account_id or record.analytic_salesperson_account_id or record.analytic_product_line_account_id:
                record.salesperson_id = False
                record.country_id = False
                record.product_line_id = False

    @api.onchange('salesperson_id', 'country_id', 'product_line_id')
    def _onchange_sales_dimensions(self):
        for record in self:
            if record.salesperson_id or record.country_id or record.product_line_id:
                record.analytic_country_account_id = False
                record.analytic_salesperson_account_id = False
                record.analytic_product_line_account_id = False
    
    @api.model
    def _get_year_selection(self):
        """Generate year selection for past 5 years and next 5 years"""
        current_year = datetime.date.today().year
        years = []
        for year in range(current_year - 5, current_year + 6):
            years.append((str(year), str(year)))
        return years
    
    @api.depends(
        'year',
        'salesperson_id', 'country_id', 'product_line_id',
        'analytic_country_account_id', 'analytic_salesperson_account_id', 'analytic_product_line_account_id'
    )
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.year:
                parts.append(record.year)
            if record.analytic_country_account_id or record.analytic_salesperson_account_id or record.analytic_product_line_account_id:
                if record.analytic_country_account_id:
                    parts.append(record.analytic_country_account_id.display_name)
                if record.analytic_salesperson_account_id:
                    parts.append(record.analytic_salesperson_account_id.display_name)
                if record.analytic_product_line_account_id:
                    parts.append(record.analytic_product_line_account_id.display_name)
            if record.salesperson_id:
                parts.append(record.salesperson_id.name)
            if record.country_id:
                parts.append(record.country_id.code or record.country_id.name)
            if record.product_line_id:
                parts.append(record.product_line_id.name)
            record.display_name = ' / '.join(parts) if parts else _('New')

    @api.constrains(
        'analytic_country_account_id', 'analytic_salesperson_account_id', 'analytic_product_line_account_id',
        'salesperson_id', 'country_id', 'product_line_id'
    )
    def _check_budget_mode_dimensions(self):
        """Enforce a single budgeting mode:

        - Analytic mode: analytic dimensions are set; sales dimensions must be empty.
        - Sales mode: analytic dimensions are empty; all sales dimensions must be set.
        """
        for record in self:
            is_analytic_mode = bool(
                record.analytic_country_account_id
                or record.analytic_salesperson_account_id
                or record.analytic_product_line_account_id
            )

            if is_analytic_mode:
                if record.salesperson_id or record.country_id or record.product_line_id:
                    raise ValidationError(_(
                        'When analytic dimensions are set, Salesperson/Country/Product Line must be empty.'
                    ))

                if not (record.analytic_country_account_id and record.analytic_salesperson_account_id and record.analytic_product_line_account_id):
                    raise ValidationError(_(
                        'For analytic budgeting, you must set Analytic Country, Analytic Salesperson, and Analytic Product Line.'
                    ))
            else:
                if not (record.salesperson_id and record.country_id and record.product_line_id):
                    raise ValidationError(_(
                        'Either set analytic dimensions (Country/Salesperson/Product Line), or set Salesperson, Country, and Product Line.'
                    ))
    
    @api.constrains('year', 'salesperson_id', 'country_id', 'product_line_id', 'company_id')
    def _check_unique_combination(self):
        """Ensure unique record per budgeting mode.

        - Sales mode: Year + Salesperson + Country + Product Line + Company
        - Analytic mode: Year + Analytic Country + Analytic Salesperson + Analytic Product Line + Company
        """
        for record in self:
            is_analytic_mode = bool(
                record.analytic_country_account_id
                or record.analytic_salesperson_account_id
                or record.analytic_product_line_account_id
            )

            if is_analytic_mode:
                domain = [
                    ('year', '=', record.year),
                    ('analytic_country_account_id', '=', record.analytic_country_account_id.id),
                    ('analytic_salesperson_account_id', '=', record.analytic_salesperson_account_id.id),
                    ('analytic_product_line_account_id', '=', record.analytic_product_line_account_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_(
                        'A budget entry already exists for Year: %s with these analytic dimensions. '
                        'Each combination must be unique.'
                    ) % (record.year,))
            else:
                domain = [
                    ('year', '=', record.year),
                    ('salesperson_id', '=', record.salesperson_id.id),
                    ('country_id', '=', record.country_id.id),
                    ('product_line_id', '=', record.product_line_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_(
                        'A budget entry already exists for Year: %s, Salesperson: %s, '
                        'Country: %s, Product Line: %s. '
                        'Each combination must be unique.'
                    ) % (record.year, record.salesperson_id.name,
                         record.country_id.name, record.product_line_id.name))
    
    @api.constrains('budget_amount')
    def _check_budget_amount(self):
        """Budget amount must be positive"""
        for record in self:
            if record.budget_amount < 0:
                raise ValidationError(_('Budget amount cannot be negative.'))
