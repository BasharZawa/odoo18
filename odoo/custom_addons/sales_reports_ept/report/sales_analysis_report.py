# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api


class SalesAnalysisReport(models.Model):
    """
    SQL View Report: Sales Analysis - Budget vs Actual by Region/Salesperson
    
    Matches the Excel wizard logic:
    - Actual sales by product line (from sale.order.line via product_line_id)
    - Budget amounts by product line
    - Variance (Actual - Budget)
    - Prior year actual sales
    - Year-over-Year variance
    - Intercompany sales tracking
    
    Grouped by: Year → Region → Country → Salesperson → Product Line
    Filter by Year and Company in the UI.
    """
    _name = 'sales.analysis.report'
    _description = 'Sales Analysis Report - Budget vs Actual'
    _auto = False
    _order = 'year desc, analytic_country_account_id, analytic_salesperson_account_id, analytic_product_line_account_id, region_id, country_id, salesperson_id, product_line_id'

    # Dimensions
    year = fields.Char(string='Year', readonly=True)
    analytic_country_account_id = fields.Many2one('account.analytic.account', string='Analytic Country', readonly=True)
    analytic_salesperson_account_id = fields.Many2one('account.analytic.account', string='Analytic Salesperson', readonly=True)
    analytic_product_line_account_id = fields.Many2one('account.analytic.account', string='Analytic Product Line', readonly=True)
    region_id = fields.Many2one('sales.region', string='Region', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    product_line_id = fields.Many2one('product.line.ept', string='Product Line', readonly=True)
    is_intercompany = fields.Boolean(string='Intercompany', readonly=True)
    
    # Current Year Actual
    actual_amount = fields.Float(string='Actual', readonly=True, aggregator='sum')
    
    # Budget
    budget_amount = fields.Float(string='Budget', readonly=True, aggregator='sum')
    
    # Budget Variance (Actual - Budget)
    budget_variance = fields.Float(string='Budget Variance', readonly=True, aggregator='sum')
    budget_variance_pct = fields.Float(string='Budget Var %', readonly=True, aggregator='avg')
    
    # Prior Year Actual
    prior_actual = fields.Float(string='Prior Year Actual', readonly=True, aggregator='sum')
    
    # YoY Variance (Current - Prior)
    yoy_variance = fields.Float(string='YoY Variance', readonly=True, aggregator='sum')
    yoy_variance_pct = fields.Float(string='YoY Var %', readonly=True, aggregator='avg')
    
    # Company/Currency
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Create the SQL view for Sales Analysis Report - matches Excel wizard logic"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH 
                -- Actual sales (sales-mode) by year, salesperson, country, product line
                -- Product line comes from sale_order_line.product_line_id (related field)
                sales_actual AS (
                    SELECT 
                        EXTRACT(YEAR FROM so.date_order)::text AS yr,
                        NULL::integer AS analytic_country_account_id,
                        NULL::integer AS analytic_salesperson_account_id,
                        NULL::integer AS analytic_product_line_account_id,
                        so.user_id AS salesperson_id,
                        rp.country_id AS country_id,
                        sol.product_line_id AS product_line_id,
                        so.company_id,
                        so.currency_id,
                        -- Check if intercompany: partner has a company_id different from order company
                        CASE WHEN rp.company_id IS NOT NULL AND rp.company_id != so.company_id 
                             THEN true ELSE false END AS is_intercompany,
                        SUM(sol.price_subtotal) AS actual_amount
                    FROM sale_order so
                    JOIN sale_order_line sol ON sol.order_id = so.id
                    JOIN res_partner rp ON rp.id = so.partner_id
                    WHERE so.state = 'sale'
                      AND sol.product_line_id IS NOT NULL
                    GROUP BY 
                        EXTRACT(YEAR FROM so.date_order)::text,
                        NULL::integer,
                        NULL::integer,
                        NULL::integer,
                        so.user_id, 
                        rp.country_id, 
                        sol.product_line_id, 
                        so.company_id, 
                        so.currency_id,
                        CASE WHEN rp.company_id IS NOT NULL AND rp.company_id != so.company_id 
                             THEN true ELSE false END
                ),
                -- Prior year actual sales (sales-mode) (for YoY comparison)
                sales_prior AS (
                    SELECT 
                        (EXTRACT(YEAR FROM so.date_order) + 1)::text AS yr,  -- Maps to NEXT year for comparison
                        NULL::integer AS analytic_country_account_id,
                        NULL::integer AS analytic_salesperson_account_id,
                        NULL::integer AS analytic_product_line_account_id,
                        so.user_id AS salesperson_id,
                        rp.country_id AS country_id,
                        sol.product_line_id AS product_line_id,
                        CASE WHEN rp.company_id IS NOT NULL AND rp.company_id != so.company_id 
                             THEN true ELSE false END AS is_intercompany,
                        SUM(sol.price_subtotal) AS prior_amount
                    FROM sale_order so
                    JOIN sale_order_line sol ON sol.order_id = so.id
                    JOIN res_partner rp ON rp.id = so.partner_id
                    WHERE so.state = 'sale'
                      AND sol.product_line_id IS NOT NULL
                    GROUP BY 
                        (EXTRACT(YEAR FROM so.date_order) + 1)::text,
                        NULL::integer,
                        NULL::integer,
                        NULL::integer,
                        so.user_id, 
                        rp.country_id, 
                        sol.product_line_id,
                        CASE WHEN rp.company_id IS NOT NULL AND rp.company_id != so.company_id 
                             THEN true ELSE false END
                ),
                -- Analytic Plans used by this module (fetched once per view query)
                plans AS (
                    SELECT
                        (SELECT res_id FROM ir_model_data WHERE module = 'sales_reports_ept' AND name = 'analytic_plan_country' LIMIT 1) AS country_plan_id,
                        (SELECT res_id FROM ir_model_data WHERE module = 'sales_reports_ept' AND name = 'analytic_plan_salesperson' LIMIT 1) AS salesperson_plan_id,
                        (SELECT res_id FROM ir_model_data WHERE module = 'sales_reports_ept' AND name = 'analytic_plan_product_line' LIMIT 1) AS product_line_plan_id
                ),

                -- Base analytic distribution lines on posted customer invoices.
                analytic_dist_lines AS (
                    SELECT
                        EXTRACT(YEAR FROM COALESCE(am.invoice_date, am.date))::text AS yr,
                        am.company_id,
                        am.currency_id,
                        j.key AS analytic_key,
                        (j.value)::numeric AS percentage,
                        (aml.price_subtotal * (j.value)::numeric / 100.0) AS amount_part
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS j(key, value) ON TRUE
                    WHERE am.state = 'posted'
                      AND am.move_type IN ('out_invoice', 'out_refund')
                      AND aml.display_type IS NULL
                      AND aml.tax_line_id IS NULL
                      AND aml.analytic_distribution IS NOT NULL
                ),

                -- Extract the 3 analytic dimensions (country/salesperson/product line) from each analytic_key.
                analytic_key_dims AS (
                    SELECT
                        k.analytic_key,
                        MAX(CASE WHEN aaa.root_plan_id = p.country_plan_id THEN aaa.id END) AS analytic_country_account_id,
                        MAX(CASE WHEN aaa.root_plan_id = p.salesperson_plan_id THEN aaa.id END) AS analytic_salesperson_account_id,
                        MAX(CASE WHEN aaa.root_plan_id = p.product_line_plan_id THEN aaa.id END) AS analytic_product_line_account_id
                    FROM (SELECT DISTINCT analytic_key FROM analytic_dist_lines) k
                    CROSS JOIN plans p
                    JOIN LATERAL unnest(regexp_split_to_array(k.analytic_key, '\\D+')) AS aid_txt ON aid_txt != ''
                    JOIN account_analytic_account aaa ON aaa.id = aid_txt::integer
                    GROUP BY k.analytic_key
                ),

                -- Actual sales (analytic-mode): group by year + (3 analytic dimensions)
                analytic_actual AS (
                    SELECT
                        l.yr,
                        d.analytic_country_account_id,
                        d.analytic_salesperson_account_id,
                        d.analytic_product_line_account_id,
                        NULL::integer AS salesperson_id,
                        NULL::integer AS country_id,
                        NULL::integer AS product_line_id,
                        l.company_id,
                        l.currency_id,
                        false AS is_intercompany,
                        SUM(l.amount_part) AS actual_amount
                    FROM analytic_dist_lines l
                    JOIN analytic_key_dims d ON d.analytic_key = l.analytic_key
                    GROUP BY
                        l.yr,
                        d.analytic_country_account_id,
                        d.analytic_salesperson_account_id,
                        d.analytic_product_line_account_id,
                        l.company_id,
                        l.currency_id
                ),

                -- Prior year actual sales (analytic-mode)
                analytic_prior AS (
                    SELECT
                        (l.yr::integer + 1)::text AS yr,
                        d.analytic_country_account_id,
                        d.analytic_salesperson_account_id,
                        d.analytic_product_line_account_id,
                        false AS is_intercompany,
                        SUM(l.amount_part) AS prior_amount
                    FROM analytic_dist_lines l
                    JOIN analytic_key_dims d ON d.analytic_key = l.analytic_key
                    GROUP BY
                        (l.yr::integer + 1)::text,
                        d.analytic_country_account_id,
                        d.analytic_salesperson_account_id,
                        d.analytic_product_line_account_id,
                        false
                ),
                -- Budget entries by year (supports both sales-mode and analytic-mode)
                budget AS (
                    SELECT 
                        year AS yr,
                        analytic_country_account_id,
                        analytic_salesperson_account_id,
                        analytic_product_line_account_id,
                        salesperson_id,
                        country_id,
                        product_line_id,
                        budget_amount,
                        company_id,
                        currency_id
                    FROM sales_budget_entry
                ),
                -- Map countries to regions
                country_region AS (
                    SELECT 
                        srcr.country_id,
                        srcr.region_id
                    FROM sales_region_country_rel srcr
                ),
                -- Combined data: sales-mode
                combined_sales AS (
                    SELECT
                        COALESCE(a.yr, b.yr, p.yr) AS yr,
                        NULL::integer AS analytic_country_account_id,
                        NULL::integer AS analytic_salesperson_account_id,
                        NULL::integer AS analytic_product_line_account_id,
                        COALESCE(a.salesperson_id, b.salesperson_id, p.salesperson_id) AS salesperson_id,
                        COALESCE(a.country_id, b.country_id, p.country_id) AS country_id,
                        COALESCE(a.product_line_id, b.product_line_id, p.product_line_id) AS product_line_id,
                        COALESCE(a.is_intercompany, p.is_intercompany, false) AS is_intercompany,
                        COALESCE(a.company_id, b.company_id) AS company_id,
                        COALESCE(a.currency_id, b.currency_id) AS currency_id,
                        COALESCE(a.actual_amount, 0) AS actual_amount,
                        COALESCE(b.budget_amount, 0) AS budget_amount,
                        COALESCE(p.prior_amount, 0) AS prior_actual
                    FROM sales_actual a
                    FULL OUTER JOIN budget b
                        ON a.yr = b.yr
                        AND b.analytic_country_account_id IS NULL
                        AND b.analytic_salesperson_account_id IS NULL
                        AND b.analytic_product_line_account_id IS NULL
                        AND a.salesperson_id = b.salesperson_id
                        AND a.country_id = b.country_id
                        AND a.product_line_id = b.product_line_id
                        AND a.is_intercompany = false
                    FULL OUTER JOIN sales_prior p
                        ON COALESCE(a.yr, b.yr) = p.yr
                        AND COALESCE(a.salesperson_id, b.salesperson_id) = p.salesperson_id
                        AND COALESCE(a.country_id, b.country_id) = p.country_id
                        AND COALESCE(a.product_line_id, b.product_line_id) = p.product_line_id
                        AND COALESCE(a.is_intercompany, false) = p.is_intercompany
                    WHERE COALESCE(a.yr, b.yr, p.yr) IS NOT NULL
                ),
                -- Combined data: analytic-mode
                combined_analytic AS (
                    SELECT
                        COALESCE(a.yr, b.yr, p.yr) AS yr,
                        COALESCE(a.analytic_country_account_id, b.analytic_country_account_id, p.analytic_country_account_id) AS analytic_country_account_id,
                        COALESCE(a.analytic_salesperson_account_id, b.analytic_salesperson_account_id, p.analytic_salesperson_account_id) AS analytic_salesperson_account_id,
                        COALESCE(a.analytic_product_line_account_id, b.analytic_product_line_account_id, p.analytic_product_line_account_id) AS analytic_product_line_account_id,
                        NULL::integer AS salesperson_id,
                        NULL::integer AS country_id,
                        NULL::integer AS product_line_id,
                        false AS is_intercompany,
                        COALESCE(a.company_id, b.company_id) AS company_id,
                        COALESCE(a.currency_id, b.currency_id) AS currency_id,
                        COALESCE(a.actual_amount, 0) AS actual_amount,
                        COALESCE(b.budget_amount, 0) AS budget_amount,
                        COALESCE(p.prior_amount, 0) AS prior_actual
                    FROM analytic_actual a
                    FULL OUTER JOIN budget b
                        ON a.yr = b.yr
                        AND a.analytic_country_account_id = b.analytic_country_account_id
                        AND a.analytic_salesperson_account_id = b.analytic_salesperson_account_id
                        AND a.analytic_product_line_account_id = b.analytic_product_line_account_id
                    FULL OUTER JOIN analytic_prior p
                        ON COALESCE(a.yr, b.yr) = p.yr
                        AND COALESCE(a.analytic_country_account_id, b.analytic_country_account_id) = p.analytic_country_account_id
                        AND COALESCE(a.analytic_salesperson_account_id, b.analytic_salesperson_account_id) = p.analytic_salesperson_account_id
                        AND COALESCE(a.analytic_product_line_account_id, b.analytic_product_line_account_id) = p.analytic_product_line_account_id
                    WHERE COALESCE(a.yr, b.yr, p.yr) IS NOT NULL
                ),
                combined AS (
                    SELECT * FROM combined_sales
                    UNION ALL
                    SELECT * FROM combined_analytic
                )
                SELECT 
                    ROW_NUMBER() OVER () AS id,
                    c.yr AS year,
                    c.analytic_country_account_id,
                    c.analytic_salesperson_account_id,
                    c.analytic_product_line_account_id,
                    cr.region_id,
                    c.country_id,
                    c.salesperson_id,
                    c.product_line_id,
                    c.is_intercompany,
                    c.actual_amount,
                    c.budget_amount,
                    (c.actual_amount - c.budget_amount) AS budget_variance,
                    CASE 
                        WHEN c.budget_amount != 0 
                        THEN ROUND(((c.actual_amount - c.budget_amount) / c.budget_amount * 100)::numeric, 2)
                        ELSE 0 
                    END AS budget_variance_pct,
                    c.prior_actual,
                    (c.actual_amount - c.prior_actual) AS yoy_variance,
                    CASE 
                        WHEN c.prior_actual != 0 
                        THEN ROUND(((c.actual_amount - c.prior_actual) / c.prior_actual * 100)::numeric, 2)
                        ELSE 0 
                    END AS yoy_variance_pct,
                    c.currency_id,
                    c.company_id
                FROM combined c
                LEFT JOIN country_region cr ON cr.country_id = c.country_id
                WHERE c.actual_amount != 0 OR c.budget_amount != 0 OR c.prior_actual != 0
            )
        """ % self._table)
