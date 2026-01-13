# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter
import io
import base64
import datetime


class SalesAnalysisReportWizard(models.TransientModel):
    _name = 'sales.analysis.report.wizard'
    _description = 'Sales Analysis Budget vs Actual Report Wizard'

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: str(datetime.date.today().year)
    )
    report_type = fields.Selection([
        ('country', 'By Country/Region'),
        ('salesperson', 'By Salesperson')
    ], string='Report Type', required=True, default='country')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    # Output fields
    report_file = fields.Binary(string='Report File', readonly=True)
    report_filename = fields.Char(string='Filename')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')
    
    @api.model
    def _get_year_selection(self):
        """Generate year selection for past 5 years and next 5 years"""
        current_year = datetime.date.today().year
        years = []
        for year in range(current_year - 5, current_year + 6):
            years.append((str(year), str(year)))
        return years
    
    def _get_product_lines(self):
        """Get all active product lines"""
        return self.env['product.line.ept'].search([])
    
    def _get_confirmed_orders_domain(self, year):
        """Get domain for confirmed sales orders in a specific year"""
        start_date = f'{year}-01-01'
        end_date = f'{year}-12-31'
        return [
            ('state', '=', 'sale'),
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
            ('company_id', '=', self.company_id.id)
        ]
    
    def _get_actual_sales_data(self, year, group_by='country'):
        """
        Get actual sales data grouped by country/region or salesperson and product line.
        Returns dict: {group_key: {product_line_id: amount}}
        """
        domain = self._get_confirmed_orders_domain(year)
        orders = self.env['sale.order'].search(domain)
        
        result = {}
        intercompany_result = {}
        
        for order in orders:
            # Determine if intercompany (partner is another company)
            is_intercompany = order.partner_id.company_id and order.partner_id.company_id != self.company_id
            
            if group_by == 'country':
                group_key = order.partner_id.country_id.id if order.partner_id.country_id else 0
            else:  # salesperson
                group_key = order.user_id.id if order.user_id else 0
            
            for line in order.order_line:
                product_line_id = line.product_id.product_tmpl_id.product_line_id.id if line.product_id.product_tmpl_id.product_line_id else 0
                amount = line.price_subtotal  # Excluding taxes
                
                if is_intercompany:
                    if product_line_id not in intercompany_result:
                        intercompany_result[product_line_id] = 0
                    intercompany_result[product_line_id] += amount
                else:
                    if group_key not in result:
                        result[group_key] = {}
                    if product_line_id not in result[group_key]:
                        result[group_key][product_line_id] = 0
                    result[group_key][product_line_id] += amount
        
        return result, intercompany_result
    
    def _get_budget_data(self, year, group_by='country'):
        """
        Get budget data grouped by country or salesperson and product line.
        Returns dict: {group_key: {product_line_id: amount}}
        """
        domain = [
            ('year', '=', year),
            ('company_id', '=', self.company_id.id)
        ]
        budgets = self.env['sales.budget.entry'].search(domain)
        
        result = {}
        for budget in budgets:
            if group_by == 'country':
                group_key = budget.country_id.id
            else:  # salesperson
                group_key = budget.salesperson_id.id
            
            if group_key not in result:
                result[group_key] = {}
            
            product_line_id = budget.product_line_id.id
            if product_line_id not in result[group_key]:
                result[group_key][product_line_id] = 0
            result[group_key][product_line_id] += budget.budget_amount
        
        return result
    
    def _calculate_variance(self, actual, budget):
        """Calculate variance amount and percentage"""
        variance_amount = actual - budget
        if budget != 0:
            variance_pct = (variance_amount / budget) * 100
        else:
            variance_pct = 100 if actual > 0 else 0
        return variance_amount, variance_pct
    
    def _get_ytd_actual(self, year, group_by='country'):
        """
        Get YTD actual sales (from Jan 1 to today or end of year if past year)
        """
        current_date = datetime.date.today()
        selected_year = int(year)
        
        if selected_year < current_date.year:
            # Past year - full year data
            end_date = f'{year}-12-31'
        else:
            # Current year - up to today
            end_date = current_date.strftime('%Y-%m-%d')
        
        start_date = f'{year}-01-01'
        domain = [
            ('state', '=', 'sale'),
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
            ('company_id', '=', self.company_id.id)
        ]
        orders = self.env['sale.order'].search(domain)
        
        result = {}
        for order in orders:
            # Skip intercompany for YTD
            is_intercompany = order.partner_id.company_id and order.partner_id.company_id != self.company_id
            if is_intercompany:
                continue
            
            if group_by == 'country':
                group_key = order.partner_id.country_id.id if order.partner_id.country_id else 0
            else:
                group_key = order.user_id.id if order.user_id else 0
            
            amount = order.amount_untaxed
            if group_key not in result:
                result[group_key] = 0
            result[group_key] += amount
        
        return result
    
    def action_generate_report(self):
        """Generate the Excel report"""
        self.ensure_one()
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        if self.report_type == 'country':
            self._generate_country_report(workbook)
            filename = f'Sales_Analysis_Budget_vs_Actual_By_Country_{self.year}.xlsx'
        else:
            self._generate_salesperson_report(workbook)
            filename = f'Sales_Analysis_Budget_vs_Actual_By_Salesperson_{self.year}.xlsx'
        
        workbook.close()
        output.seek(0)
        
        # Save the file
        self.write({
            'report_file': base64.b64encode(output.read()),
            'report_filename': filename,
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sales.analysis.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }
    
    def _setup_formats(self, workbook):
        """Setup Excel formats"""
        formats = {
            'title': workbook.add_format({
                'bold': True, 'font_size': 16, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#4472C4', 'font_color': 'white'
            }),
            'header': workbook.add_format({
                'bold': True, 'font_size': 11, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#D9E2F3', 'border': 1,
                'text_wrap': True
            }),
            'header_product': workbook.add_format({
                'bold': True, 'font_size': 10, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#E2EFDA', 'border': 1,
                'text_wrap': True
            }),
            'region': workbook.add_format({
                'bold': True, 'font_size': 11, 'bg_color': '#FFF2CC',
                'border': 1, 'valign': 'vcenter'
            }),
            'country': workbook.add_format({
                'font_size': 10, 'border': 1, 'valign': 'vcenter', 'indent': 1
            }),
            'number': workbook.add_format({
                'font_size': 10, 'border': 1, 'num_format': '#,##0.00',
                'align': 'right', 'valign': 'vcenter'
            }),
            'number_bold': workbook.add_format({
                'bold': True, 'font_size': 10, 'border': 1,
                'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter',
                'bg_color': '#FFF2CC'
            }),
            'percent': workbook.add_format({
                'font_size': 10, 'border': 1, 'num_format': '0.00%',
                'align': 'right', 'valign': 'vcenter'
            }),
            'percent_bold': workbook.add_format({
                'bold': True, 'font_size': 10, 'border': 1,
                'num_format': '0.00%', 'align': 'right', 'valign': 'vcenter',
                'bg_color': '#FFF2CC'
            }),
            'intercompany': workbook.add_format({
                'bold': True, 'font_size': 10, 'border': 1, 'italic': True,
                'bg_color': '#FCE4D6', 'valign': 'vcenter'
            }),
            'total': workbook.add_format({
                'bold': True, 'font_size': 11, 'border': 2,
                'bg_color': '#4472C4', 'font_color': 'white',
                'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'
            }),
        }
        return formats
    
    def _generate_country_report(self, workbook):
        """Generate country/region-wise report"""
        worksheet = workbook.add_worksheet('Budget vs Actual by Country')
        formats = self._setup_formats(workbook)
        
        # Get data
        year = self.year
        prev_year = str(int(year) - 1)
        product_lines = self._get_product_lines()
        
        actual_data, intercompany_data = self._get_actual_sales_data(year, 'country')
        budget_data = self._get_budget_data(year, 'country')
        prev_actual_data, _ = self._get_actual_sales_data(prev_year, 'country')
        ytd_actual = self._get_ytd_actual(year, 'country')
        ytd_prev = self._get_ytd_actual(prev_year, 'country')
        ytd_budget = self._get_budget_data(year, 'country')  # Same as budget for now
        
        # Get regions and countries
        regions = self.env['sales.region'].search([('active', '=', True)])
        
        # Setup columns
        # Column structure: Region/Country | YTD Actual | YTD Budget | YTD Prev |
        # For each product line: Actual | Budget | Var Amt | Var % | Prev Actual | Var Amt | Var %
        
        row = 0
        col = 0
        
        # Title
        worksheet.merge_range(row, 0, row, 6 + len(product_lines) * 7, 
                             f'Sales Analysis - Budget vs Actual Report ({year})', formats['title'])
        row += 2
        
        # Header row 1 - Main categories
        worksheet.write(row, 0, 'Region / Country', formats['header'])
        worksheet.write(row, 1, f'YTD Actual {year}', formats['header'])
        worksheet.write(row, 2, f'YTD Budget {year}', formats['header'])
        worksheet.write(row, 3, f'YTD Prev {prev_year}', formats['header'])
        
        col = 4
        for pl in product_lines:
            worksheet.merge_range(row, col, row, col + 6, pl.name, formats['header_product'])
            col += 7
        
        row += 1
        
        # Header row 2 - Sub categories
        worksheet.write(row, 0, '', formats['header'])
        worksheet.write(row, 1, '', formats['header'])
        worksheet.write(row, 2, '', formats['header'])
        worksheet.write(row, 3, '', formats['header'])
        
        col = 4
        for pl in product_lines:
            worksheet.write(row, col, f'Actual {year}', formats['header'])
            worksheet.write(row, col + 1, f'Budget {year}', formats['header'])
            worksheet.write(row, col + 2, 'Var Amt', formats['header'])
            worksheet.write(row, col + 3, 'Var %', formats['header'])
            worksheet.write(row, col + 4, f'Prev {prev_year}', formats['header'])
            worksheet.write(row, col + 5, 'YoY Var Amt', formats['header'])
            worksheet.write(row, col + 6, 'YoY Var %', formats['header'])
            col += 7
        
        row += 1
        
        # Set column widths
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 3, 15)
        worksheet.set_column(4, 4 + len(product_lines) * 7, 12)
        
        grand_totals = {
            'ytd_actual': 0, 'ytd_budget': 0, 'ytd_prev': 0,
            'by_pl': {pl.id: {'actual': 0, 'budget': 0, 'prev': 0} for pl in product_lines}
        }
        
        # Data rows - by region
        for region in regions:
            # Region header row
            worksheet.write(row, 0, region.name, formats['region'])
            region_ytd_actual = 0
            region_ytd_budget = 0
            region_ytd_prev = 0
            region_pl_data = {pl.id: {'actual': 0, 'budget': 0, 'prev': 0} for pl in product_lines}
            
            for country in region.country_ids:
                country_id = country.id
                
                # YTD values
                ytd_act = ytd_actual.get(country_id, 0)
                ytd_bud = sum(ytd_budget.get(country_id, {}).values())
                ytd_prv = ytd_prev.get(country_id, 0)
                
                region_ytd_actual += ytd_act
                region_ytd_budget += ytd_bud
                region_ytd_prev += ytd_prv
                
                for pl in product_lines:
                    actual = actual_data.get(country_id, {}).get(pl.id, 0)
                    budget = budget_data.get(country_id, {}).get(pl.id, 0)
                    prev = prev_actual_data.get(country_id, {}).get(pl.id, 0)
                    
                    region_pl_data[pl.id]['actual'] += actual
                    region_pl_data[pl.id]['budget'] += budget
                    region_pl_data[pl.id]['prev'] += prev
            
            # Write region totals
            worksheet.write(row, 1, region_ytd_actual, formats['number_bold'])
            worksheet.write(row, 2, region_ytd_budget, formats['number_bold'])
            worksheet.write(row, 3, region_ytd_prev, formats['number_bold'])
            
            grand_totals['ytd_actual'] += region_ytd_actual
            grand_totals['ytd_budget'] += region_ytd_budget
            grand_totals['ytd_prev'] += region_ytd_prev
            
            col = 4
            for pl in product_lines:
                actual = region_pl_data[pl.id]['actual']
                budget = region_pl_data[pl.id]['budget']
                prev = region_pl_data[pl.id]['prev']
                var_amt, var_pct = self._calculate_variance(actual, budget)
                yoy_var_amt, yoy_var_pct = self._calculate_variance(actual, prev)
                
                worksheet.write(row, col, actual, formats['number_bold'])
                worksheet.write(row, col + 1, budget, formats['number_bold'])
                worksheet.write(row, col + 2, var_amt, formats['number_bold'])
                worksheet.write(row, col + 3, var_pct / 100, formats['percent_bold'])
                worksheet.write(row, col + 4, prev, formats['number_bold'])
                worksheet.write(row, col + 5, yoy_var_amt, formats['number_bold'])
                worksheet.write(row, col + 6, yoy_var_pct / 100, formats['percent_bold'])
                
                grand_totals['by_pl'][pl.id]['actual'] += actual
                grand_totals['by_pl'][pl.id]['budget'] += budget
                grand_totals['by_pl'][pl.id]['prev'] += prev
                col += 7
            
            row += 1
            
            # Country rows under each region
            for country in region.country_ids:
                country_id = country.id
                worksheet.write(row, 0, country.name, formats['country'])
                
                # YTD values
                ytd_act = ytd_actual.get(country_id, 0)
                ytd_bud = sum(ytd_budget.get(country_id, {}).values())
                ytd_prv = ytd_prev.get(country_id, 0)
                
                worksheet.write(row, 1, ytd_act, formats['number'])
                worksheet.write(row, 2, ytd_bud, formats['number'])
                worksheet.write(row, 3, ytd_prv, formats['number'])
                
                col = 4
                for pl in product_lines:
                    actual = actual_data.get(country_id, {}).get(pl.id, 0)
                    budget = budget_data.get(country_id, {}).get(pl.id, 0)
                    prev = prev_actual_data.get(country_id, {}).get(pl.id, 0)
                    var_amt, var_pct = self._calculate_variance(actual, budget)
                    yoy_var_amt, yoy_var_pct = self._calculate_variance(actual, prev)
                    
                    worksheet.write(row, col, actual, formats['number'])
                    worksheet.write(row, col + 1, budget, formats['number'])
                    worksheet.write(row, col + 2, var_amt, formats['number'])
                    worksheet.write(row, col + 3, var_pct / 100, formats['percent'])
                    worksheet.write(row, col + 4, prev, formats['number'])
                    worksheet.write(row, col + 5, yoy_var_amt, formats['number'])
                    worksheet.write(row, col + 6, yoy_var_pct / 100, formats['percent'])
                    col += 7
                
                row += 1
        
        # Intercompany Sales row
        if intercompany_data:
            worksheet.write(row, 0, 'Intercompany Sales', formats['intercompany'])
            worksheet.write(row, 1, '', formats['intercompany'])
            worksheet.write(row, 2, '', formats['intercompany'])
            worksheet.write(row, 3, '', formats['intercompany'])
            
            col = 4
            for pl in product_lines:
                ic_amount = intercompany_data.get(pl.id, 0)
                worksheet.write(row, col, ic_amount, formats['number'])
                worksheet.write(row, col + 1, '', formats['number'])
                worksheet.write(row, col + 2, '', formats['number'])
                worksheet.write(row, col + 3, '', formats['percent'])
                worksheet.write(row, col + 4, '', formats['number'])
                worksheet.write(row, col + 5, '', formats['number'])
                worksheet.write(row, col + 6, '', formats['percent'])
                col += 7
            row += 1
        
        # Grand Total row
        worksheet.write(row, 0, 'GRAND TOTAL', formats['total'])
        worksheet.write(row, 1, grand_totals['ytd_actual'], formats['total'])
        worksheet.write(row, 2, grand_totals['ytd_budget'], formats['total'])
        worksheet.write(row, 3, grand_totals['ytd_prev'], formats['total'])
        
        col = 4
        for pl in product_lines:
            actual = grand_totals['by_pl'][pl.id]['actual']
            budget = grand_totals['by_pl'][pl.id]['budget']
            prev = grand_totals['by_pl'][pl.id]['prev']
            var_amt, var_pct = self._calculate_variance(actual, budget)
            yoy_var_amt, yoy_var_pct = self._calculate_variance(actual, prev)
            
            worksheet.write(row, col, actual, formats['total'])
            worksheet.write(row, col + 1, budget, formats['total'])
            worksheet.write(row, col + 2, var_amt, formats['total'])
            worksheet.write(row, col + 3, var_pct / 100, formats['percent_bold'])
            worksheet.write(row, col + 4, prev, formats['total'])
            worksheet.write(row, col + 5, yoy_var_amt, formats['total'])
            worksheet.write(row, col + 6, yoy_var_pct / 100, formats['percent_bold'])
            col += 7
    
    def _generate_salesperson_report(self, workbook):
        """Generate salesperson-wise report"""
        worksheet = workbook.add_worksheet('Budget vs Actual by Salesperson')
        formats = self._setup_formats(workbook)
        
        # Get data
        year = self.year
        prev_year = str(int(year) - 1)
        product_lines = self._get_product_lines()
        
        actual_data, intercompany_data = self._get_actual_sales_data(year, 'salesperson')
        budget_data = self._get_budget_data(year, 'salesperson')
        prev_actual_data, _ = self._get_actual_sales_data(prev_year, 'salesperson')
        ytd_actual = self._get_ytd_actual(year, 'salesperson')
        ytd_prev = self._get_ytd_actual(prev_year, 'salesperson')
        ytd_budget = self._get_budget_data(year, 'salesperson')
        
        # Get all salespersons with data
        salesperson_ids = set(actual_data.keys()) | set(budget_data.keys()) | set(prev_actual_data.keys())
        salespersons = self.env['res.users'].browse(list(salesperson_ids))
        
        row = 0
        col = 0
        
        # Title
        worksheet.merge_range(row, 0, row, 6 + len(product_lines) * 7, 
                             f'Sales Analysis - Budget vs Actual Report ({year})', formats['title'])
        row += 2
        
        # Header row 1
        worksheet.write(row, 0, 'Salesperson', formats['header'])
        worksheet.write(row, 1, f'YTD Actual {year}', formats['header'])
        worksheet.write(row, 2, f'YTD Budget {year}', formats['header'])
        worksheet.write(row, 3, f'YTD Prev {prev_year}', formats['header'])
        
        col = 4
        for pl in product_lines:
            worksheet.merge_range(row, col, row, col + 6, pl.name, formats['header_product'])
            col += 7
        
        row += 1
        
        # Header row 2
        worksheet.write(row, 0, '', formats['header'])
        worksheet.write(row, 1, '', formats['header'])
        worksheet.write(row, 2, '', formats['header'])
        worksheet.write(row, 3, '', formats['header'])
        
        col = 4
        for pl in product_lines:
            worksheet.write(row, col, f'Actual {year}', formats['header'])
            worksheet.write(row, col + 1, f'Budget {year}', formats['header'])
            worksheet.write(row, col + 2, 'Var Amt', formats['header'])
            worksheet.write(row, col + 3, 'Var %', formats['header'])
            worksheet.write(row, col + 4, f'Prev {prev_year}', formats['header'])
            worksheet.write(row, col + 5, 'YoY Var Amt', formats['header'])
            worksheet.write(row, col + 6, 'YoY Var %', formats['header'])
            col += 7
        
        row += 1
        
        # Set column widths
        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 3, 15)
        worksheet.set_column(4, 4 + len(product_lines) * 7, 12)
        
        grand_totals = {
            'ytd_actual': 0, 'ytd_budget': 0, 'ytd_prev': 0,
            'by_pl': {pl.id: {'actual': 0, 'budget': 0, 'prev': 0} for pl in product_lines}
        }
        
        # Data rows - by salesperson
        for user in salespersons.sorted(key=lambda u: u.name):
            user_id = user.id
            worksheet.write(row, 0, user.name or 'Unassigned', formats['country'])
            
            # YTD values
            ytd_act = ytd_actual.get(user_id, 0)
            ytd_bud = sum(ytd_budget.get(user_id, {}).values())
            ytd_prv = ytd_prev.get(user_id, 0)
            
            worksheet.write(row, 1, ytd_act, formats['number'])
            worksheet.write(row, 2, ytd_bud, formats['number'])
            worksheet.write(row, 3, ytd_prv, formats['number'])
            
            grand_totals['ytd_actual'] += ytd_act
            grand_totals['ytd_budget'] += ytd_bud
            grand_totals['ytd_prev'] += ytd_prv
            
            col = 4
            for pl in product_lines:
                actual = actual_data.get(user_id, {}).get(pl.id, 0)
                budget = budget_data.get(user_id, {}).get(pl.id, 0)
                prev = prev_actual_data.get(user_id, {}).get(pl.id, 0)
                var_amt, var_pct = self._calculate_variance(actual, budget)
                yoy_var_amt, yoy_var_pct = self._calculate_variance(actual, prev)
                
                worksheet.write(row, col, actual, formats['number'])
                worksheet.write(row, col + 1, budget, formats['number'])
                worksheet.write(row, col + 2, var_amt, formats['number'])
                worksheet.write(row, col + 3, var_pct / 100, formats['percent'])
                worksheet.write(row, col + 4, prev, formats['number'])
                worksheet.write(row, col + 5, yoy_var_amt, formats['number'])
                worksheet.write(row, col + 6, yoy_var_pct / 100, formats['percent'])
                
                grand_totals['by_pl'][pl.id]['actual'] += actual
                grand_totals['by_pl'][pl.id]['budget'] += budget
                grand_totals['by_pl'][pl.id]['prev'] += prev
                col += 7
            
            row += 1
        
        # Intercompany Sales row
        if intercompany_data:
            worksheet.write(row, 0, 'Intercompany Sales', formats['intercompany'])
            worksheet.write(row, 1, '', formats['intercompany'])
            worksheet.write(row, 2, '', formats['intercompany'])
            worksheet.write(row, 3, '', formats['intercompany'])
            
            col = 4
            for pl in product_lines:
                ic_amount = intercompany_data.get(pl.id, 0)
                worksheet.write(row, col, ic_amount, formats['number'])
                worksheet.write(row, col + 1, '', formats['number'])
                worksheet.write(row, col + 2, '', formats['number'])
                worksheet.write(row, col + 3, '', formats['percent'])
                worksheet.write(row, col + 4, '', formats['number'])
                worksheet.write(row, col + 5, '', formats['number'])
                worksheet.write(row, col + 6, '', formats['percent'])
                col += 7
            row += 1
        
        # Grand Total row
        worksheet.write(row, 0, 'GRAND TOTAL', formats['total'])
        worksheet.write(row, 1, grand_totals['ytd_actual'], formats['total'])
        worksheet.write(row, 2, grand_totals['ytd_budget'], formats['total'])
        worksheet.write(row, 3, grand_totals['ytd_prev'], formats['total'])
        
        col = 4
        for pl in product_lines:
            actual = grand_totals['by_pl'][pl.id]['actual']
            budget = grand_totals['by_pl'][pl.id]['budget']
            prev = grand_totals['by_pl'][pl.id]['prev']
            var_amt, var_pct = self._calculate_variance(actual, budget)
            yoy_var_amt, yoy_var_pct = self._calculate_variance(actual, prev)
            
            worksheet.write(row, col, actual, formats['total'])
            worksheet.write(row, col + 1, budget, formats['total'])
            worksheet.write(row, col + 2, var_amt, formats['total'])
            worksheet.write(row, col + 3, var_pct / 100, formats['percent_bold'])
            worksheet.write(row, col + 4, prev, formats['total'])
            worksheet.write(row, col + 5, yoy_var_amt, formats['total'])
            worksheet.write(row, col + 6, yoy_var_pct / 100, formats['percent_bold'])
            col += 7
