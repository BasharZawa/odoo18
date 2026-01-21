# -*- coding: utf-8 -*-
{
    'name': 'Sales Reports EPT',
    'version': '18.0.1.2.0',
    'category': 'Sales/Reports',
    'summary': 'Actual vs Budget and Sales Recognition Reports with Interactive Pivot Views',
    'description': """
        Sales Reporting Module - Actual vs Budget & Sales Recognition
        ==============================================================
        
        This module provides two comprehensive sales reports:
        
        1. ACTUAL VS BUDGET REPORT
           - Compare actual sales against budget targets
           - Rows: Region → Country → Salesperson
           - Columns: Year, Product Line (Legacy Prod, CVM, SS, Media Ana, Services)
           - Measures: Actual Amount, Budget Amount, Budget Variance, Prior Year, YoY Variance
           - Intercompany sales tracking
           - Multi-year analysis
        
        2. SALES RECOGNITION REPORT
           - Monthly revenue recognition breakdown by order
           - Columns: Order No, Customer, Payment Status, End User, Sector, 
             Salesperson, Country, Class of Product, Order Date, Total
           - Monthly columns: Jan - Dec (current year)
           - Carry Forward columns: Future years with scheduled recognition
           - Shows only orders with recognition schedule entries
        
        Features:
        - Interactive Pivot/List/Graph Views
        - Budget Entry management
        - Sales Region master data
    """,
    'author': 'Emipro Technologies Pvt Ltd',
    'website': 'https://www.emiprotechnologies.com',
    'depends': [
        'sale',
        'sales_team',
        'account',
        'analytic',
        'account_budget',
        'crm_extended_ept',
        'customer_management_ept',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sales_region_data.xml',
        'data/analytic_plans.xml',
        'views/sales_budget_entry_views.xml',
        'views/sales_region_views.xml',
        'report/sales_analysis_report_views.xml',
        'report/customer_sales_report_views.xml',
        'views/menu_items.xml',
        'report/analytic_budget_performance_report.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
