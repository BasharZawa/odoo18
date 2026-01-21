# -*- coding: utf-8 -*-

import datetime
from lxml import etree

from odoo import models, fields, tools


class CustomerSalesReport(models.Model):
    """
    SQL View Report: Sales Recognition by Order (Current Year)
    
    Columns:
    - Order No, Customer Name, Payment Status, End User, Sector, Salesperson,
      Country, Class of Product, Order Date, Total
    - Monthly breakdown: Jan - Dec (current year only)
    - Carry Forward: C/F columns for future years with recognition schedule
    
    Shows only orders that have recognition schedule entries for the current year or future.
    """
    _name = 'customer.sales.report'
    _description = 'Sales Recognition Report'
    _auto = False
    _order = 'order_date desc, order_no'

    # Order dimensions
    sale_order_id = fields.Many2one('sale.order', string='Order', readonly=True)
    order_no = fields.Char(string='Order No', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer Name', readonly=True)
    payment_status = fields.Char(string='Payment Status', readonly=True)
    end_user_id = fields.Many2one('res.partner', string='End User', readonly=True)
    sector_id = fields.Many2one('res.partner.industry', string='Sector', readonly=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    class_of_product = fields.Char(string='Class of Product', readonly=True)
    order_date = fields.Date(string='Order Date', readonly=True)
    
    # Total (order untaxed amount)
    total_amount = fields.Monetary(string='Total', readonly=True, aggregator='sum', currency_field='currency_id')
    
    # Monthly Recognition Amounts (current year)
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
    
    # Carry Forward columns for future years (up to 5 years ahead)
    cf_year_1 = fields.Monetary(string='C/F Year+1', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_2 = fields.Monetary(string='C/F Year+2', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_3 = fields.Monetary(string='C/F Year+3', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_4 = fields.Monetary(string='C/F Year+4', readonly=True, aggregator='sum', currency_field='currency_id')
    cf_year_5 = fields.Monetary(string='C/F Year+5', readonly=True, aggregator='sum', currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def _get_current_year(self):
        return datetime.date.today().year

    def get_view(self, view_id=None, view_type='form', **options):
        """Override to dynamically set column labels with actual years."""
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        
        if view_type not in ('tree', 'list', 'pivot'):
            return res
        
        current_year = self._get_current_year()
        arch = etree.fromstring(res['arch'])
        
        # Map month fields to labels with year
        month_labels = {
            'jan_amount': f'Jan {current_year}',
            'feb_amount': f'Feb {current_year}',
            'mar_amount': f'Mar {current_year}',
            'apr_amount': f'Apr {current_year}',
            'may_amount': f'May {current_year}',
            'jun_amount': f'Jun {current_year}',
            'jul_amount': f'Jul {current_year}',
            'aug_amount': f'Aug {current_year}',
            'sep_amount': f'Sep {current_year}',
            'oct_amount': f'Oct {current_year}',
            'nov_amount': f'Nov {current_year}',
            'dec_amount': f'Dec {current_year}',
        }
        
        # Map C/F fields to actual years
        cf_labels = {
            'cf_year_1': f'C/F {current_year + 1}',
            'cf_year_2': f'C/F {current_year + 2}',
            'cf_year_3': f'C/F {current_year + 3}',
            'cf_year_4': f'C/F {current_year + 4}',
            'cf_year_5': f'C/F {current_year + 5}',
        }
        
        # Update month column labels
        for field_name, label in month_labels.items():
            for node in arch.xpath(f"//field[@name='{field_name}']"):
                node.set('string', label)
                if node.get('sum'):
                    node.set('sum', label)
        
        # Update C/F column labels
        for field_name, label in cf_labels.items():
            for node in arch.xpath(f"//field[@name='{field_name}']"):
                node.set('string', label)
                if node.get('sum'):
                    node.set('sum', label)
        
        res['arch'] = etree.tostring(arch, encoding='unicode')
        return res

    def init(self):
        """Create the SQL view for Sales Recognition Report - Order Level, Current Year."""
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH
                    current_year AS (
                        SELECT EXTRACT(YEAR FROM CURRENT_DATE)::int AS yr
                    ),
                    -- Aggregate product lines per order
                    product_lines AS (
                        SELECT
                            so.id AS order_id,
                            COALESCE(string_agg(DISTINCT pl.name, ', ' ORDER BY pl.name), '') AS product_lines
                        FROM sale_order so
                        JOIN sale_order_line sol ON sol.order_id = so.id
                        JOIN product_product pp ON pp.id = sol.product_id
                        JOIN product_template pt ON pt.id = pp.product_tmpl_id
                        LEFT JOIN product_line pl ON pl.id = pt.product_line_id
                        WHERE so.state = 'sale'
                        GROUP BY so.id
                    ),
                    -- Invoice payment status per order
                    invoice_status AS (
                        SELECT
                            so.id AS order_id,
                            COUNT(DISTINCT am.id) FILTER (WHERE am.state = 'posted') AS posted_count,
                            COUNT(DISTINCT am.id) FILTER (WHERE am.state = 'posted' AND am.payment_state = 'paid') AS paid_count,
                            COUNT(DISTINCT am.id) FILTER (WHERE am.state = 'posted' AND am.payment_state IN ('paid', 'partial')) AS any_paid_count
                        FROM sale_order so
                        LEFT JOIN sale_order_line sol ON sol.order_id = so.id
                        LEFT JOIN sale_order_line_invoice_rel rel ON rel.order_line_id = sol.id
                        LEFT JOIN account_move_line aml ON aml.id = rel.invoice_line_id
                        LEFT JOIN account_move am ON am.id = aml.move_id AND am.move_type IN ('out_invoice', 'out_refund')
                        WHERE so.state = 'sale'
                        GROUP BY so.id
                    ),
                    -- Recognition amounts per order aggregated by current year months and future years
                    recognition AS (
                        SELECT
                            so.id AS order_id,
                            -- Current year monthly amounts
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 1 THEN sors.amount ELSE 0 END) AS jan_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 2 THEN sors.amount ELSE 0 END) AS feb_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 3 THEN sors.amount ELSE 0 END) AS mar_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 4 THEN sors.amount ELSE 0 END) AS apr_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 5 THEN sors.amount ELSE 0 END) AS may_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 6 THEN sors.amount ELSE 0 END) AS jun_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 7 THEN sors.amount ELSE 0 END) AS jul_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 8 THEN sors.amount ELSE 0 END) AS aug_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 9 THEN sors.amount ELSE 0 END) AS sep_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 10 THEN sors.amount ELSE 0 END) AS oct_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 11 THEN sors.amount ELSE 0 END) AS nov_amount,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr 
                                      AND EXTRACT(MONTH FROM sors.recognition_date) = 12 THEN sors.amount ELSE 0 END) AS dec_amount,
                            -- Carry forward for future years
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 1 THEN sors.amount ELSE 0 END) AS cf_year_1,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 2 THEN sors.amount ELSE 0 END) AS cf_year_2,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 3 THEN sors.amount ELSE 0 END) AS cf_year_3,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 4 THEN sors.amount ELSE 0 END) AS cf_year_4,
                            SUM(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int = cy.yr + 5 THEN sors.amount ELSE 0 END) AS cf_year_5,
                            -- Flag: has any recognition in current year or future
                            MAX(CASE WHEN EXTRACT(YEAR FROM sors.recognition_date)::int >= cy.yr THEN 1 ELSE 0 END) AS has_recognition
                        FROM sale_order so
                        JOIN sale_order_recognition_schedule sors ON sors.sale_order_id = so.id
                        CROSS JOIN current_year cy
                        WHERE so.state = 'sale'
                        GROUP BY so.id
                    )
                SELECT
                    so.id AS id,
                    so.id AS sale_order_id,
                    so.name AS order_no,
                    so.partner_id,
                    CASE
                        WHEN inv.posted_count = 0 OR inv.posted_count IS NULL THEN 'Not Invoiced'
                        WHEN inv.paid_count = inv.posted_count THEN 'Paid'
                        WHEN inv.any_paid_count > 0 THEN 'Partial'
                        ELSE 'Unpaid'
                    END AS payment_status,
                    so.end_customer_id AS end_user_id,
                    rp.industry_id AS sector_id,
                    so.user_id AS salesperson_id,
                    rp.country_id AS country_id,
                    pl.product_lines AS class_of_product,
                    so.date_order::date AS order_date,
                    so.amount_untaxed AS total_amount,
                    COALESCE(r.jan_amount, 0) AS jan_amount,
                    COALESCE(r.feb_amount, 0) AS feb_amount,
                    COALESCE(r.mar_amount, 0) AS mar_amount,
                    COALESCE(r.apr_amount, 0) AS apr_amount,
                    COALESCE(r.may_amount, 0) AS may_amount,
                    COALESCE(r.jun_amount, 0) AS jun_amount,
                    COALESCE(r.jul_amount, 0) AS jul_amount,
                    COALESCE(r.aug_amount, 0) AS aug_amount,
                    COALESCE(r.sep_amount, 0) AS sep_amount,
                    COALESCE(r.oct_amount, 0) AS oct_amount,
                    COALESCE(r.nov_amount, 0) AS nov_amount,
                    COALESCE(r.dec_amount, 0) AS dec_amount,
                    COALESCE(r.cf_year_1, 0) AS cf_year_1,
                    COALESCE(r.cf_year_2, 0) AS cf_year_2,
                    COALESCE(r.cf_year_3, 0) AS cf_year_3,
                    COALESCE(r.cf_year_4, 0) AS cf_year_4,
                    COALESCE(r.cf_year_5, 0) AS cf_year_5,
                    so.currency_id,
                    so.company_id
                FROM sale_order so
                JOIN res_partner rp ON rp.id = so.partner_id
                LEFT JOIN product_lines pl ON pl.order_id = so.id
                LEFT JOIN invoice_status inv ON inv.order_id = so.id
                LEFT JOIN recognition r ON r.order_id = so.id
                WHERE so.state = 'sale'
                  AND COALESCE(r.has_recognition, 0) = 1
            )
        """ % self._table)
