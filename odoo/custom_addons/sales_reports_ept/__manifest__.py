# -*- coding: utf-8 -*-
{
    'name': 'Sales Reports EPT',
    'version': '18.0.1.0.0',
    'category': 'Sales/Reports',
    'summary': 'Sales Analysis Budget vs Actual and Sales Recognition Reports',
    'description': """
        Sales Analysis & Sales Recognition Reporting Module
        
        Features:
        - Sales Analysis: Budget vs Actual Report
          * Budget entry management by Year, Salesperson, Country, Product Line
          * Comparison of Actual vs Budget sales
          * Year-over-year variance analysis
          * Country/Region-wise and Salesperson-wise reports
          * Intercompany sales tracking
        
        - Sales Recognition Report
          * Monthly revenue recognition tracking
          * Carry-forward recognition for future years
          * Based on Recognition Schedule in Sales Orders
        
        Both reports:
        - Accessible from Sales → Reports
        - Excel download format
        - Based on confirmed Sales Orders
        - All values calculated including taxes
    """,
    'author': 'Emipro Technologies Pvt Ltd',
    'website': 'https://www.emiprotechnologies.com',
    'depends': [
        'sale',
        'sales_team',
        'crm_extended_ept',
        'customer_management_ept',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sales_region_data.xml',
        'views/sales_budget_entry_views.xml',
        'views/sales_region_views.xml',
        'wizard/sales_analysis_report_wizard_views.xml',
        'wizard/sales_recognition_report_wizard_views.xml',
        'views/menu_items.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
