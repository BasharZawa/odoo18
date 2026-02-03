# -*- coding: utf-8 -*-

import datetime
from lxml import etree

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
        """Create SQL view for Budget vs Actual analysis.
        
        Dynamically detects available analytic plan columns in budget_line table.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Detect which x_plan columns exist in budget_line table
        self.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'budget_line' 
            AND column_name LIKE 'x_plan%_id'
            ORDER BY column_name
        """)
        available_plan_cols = [row[0] for row in self.env.cr.fetchall()]
        
        # Map plan columns dynamically (use first 3 available, or NULL if not available)
        plan1_col = available_plan_cols[0] if len(available_plan_cols) > 0 else None
        plan2_col = available_plan_cols[1] if len(available_plan_cols) > 1 else None
        plan3_col = available_plan_cols[2] if len(available_plan_cols) > 2 else None
        
        # Build dynamic SELECT expressions
        plan1_select = f"bl.{plan1_col}" if plan1_col else "NULL::integer"
        plan2_select = f"bl.{plan2_col}" if plan2_col else "NULL::integer"
        plan3_select = f"bl.{plan3_col}" if plan3_col else "NULL::integer"
        
        # Build dynamic JOIN expressions
        plan1_join = f"LEFT JOIN account_analytic_account aa1 ON aa1.id = bl.{plan1_col}" if plan1_col else ""
        plan2_join = f"LEFT JOIN account_analytic_account aa2 ON aa2.id = bl.{plan2_col}" if plan2_col else ""
        plan3_join = f"LEFT JOIN account_analytic_account aa3 ON aa3.id = bl.{plan3_col}" if plan3_col else ""
        
        plan1_name = "aa1.name" if plan1_col else "NULL::varchar"
        plan2_name = "aa2.name" if plan2_col else "NULL::varchar"
        plan3_name = "aa3.name" if plan3_col else "NULL::varchar"
        
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
                    
                    -- Grouping Dimensions (dynamic based on available plans)
                    crm.region_id,
                    crm.region_name,
                    -- Plan 1 (usually Project)
                    {plan1_select} AS salesperson_analytic_id,
                    {plan1_name} AS salesperson_name,
                    -- Plan 2 (usually Departments)
                    {plan2_select} AS country_analytic_id,
                    {plan2_name} AS country_name,
                    -- Plan 3 (usually Internal)
                    {plan3_select} AS product_line_analytic_id,
                    {plan3_name} AS product_line_name,
                    
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
                    rcomp.currency_id
                    
                FROM budget_line bl
                JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
                
                -- Dimension joins (analytic accounts) - dynamic
                {plan1_join}
                {plan2_join}
                {plan3_join}
                
                -- Country to Region mapping - match first plan name to res_country
                LEFT JOIN res_country rc_match ON rc_match.name::text ILIKE {plan2_name}::text
                LEFT JOIN country_region_map crm ON crm.country_id = rc_match.id
                
                -- Actual amounts
                LEFT JOIN actual_amounts aa ON aa.budget_line_id = bl.id
                LEFT JOIN ytd_budget_calc yb ON yb.budget_line_id = bl.id
                
                -- Company currency
                LEFT JOIN res_company rcomp ON rcomp.id = bl.company_id
                
                WHERE ba.state IN ('confirmed', 'done')
            )
        """.format(
            plan1_select=plan1_select,
            plan2_select=plan2_select,
            plan3_select=plan3_select,
            plan1_name=plan1_name,
            plan2_name=plan2_name,
            plan3_name=plan3_name,
            plan1_join=plan1_join,
            plan2_join=plan2_join,
            plan3_join=plan3_join,
        )
        
        self.env.cr.execute(query % self._table)

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

    @api.model
    def get_available_years(self):
        """Get list of years that have budget data"""
        self.env.cr.execute("""
            SELECT DISTINCT EXTRACT(YEAR FROM bl.date_from)::int AS year
            FROM budget_line bl
            JOIN budget_analytic ba ON ba.id = bl.budget_analytic_id
            WHERE ba.state IN ('confirmed', 'done')
            ORDER BY year DESC
        """)
        years = [row[0] for row in self.env.cr.fetchall()]
        if not years:
            years = [datetime.date.today().year]
        return years

    def get_view(self, view_id=None, view_type='form', **options):
        """Override to dynamically inject year filters in search view."""
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        
        if view_type != 'search':
            return res
        
        arch = etree.fromstring(res['arch'])
        available_years = self.get_available_years()
        current_year = datetime.date.today().year
        
        # Ensure current year is included
        if current_year not in available_years:
            available_years.append(current_year)
        available_years = sorted(available_years, reverse=True)
        
        # Find and remove existing static year filters
        for filter_elem in arch.xpath("//filter[starts-with(@name, 'filter_year_')]"):
            filter_elem.getparent().remove(filter_elem)
        
        # Find the fiscal_year field to insert after
        fiscal_year_field = arch.find(".//field[@name='fiscal_year']")
        if fiscal_year_field is not None:
            parent = fiscal_year_field.getparent()
            
            # Find the separator after fiscal_year
            separators = arch.xpath("//field[@name='fiscal_year']/following-sibling::separator")
            if separators:
                insert_index = list(parent).index(separators[0]) + 1
            else:
                insert_index = list(parent).index(fiscal_year_field) + 1
            
            # Insert dynamic year filters
            for i, year in enumerate(available_years):
                filter_elem = etree.Element('filter')
                filter_elem.set('name', f'filter_year_{year}')
                filter_elem.set('string', str(year))
                filter_elem.set('domain', f"[('fiscal_year', '=', '{year}')]")
                parent.insert(insert_index + i, filter_elem)
        
        res['arch'] = etree.tostring(arch, encoding='unicode')
        return res

    @api.model
    def action_open_report(self):
        """Open the Budget vs Actual Report with current year filter active."""
        current_year = datetime.date.today().year
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget vs Actual'),
            'res_model': 'budget.vs.actual.report',
            'view_mode': 'pivot,list,graph',
            'context': {
                f'search_default_filter_year_{current_year}': 1,
                'search_default_filter_confirmed': 1,
            },
        }
