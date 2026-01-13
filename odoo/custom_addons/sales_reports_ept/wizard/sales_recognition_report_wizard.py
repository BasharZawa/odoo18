# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter
import io
import base64
import datetime
from collections import defaultdict


class SalesRecognitionReportWizard(models.TransientModel):
    _name = 'sales.recognition.report.wizard'
    _description = 'Sales Recognition Report Wizard'

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        required=True,
        default=lambda self: str(datetime.date.today().year)
    )
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
    
    def _get_month_name(self, month_num):
        """Get month abbreviation"""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return months[month_num - 1]
    
    def _get_payment_status(self, order):
        """Get payment status from invoices related to the order"""
        invoices = order.invoice_ids.filtered(lambda i: i.state == 'posted')
        if not invoices:
            return 'Not Invoiced'
        
        all_paid = all(inv.payment_state == 'paid' for inv in invoices)
        any_paid = any(inv.payment_state in ['paid', 'partial'] for inv in invoices)
        
        if all_paid:
            return 'Paid'
        elif any_paid:
            return 'Partial'
        else:
            return 'Unpaid'
    
    def _get_product_lines_from_order(self, order):
        """Get unique product lines from order lines"""
        product_lines = set()
        for line in order.order_line:
            if line.product_id.product_tmpl_id.product_line_id:
                product_lines.add(line.product_id.product_tmpl_id.product_line_id.name)
        return ', '.join(sorted(product_lines)) if product_lines else ''
    
    def _get_recognition_by_month(self, order, year):
        """
        Get recognition amounts by month for a specific year.
        Returns dict: {month_num: amount}
        """
        monthly_data = {i: 0 for i in range(1, 13)}
        
        for schedule in order.recognition_schedule_ids:
            if schedule.recognition_date and schedule.recognition_date.year == int(year):
                month = schedule.recognition_date.month
                monthly_data[month] += schedule.amount
        
        return monthly_data
    
    def _get_carry_forward(self, order, year):
        """
        Get carry forward amounts for future years.
        Returns dict: {year: amount}
        """
        selected_year = int(year)
        cf_years = [selected_year + 1, selected_year + 2, selected_year + 3]
        cf_data = {y: 0 for y in cf_years}
        
        for schedule in order.recognition_schedule_ids:
            if schedule.recognition_date:
                sched_year = schedule.recognition_date.year
                if sched_year in cf_years:
                    cf_data[sched_year] += schedule.amount
        
        return cf_data
    
    def action_generate_report(self):
        """Generate the Sales Recognition Excel report"""
        self.ensure_one()
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        self._generate_recognition_report(workbook)
        filename = f'Sales_Recognition_Report_{self.year}.xlsx'
        
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
            'res_model': 'sales.recognition.report.wizard',
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
                'bold': True, 'font_size': 10, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#D9E2F3', 'border': 1,
                'text_wrap': True
            }),
            'header_month': workbook.add_format({
                'bold': True, 'font_size': 10, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#E2EFDA', 'border': 1,
                'text_wrap': True
            }),
            'header_cf': workbook.add_format({
                'bold': True, 'font_size': 10, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#FCE4D6', 'border': 1,
                'text_wrap': True
            }),
            'text': workbook.add_format({
                'font_size': 10, 'border': 1, 'valign': 'vcenter',
                'text_wrap': True
            }),
            'text_center': workbook.add_format({
                'font_size': 10, 'border': 1, 'valign': 'vcenter',
                'align': 'center'
            }),
            'number': workbook.add_format({
                'font_size': 10, 'border': 1, 'num_format': '#,##0.00',
                'align': 'right', 'valign': 'vcenter'
            }),
            'number_month': workbook.add_format({
                'font_size': 10, 'border': 1, 'num_format': '#,##0.00',
                'align': 'right', 'valign': 'vcenter', 'bg_color': '#F2F8EE'
            }),
            'number_cf': workbook.add_format({
                'font_size': 10, 'border': 1, 'num_format': '#,##0.00',
                'align': 'right', 'valign': 'vcenter', 'bg_color': '#FDF5EE'
            }),
            'date': workbook.add_format({
                'font_size': 10, 'border': 1, 'num_format': 'yyyy-mm-dd',
                'align': 'center', 'valign': 'vcenter'
            }),
            'total': workbook.add_format({
                'bold': True, 'font_size': 11, 'border': 2,
                'bg_color': '#4472C4', 'font_color': 'white',
                'num_format': '#,##0.00', 'align': 'right', 'valign': 'vcenter'
            }),
            'total_label': workbook.add_format({
                'bold': True, 'font_size': 11, 'border': 2,
                'bg_color': '#4472C4', 'font_color': 'white',
                'align': 'right', 'valign': 'vcenter'
            }),
        }
        return formats
    
    def _generate_recognition_report(self, workbook):
        """Generate the Sales Recognition Report"""
        worksheet = workbook.add_worksheet('Sales Recognition')
        formats = self._setup_formats(workbook)
        
        year = self.year
        selected_year = int(year)
        cf_years = [selected_year + 1, selected_year + 2, selected_year + 3]
        
        # Get confirmed sales orders
        domain = [
            ('state', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ]
        orders = self.env['sale.order'].search(domain, order='date_order')
        
        # Filter orders that have recognition schedule entries for the selected year or CF years
        relevant_orders = orders.filtered(
            lambda o: o.recognition_schedule_ids and any(
                s.recognition_date and (
                    s.recognition_date.year == selected_year or 
                    s.recognition_date.year in cf_years
                )
                for s in o.recognition_schedule_ids
            )
        )
        
        row = 0
        
        # Title
        total_cols = 10 + 12 + 3  # Base cols + 12 months + 3 CF years
        worksheet.merge_range(row, 0, row, total_cols - 1, 
                             f'Sales Recognition Report - {year}', formats['title'])
        row += 2
        
        # Header row
        headers = [
            ('Order No', 12),
            ('Customer Name', 25),
            ('Payment Status', 12),
            ('End User', 20),
            ('Sector', 15),
            ('Salesperson', 18),
            ('Country', 12),
            ('Class of Product', 20),
            ('Order Date', 12),
            ('Total', 15),
        ]
        
        col = 0
        for header, width in headers:
            worksheet.write(row, col, header, formats['header'])
            worksheet.set_column(col, col, width)
            col += 1
        
        # Month columns
        for month in range(1, 13):
            month_name = f"{self._get_month_name(month)} {year}"
            worksheet.write(row, col, month_name, formats['header_month'])
            worksheet.set_column(col, col, 12)
            col += 1
        
        # Carry forward columns
        for cf_year in cf_years:
            worksheet.write(row, col, f'C/F {cf_year}', formats['header_cf'])
            worksheet.set_column(col, col, 12)
            col += 1
        
        row += 1
        
        # Initialize totals
        totals = {
            'total': 0,
            'months': {i: 0 for i in range(1, 13)},
            'cf': {y: 0 for y in cf_years}
        }
        
        # Data rows
        for order in relevant_orders:
            col = 0
            
            # Order No
            worksheet.write(row, col, order.name, formats['text'])
            col += 1
            
            # Customer Name
            worksheet.write(row, col, order.partner_id.name or '', formats['text'])
            col += 1
            
            # Payment Status
            payment_status = self._get_payment_status(order)
            worksheet.write(row, col, payment_status, formats['text_center'])
            col += 1
            
            # End User
            end_user = order.end_customer_id.name if hasattr(order, 'end_customer_id') and order.end_customer_id else ''
            worksheet.write(row, col, end_user, formats['text'])
            col += 1
            
            # Sector (Industry)
            sector = order.partner_id.industry_id.name if order.partner_id.industry_id else ''
            worksheet.write(row, col, sector, formats['text'])
            col += 1
            
            # Salesperson
            worksheet.write(row, col, order.user_id.name if order.user_id else '', formats['text'])
            col += 1
            
            # Country
            worksheet.write(row, col, order.partner_id.country_id.name if order.partner_id.country_id else '', formats['text'])
            col += 1
            
            # Class of Product (Product Lines)
            product_lines = self._get_product_lines_from_order(order)
            worksheet.write(row, col, product_lines, formats['text'])
            col += 1
            
            # Order Date
            worksheet.write(row, col, order.date_order.date() if order.date_order else '', formats['date'])
            col += 1
            
            # Total (Order amount with taxes)
            worksheet.write(row, col, order.amount_total, formats['number'])
            totals['total'] += order.amount_total
            col += 1
            
            # Monthly recognition amounts
            monthly_data = self._get_recognition_by_month(order, year)
            for month in range(1, 13):
                amount = monthly_data.get(month, 0)
                worksheet.write(row, col, amount if amount else '', formats['number_month'])
                totals['months'][month] += amount
                col += 1
            
            # Carry forward amounts
            cf_data = self._get_carry_forward(order, year)
            for cf_year in cf_years:
                amount = cf_data.get(cf_year, 0)
                worksheet.write(row, col, amount if amount else '', formats['number_cf'])
                totals['cf'][cf_year] += amount
                col += 1
            
            row += 1
        
        # Total row
        col = 0
        worksheet.merge_range(row, 0, row, 8, 'TOTAL', formats['total_label'])
        col = 9
        
        # Total amount
        worksheet.write(row, col, totals['total'], formats['total'])
        col += 1
        
        # Monthly totals
        for month in range(1, 13):
            worksheet.write(row, col, totals['months'][month], formats['total'])
            col += 1
        
        # CF totals
        for cf_year in cf_years:
            worksheet.write(row, col, totals['cf'][cf_year], formats['total'])
            col += 1
        
        # Freeze panes
        worksheet.freeze_panes(3, 1)
