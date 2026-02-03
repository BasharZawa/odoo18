# -*- coding: utf-8 -*-

import datetime
from lxml import etree

from odoo import models, fields, tools, api, _


class SalesRecognitionReport(models.Model):
    """
    SQL View Report: Sales Recognition by Order
    
    Shows revenue recognition schedule breakdown by sales order:
    - Order details: Order No, Customer, End User, Sector, Salesperson, Country
    - Payment status from linked invoices
    - Monthly recognition amounts for the selected year
    - Carry forward amounts for future years
    - Recognition coverage and status indicators
    
    Data Sources:
    - sale.order: Sales order header
    - sale.order.recognition.schedule: Revenue recognition schedule lines
    - account.move: Invoice payment status
    - product.line.ept: Product line classification
    """
    _name = 'sales.recognition.report'
    _description = 'Sales Recognition Report'
    _auto = False
    _order = 'order_date desc, order_name'

    # Order Identification
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    order_name = fields.Char(string='Order No', readonly=True)
    
    # Customer Information
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    end_user_id = fields.Many2one('res.partner', string='End User', readonly=True)
    sector_id = fields.Many2one('res.partner.industry', string='Sector', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    
    # Sales Information
    salesperson_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', readonly=True)
    order_date = fields.Date(string='Order Date', readonly=True)
    
    # Product Classification
    product_lines = fields.Char(string='Product Lines', readonly=True)
    
    # Payment Status
    payment_status = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
    ], string='Payment Status', readonly=True)
    
    # Order Totals
    order_total = fields.Monetary(
        string='Order Total', 
        readonly=True, 
        aggregator='sum',
        currency_field='currency_id'
    )
    
    # Recognition Totals
    total_scheduled = fields.Monetary(
        string='Total Scheduled',
        readonly=True,
        aggregator='sum',
        currency_field='currency_id',
        help='Total amount scheduled for recognition'
    )
    recognition_coverage_pct = fields.Float(
        string='Coverage %',
        readonly=True,
        aggregator='avg',
        help='Percentage of order covered by recognition schedule'
    )
    
    # Recognition Status
    recognition_status = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('complete', 'Complete'),
    ], string='Recognition Status', readonly=True)
    
    # Monthly Recognition Amounts (current year context)
    jan_amount = fields.Monetary(string='Jan', readonly=True, aggregator='sum', currency_field='currency_id')
    feb_amount = fields.Monetary(string='Feb', readonly=True, aggregator='sum', currency_field='currency_id')
    mar_amount = fields.Monetary(string='Mar', readonly=True, aggregator='sum', currency_field='currency_id')
    apr_amount = fields.Monetary(string='Apr', readonly=True, aggregator='sum', currency_field='currency_id')
    may_amount = fields.Monetary(string='May', readonly=True, aggregator='sum', currency_field='currency_id')
    jun_amount = fields.Monetary(string='Jun', readonly=True, aggregator='sum', currency_field='currency_id')
    jul_amount = fields.Monetary(string='Jul', readonly=True, aggregator='sum', currency_field='currency_id')
    aug_amount = fields.Monetary(string='Aug', readonly=True, aggregator='sum', currency_field='currency_id')
    sep_amount = fields.Monetary(string='Sep', readonly=True, aggregator='sum', currency_field='currency_id')
    oct_amount = fields.Monetary(string='Oct', readonly=True, aggregator='sum', currency_field='currency_id')
    nov_amount = fields.Monetary(string='Nov', readonly=True, aggregator='sum', currency_field='currency_id')
    dec_amount = fields.Monetary(string='Dec', readonly=True, aggregator='sum', currency_field='currency_id')
    
    # Current Year Total
    current_year_total = fields.Monetary(
        string='Year Total',
        readonly=True,
        aggregator='sum',
        currency_field='currency_id'
    )
    
    # Carry Forward columns (future years)
    cf_year_1 = fields.Monetary(string='C/F +1', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_2 = fields.Monetary(string='C/F +2', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_3 = fields.Monetary(string='C/F +3', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_4 = fields.Monetary(string='C/F +4', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_5 = fields.Monetary(string='C/F +5', readonly=True, aggregator='sum', currency_field='currency_id')
    
    # Past Recognition (before current year)
    past_recognized = fields.Monetary(
        string='Past Recognized',
        readonly=True,
        aggregator='sum',
        currency_field='currency_id'
    )
    
    # Currency/Company
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    
    # Report Year (for filtering)
    report_year = fields.Integer(string='Report Year', readonly=True)

    def _get_report_year(self):
        """Get the current year for the report.
        
        Since the report now only shows current year data, this simply returns the current year.
        """
        return datetime.date.today().year

    def get_view(self, view_id=None, view_type='form', **options):
        """Override to dynamically set column labels with actual years for months and carry forward."""
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        
        if view_type not in ('tree', 'list', 'pivot'):
            return res
        
        # Get the current year for dynamic labels
        report_year = self._get_report_year()
        arch = etree.fromstring(res['arch'])
        
        # Map month fields to labels with current year
        month_labels = {
            'jan_amount': f'Jan {report_year}',
            'feb_amount': f'Feb {report_year}',
            'mar_amount': f'Mar {report_year}',
            'apr_amount': f'Apr {report_year}',
            'may_amount': f'May {report_year}',
            'jun_amount': f'Jun {report_year}',
            'jul_amount': f'Jul {report_year}',
            'aug_amount': f'Aug {report_year}',
            'sep_amount': f'Sep {report_year}',
            'oct_amount': f'Oct {report_year}',
            'nov_amount': f'Nov {report_year}',
            'dec_amount': f'Dec {report_year}',
            'current_year_total': f'Total {report_year}',
            'past_recognized': f'Before {report_year}',
        }
        
        # Map C/F fields to actual future years
        cf_labels = {
            'cf_year_1': str(report_year + 1),
            'cf_year_2': str(report_year + 2),
            'cf_year_3': str(report_year + 3),
            'cf_year_4': str(report_year + 4),
            'cf_year_5': str(report_year + 5),
        }
        
        # Update labels
        for field_name, label in {**month_labels, **cf_labels}.items():
            for node in arch.xpath(f"//field[@name='{field_name}']"):
                node.set('string', label)
                if node.get('sum'):
                    node.set('sum', label)
        
        res['arch'] = etree.tostring(arch, encoding='unicode')
        return res

    def init(self):
        """Create the SQL view for Sales Recognition Report.
        
        Report logic:
        - Only shows ACTIVE orders (state = 'sale', not closed/done)
        - Only shows orders that have ANY upcoming recognition schedules (current year or future)
        - Monthly breakdown is ONLY for current year
        - Past years' recognition is aggregated into 'past_recognized'
        - Future years shown as carry forward (CF+1 to CF+5)
        """
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH
                    -- Current year constant
                    current_year AS (
                        SELECT EXTRACT(YEAR FROM CURRENT_DATE)::int AS yr
                    ),
                    
                    -- Orders with upcoming recognition (current year or future)
                    -- This determines which orders to include
                    orders_with_upcoming AS (
                        SELECT DISTINCT sors.sale_order_id AS order_id
                        FROM sale_order_recognition_schedule sors
                        CROSS JOIN current_year cy
                        WHERE EXTRACT(YEAR FROM sors.recognition_date)::int >= cy.yr
                    ),
                    
                    -- Aggregate product lines per order
                    order_product_lines AS (
                        SELECT
                            so.id AS order_id,
                            COALESCE(
                                string_agg(DISTINCT ple.name, ', ' ORDER BY ple.name), 
                                ''
                            ) AS product_lines
                        FROM sale_order so
                        JOIN sale_order_line sol ON sol.order_id = so.id
                        LEFT JOIN product_product pp ON pp.id = sol.product_id
                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        LEFT JOIN product_line_ept ple ON ple.id = pt.product_line_id
                        WHERE so.state = 'sale'  -- Only active orders
                        GROUP BY so.id
                    ),
                    
                    -- Invoice payment status per order
                    order_payment_status AS (
                        SELECT
                            so.id AS order_id,
                            COUNT(DISTINCT am.id) FILTER (
                                WHERE am.state = 'posted' 
                                AND am.move_type IN ('out_invoice', 'out_refund')
                            ) AS invoice_count,
                            COUNT(DISTINCT am.id) FILTER (
                                WHERE am.state = 'posted' 
                                AND am.move_type IN ('out_invoice', 'out_refund')
                                AND am.payment_state = 'paid'
                            ) AS paid_count,
                            COUNT(DISTINCT am.id) FILTER (
                                WHERE am.state = 'posted' 
                                AND am.move_type IN ('out_invoice', 'out_refund')
                                AND am.payment_state IN ('paid', 'partial')
                            ) AS any_paid_count
                        FROM sale_order so
                        LEFT JOIN sale_order_line sol ON sol.order_id = so.id
                        LEFT JOIN sale_order_line_invoice_rel rel ON rel.order_line_id = sol.id
                        LEFT JOIN account_move_line aml ON aml.id = rel.invoice_line_id
                        LEFT JOIN account_move am ON am.id = aml.move_id
                        WHERE so.state = 'sale'  -- Only active orders
                        GROUP BY so.id
                    ),
                    
                    -- Recognition schedule aggregation per order (current year focus)
                    recognition_agg AS (
                        SELECT
                            sors.sale_order_id AS order_id,
                            cy.yr AS report_year,
                            
                            -- Total scheduled (all time)
                            SUM(sors.amount) AS total_scheduled,
                            
                            -- Past recognition (before current year)
                            SUM(CASE 
                                WHEN EXTRACT(YEAR FROM sors.recognition_date)::int < cy.yr 
                                THEN sors.amount ELSE 0 
                            END) AS past_recognized,
                            
                            -- Monthly amounts ONLY for current year
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 1 
                                THEN sors.amount ELSE 0 END) AS jan_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 2 
                                THEN sors.amount ELSE 0 END) AS feb_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 3 
                                THEN sors.amount ELSE 0 END) AS mar_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 4 
                                THEN sors.amount ELSE 0 END) AS apr_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 5 
                                THEN sors.amount ELSE 0 END) AS may_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 6 
                                THEN sors.amount ELSE 0 END) AS jun_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 7 
                                THEN sors.amount ELSE 0 END) AS jul_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 8 
                                THEN sors.amount ELSE 0 END) AS aug_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 9 
                                THEN sors.amount ELSE 0 END) AS sep_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 10 
                                THEN sors.amount ELSE 0 END) AS oct_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 11 
                                THEN sors.amount ELSE 0 END) AS nov_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 12 
                                THEN sors.amount ELSE 0 END) AS dec_amount,
                            
                            -- Current year total
                            SUM(CASE 
                                WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                THEN sors.amount ELSE 0 
                            END) AS current_year_total,
                            
                            -- Carry forward for future years (relative to current year)
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 1 
                                THEN sors.amount ELSE 0 END) AS cf_year_1,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 2 
                                THEN sors.amount ELSE 0 END) AS cf_year_2,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 3 
                                THEN sors.amount ELSE 0 END) AS cf_year_3,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 4 
                                THEN sors.amount ELSE 0 END) AS cf_year_4,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 5 
                                THEN sors.amount ELSE 0 END) AS cf_year_5
                            
                        FROM sale_order_recognition_schedule sors
                        CROSS JOIN current_year cy
                        GROUP BY sors.sale_order_id, cy.yr
                    )
                    
                SELECT
                    -- Unique ID: use order_id directly (one row per active order)
                    so.id AS id,
                    so.id AS sale_order_id,
                    so.name AS order_name,
                    so.partner_id,
                    so.end_customer_id AS end_user_id,
                    rp.industry_id AS sector_id,
                    rp.country_id,
                    so.user_id AS salesperson_id,
                    so.team_id,
                    so.date_order::date AS order_date,
                    
                    -- Product lines
                    opl.product_lines,
                    
                    -- Payment status
                    CASE
                        WHEN ops.invoice_count = 0 OR ops.invoice_count IS NULL THEN 'not_invoiced'
                        WHEN ops.paid_count = ops.invoice_count THEN 'paid'
                        WHEN ops.any_paid_count > 0 THEN 'partial'
                        ELSE 'unpaid'
                    END AS payment_status,
                    
                    -- Order total
                    so.amount_untaxed AS order_total,
                    
                    -- Recognition totals
                    COALESCE(ra.total_scheduled, 0) AS total_scheduled,
                    CASE 
                        WHEN so.amount_untaxed = 0 THEN 0
                        ELSE ROUND((COALESCE(ra.total_scheduled, 0) / so.amount_untaxed * 100)::numeric, 2)
                    END AS recognition_coverage_pct,
                    
                    -- Recognition status
                    CASE
                        WHEN COALESCE(ra.total_scheduled, 0) = 0 THEN 'pending'
                        WHEN COALESCE(ra.total_scheduled, 0) >= so.amount_untaxed THEN 'complete'
                        ELSE 'partial'
                    END AS recognition_status,
                    
                    -- Past recognized (before current year)
                    COALESCE(ra.past_recognized, 0) AS past_recognized,
                    
                    -- Monthly amounts (current year only)
                    COALESCE(ra.jan_amount, 0) AS jan_amount,
                    COALESCE(ra.feb_amount, 0) AS feb_amount,
                    COALESCE(ra.mar_amount, 0) AS mar_amount,
                    COALESCE(ra.apr_amount, 0) AS apr_amount,
                    COALESCE(ra.may_amount, 0) AS may_amount,
                    COALESCE(ra.jun_amount, 0) AS jun_amount,
                    COALESCE(ra.jul_amount, 0) AS jul_amount,
                    COALESCE(ra.aug_amount, 0) AS aug_amount,
                    COALESCE(ra.sep_amount, 0) AS sep_amount,
                    COALESCE(ra.oct_amount, 0) AS oct_amount,
                    COALESCE(ra.nov_amount, 0) AS nov_amount,
                    COALESCE(ra.dec_amount, 0) AS dec_amount,
                    
                    -- Current year total
                    COALESCE(ra.current_year_total, 0) AS current_year_total,
                    
                    -- Carry forward (future years)
                    COALESCE(ra.cf_year_1, 0) AS cf_year_1,
                    COALESCE(ra.cf_year_2, 0) AS cf_year_2,
                    COALESCE(ra.cf_year_3, 0) AS cf_year_3,
                    COALESCE(ra.cf_year_4, 0) AS cf_year_4,
                    COALESCE(ra.cf_year_5, 0) AS cf_year_5,
                    
                    -- Report year (always current year)
                    ra.report_year,
                    
                    -- Currency/Company
                    so.currency_id,
                    so.company_id
                    
                FROM sale_order so
                JOIN res_partner rp ON rp.id = so.partner_id
                -- Only orders with upcoming recognition (current year or future)
                JOIN orders_with_upcoming owu ON owu.order_id = so.id
                LEFT JOIN order_product_lines opl ON opl.order_id = so.id
                LEFT JOIN order_payment_status ops ON ops.order_id = so.id
                LEFT JOIN recognition_agg ra ON ra.order_id = so.id
                
                -- Only active (non-closed) orders
                WHERE so.state = 'sale'
            )
        """ % self._table)

    def action_open_order(self):
        """Open the source sales order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }

    def action_open_recognition_schedule(self):
        """Open recognition schedule lines for this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recognition Schedule'),
            'res_model': 'sale.order.recognition.schedule',
            'view_mode': 'list',
            'domain': [('sale_order_id', '=', self.sale_order_id.id)],
            'context': {'default_sale_order_id': self.sale_order_id.id},
        }

    @api.model
    def action_open_report(self):
        """Open the Sales Recognition Report.
        
        Report automatically shows current year data for active orders with
        upcoming recognition schedules.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Recognition'),
            'res_model': 'sales.recognition.report',
            'view_mode': 'list,pivot,graph',
            'context': {},
        }
