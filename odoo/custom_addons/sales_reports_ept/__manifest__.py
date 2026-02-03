# -*- coding: utf-8 -*-
{
    'name': 'Sales Reports EPT',
    'version': '18.0.3.0.0',
    'category': 'Sales/Reports',
    'summary': 'Budget vs Actual (Native Integration) & Sales Recognition Reports',
    'description': """
        Sales Reporting Module - Budget vs Actual & Sales Recognition
        ==============================================================
        
        This module provides two comprehensive sales reports fully integrated
        with Odoo 18 Enterprise native modules.
        
        1. BUDGET VS ACTUAL REPORT
           - Integrates with native account_budget module (budget.analytic / budget.line)
           - Actual data from account.analytic.line (posted invoices)
           - Supports all analytic plans dynamically
           - Measures: Budget, Achieved, Committed, Variance, Achievement %
           - Multi-year and multi-company support
        
        2. SALES RECOGNITION REPORT
           - Revenue recognition by sales order
           - Monthly breakdown (Jan-Dec) for selected year
           - Carry Forward columns for future years
           - Payment status, End User, Sector tracking
           - Recognition coverage and status indicators
        
        Features:
        - Native Odoo Budget Integration (budget.analytic / budget.line / budget.report)
        - Interactive Pivot/List/Graph Views
        - Sales Region master data
        - Multi-currency support with company currency conversion
    """,
    'author': 'Emipro Technologies Pvt Ltd',
    'website': 'https://www.emiprotechnologies.com',
    'depends': [
        'sale',
        'sales_team',
        'account',
        'analytic',
        'account_budget',  # Enterprise module - native budget
        'crm_extended_ept',
        'customer_management_ept',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sales_region_views.xml',
        'report/budget_vs_actual_report_views.xml',
        'report/sales_recognition_report_views.xml',
        'report/sales_recognition_report_v2_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OEEL-1',  # Enterprise license since it depends on account_budget
}
