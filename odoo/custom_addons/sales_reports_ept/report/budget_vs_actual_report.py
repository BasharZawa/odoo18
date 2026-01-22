# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _


class BudgetVsActualReport(models.Model):
    """
    SQL View Report: Budget vs Actual Analysis
    
    Report structure:
    - LEFT SIDE: Groupable by Region or Salesperson (configurable in pivot)
    - HEADER: Yearly Budget, Actual, Variance + YTD measures
    
    Data Sources:
    - Budget: budget.analytic + budget.line (native Odoo Budget)
    - Actual: account.analytic.line (posted journal entries)
    - Dimensions: x_plan4 (Country), x_plan5 (Salesperson), x_plan6 (Product Line)
    - Region: sales.region (linked via country)
    """
    _name = 'budget.vs.actual.report'
    _description = 'Budget vs Actual Report'
    _auto = False
    _order = 'fiscal_year desc, region_name, salesperson_name'

    # ==================== GROUPING DIMENSIONS (Left Side) ====================
    
    # Region (from sales.region via country)
    region_id = fields.Many2one(
        'sales.region', 
        string='Region', 
        readonly=True,
        help='Sales Region (derived from Country)'
    )
    region_name = fields.Char(string='Region', readonly=True)
    
    # Salesperson (from x_plan5)
    salesperson_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Salesperson Account',
        readonly=True
    )
    salesperson_name = fields.Char(string='Salesperson', readonly=True)
    
    # Country (from x_plan4) 
    country_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Country Account',
        readonly=True
    )
    country_name = fields.Char(string='Country', readonly=True)
    
    # Product Line (from x_plan6)
    product_line_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Product Line Account',
        readonly=True
    )
    product_line_name = fields.Char(string='Product Line', readonly=True)

    # ==================== TIME DIMENSIONS ====================
    
    fiscal_year = fields.Char(string='Year', readonly=True)
    date_from = fields.Date(string='Start Date', readonly=True)
    date_to = fields.Date(string='End Date', readonly=True)
    
    # ==================== BUDGET REFERENCE ====================
    
    budget_analytic_id = fields.Many2one(
        'budget.analytic', 
        string='Budget', 
        readonly=True
    )
    budget_line_id = fields.Many2one(
        'budget.line', 
        string='Budget Line', 
        readonly=True
    )
    budget_name = fields.Char(string='Budget Name', readonly=True)
    budget_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Open'),
        ('revised', 'Revised'),
        ('done', 'Done'),
        ('canceled', 'Canceled')
    ], string='Status', readonly=True)
    budget_type = fields.Selection([
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
        ('both', 'Both'),
    ], string='Type', readonly=True)

    # ==================== MEASURES (Header Columns) ====================
    
    # Full Year Measures
    budget_amount = fields.Float(
        string='Budget', 
        readonly=True,
        aggregator='sum',
        help='Full year budget amount'
    )
    actual_amount = fields.Float(
        string='Actual', 
        readonly=True,
        aggregator='sum',
        help='Actual achieved amount (full period)'
    )
    variance = fields.Float(
        string='Variance', 
        readonly=True,
        aggregator='sum',
        help='Actual - Budget'
    )
    variance_pct = fields.Float(
        string='Variance %', 
        readonly=True,
        aggregator='avg',
        help='(Actual / Budget - 1) * 100'
    )
    
    # YTD (Year-to-Date) Measures
    ytd_budget = fields.Float(
        string='YTD Budget', 
        readonly=True,
        aggregator='sum',
        help='Pro-rated budget from start of year to today'
    )
    ytd_actual = fields.Float(
        string='YTD Actual', 
        readonly=True,
        aggregator='sum',
        help='Actual amount from start of year to today'
    )
    ytd_variance = fields.Float(
        string='YTD Variance', 
        readonly=True,
        aggregator='sum',
        help='YTD Actual - YTD Budget'
    )
    
    # Achievement
    achievement_pct = fields.Float(
        string='Achievement %', 
        readonly=True,
        aggregator='avg',
        help='(Actual / Budget) * 100'
    )
    
    # Company/Currency
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    def init(self):
        """Create SQL view for Budget vs Actual analysis"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                WITH 
                -- Get country to region mapping via sales_region_country_rel
                country_region_map AS (
                    SELECT 
                        rc.id AS country_id,
                        rc.name AS country_db_name,
                        sr.id AS region_id,
                        sr.name AS region_name
                    FROM res_country rc
                    LEFT JOIN sales_region_country_rel srcr ON srcr.country_id = rc.id
                    LEFT JOIN sales_region sr ON sr.id = srcr.region_id
                ),
                
                -- Get actual amounts from analytic lines within budget periods
                actual_amounts AS (
                    SELECT
                        bl.id AS budget_line_id,
                        -- Full period actual
                        SUM(
                            CASE 
                                WHEN ba.budget_type = 'expense' THEN -aal.amount
                                ELSE aal.amount
                            END
                        ) AS actual_amount,
                        -- YTD actual (from period start to today)
                        SUM(
                            CASE 
                                WHEN aal.date <= CURRENT_DATE THEN
                                    CASE 
                                        WHEN ba.budget_type = 'expense' THEN -aal.amount
                                        ELSE aal.amount
                                    END
                                ELSE 0
                            END
                        ) AS ytd_actual
                    FROM budget_line bl
                    JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
                    JOIN account_analytic_line aal ON (
                        aal.company_id = bl.company_id
                        AND aal.date >= bl.date_from
                        AND aal.date <= bl.date_to
                    )
                    WHERE ba.state IN ('confirmed', 'done')
                    GROUP BY bl.id
                ),
                
                -- Calculate YTD budget (pro-rated)
                ytd_budget_calc AS (
                    SELECT
                        bl.id AS budget_line_id,
                        CASE 
                            WHEN bl.date_from IS NULL OR bl.date_to IS NULL THEN 0
                            WHEN CURRENT_DATE < bl.date_from THEN 0
                            WHEN CURRENT_DATE > bl.date_to THEN bl.budget_amount
                            ELSE bl.budget_amount * 
                                 ((LEAST(CURRENT_DATE, bl.date_to) - bl.date_from + 1)::float /
                                  NULLIF((bl.date_to - bl.date_from + 1)::float, 0))
                        END AS ytd_budget
                    FROM budget_line bl
                )
                
                SELECT
                    bl.id AS id,
                    
                    -- Grouping Dimensions
                    crm.region_id,
                    crm.region_name,
                    bl.x_plan5_id AS salesperson_analytic_id,
                    sp.name AS salesperson_name,
                    bl.x_plan4_id AS country_analytic_id,
                    cty.name AS country_name,
                    bl.x_plan6_id AS product_line_analytic_id,
                    pl.name AS product_line_name,
                    
                    -- Time Dimensions
                    EXTRACT(YEAR FROM bl.date_from)::text AS fiscal_year,
                    bl.date_from,
                    bl.date_to,
                    
                    -- Budget Reference
                    bl.budget_analytic_id,
                    bl.id AS budget_line_id,
                    ba.name AS budget_name,
                    ba.state AS budget_state,
                    ba.budget_type,
                    
                    -- Full Year Measures
                    COALESCE(bl.budget_amount, 0)::float AS budget_amount,
                    COALESCE(aa.actual_amount, 0)::float AS actual_amount,
                    (COALESCE(aa.actual_amount, 0) - COALESCE(bl.budget_amount, 0))::float AS variance,
                    CASE 
                        WHEN COALESCE(bl.budget_amount, 0) = 0 THEN 0
                        ELSE ROUND(((COALESCE(aa.actual_amount, 0) / NULLIF(bl.budget_amount, 0)) - 1) * 100, 2)
                    END::float AS variance_pct,
                    
                    -- YTD Measures
                    COALESCE(yb.ytd_budget, 0)::float AS ytd_budget,
                    COALESCE(aa.ytd_actual, 0)::float AS ytd_actual,
                    (COALESCE(aa.ytd_actual, 0) - COALESCE(yb.ytd_budget, 0))::float AS ytd_variance,
                    
                    -- Achievement
                    CASE 
                        WHEN COALESCE(bl.budget_amount, 0) = 0 THEN 0
                        ELSE ROUND((COALESCE(aa.actual_amount, 0) / NULLIF(bl.budget_amount, 0) * 100), 2)
                    END::float AS achievement_pct,
                    
                    -- Company/Currency
                    bl.company_id,
                    rc.currency_id
                    
                FROM budget_line bl
                JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
                
                -- Dimension joins (analytic accounts)
                LEFT JOIN account_analytic_account cty ON cty.id = bl.x_plan4_id
                LEFT JOIN account_analytic_account sp ON sp.id = bl.x_plan5_id
                LEFT JOIN account_analytic_account pl ON pl.id = bl.x_plan6_id
                
                -- Country to Region mapping - match country name from analytic to res_country
                LEFT JOIN res_country rc_match ON rc_match.name::text ILIKE cty.name::text
                LEFT JOIN country_region_map crm ON crm.country_id = rc_match.id
                
                -- Actual amounts
                LEFT JOIN actual_amounts aa ON aa.budget_line_id = bl.id
                LEFT JOIN ytd_budget_calc yb ON yb.budget_line_id = bl.id
                
                -- Company currency
                LEFT JOIN res_company rc ON rc.id = bl.company_id
                
                WHERE ba.state IN ('confirmed', 'done')
            )
        """ % self._table
        
        self.env.cr.execute(query)

    def action_open_budget_entries(self):
        """Open analytic lines for this budget period"""
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Analytic Entries'),
            'res_model': 'account.analytic.line',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_group_by_date': 1},
        }

    def action_open_budget(self):
        """Open the source budget"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'budget.analytic',
            'view_mode': 'form',
            'res_id': self.budget_analytic_id.id,
        }
