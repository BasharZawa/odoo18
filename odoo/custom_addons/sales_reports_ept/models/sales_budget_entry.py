# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime


class SalesBudgetEntry(models.Model):
    _name = 'sales.budget.entry'
    _description = 'Sales Budget Entry'
    _order = 'year desc, salesperson_id, country_id, product_line_id'
    _rec_name = 'display_name'

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: str(datetime.date.today().year)
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        required=True,
        domain=[('share', '=', False)]
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True
    )
    product_line_id = fields.Many2one(
        'product.line.ept',
        string='Product Line',
        required=True,
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
    
    @api.model
    def _get_year_selection(self):
        """Generate year selection for past 5 years and next 5 years"""
        current_year = datetime.date.today().year
        years = []
        for year in range(current_year - 5, current_year + 6):
            years.append((str(year), str(year)))
        return years
    
    @api.depends('year', 'salesperson_id', 'country_id', 'product_line_id')
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.year:
                parts.append(record.year)
            if record.salesperson_id:
                parts.append(record.salesperson_id.name)
            if record.country_id:
                parts.append(record.country_id.code or record.country_id.name)
            if record.product_line_id:
                parts.append(record.product_line_id.name)
            record.display_name = ' / '.join(parts) if parts else _('New')
    
    @api.constrains('year', 'salesperson_id', 'country_id', 'product_line_id', 'company_id')
    def _check_unique_combination(self):
        """Ensure unique record per Year + Salesperson + Country + Product Line + Company"""
        for record in self:
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
