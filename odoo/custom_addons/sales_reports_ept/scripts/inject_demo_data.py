#!/usr/bin/env python3
"""
Demo Data Injection Script for Sales Reports

Run this script after installing the sales_reports_ept module to create:
- Demo Sale Orders
- Recognition Schedules

Usage:
    python3 inject_demo_data.py

Requires: xmlrpc connection to running Odoo server
"""

import xmlrpc.client
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Connection settings - UPDATE THESE
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'OdooE'  # Your database name
ODOO_USER = 'admin'
ODOO_PASSWORD = 'admin'  # Your admin password

def get_connection():
    """Establish connection to Odoo"""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Authentication failed!")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

def search_read(models, uid, model, domain, fields):
    """Helper to search and read"""
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, 'search_read', [domain], {'fields': fields})

def create_record(models, uid, model, vals):
    """Helper to create record"""
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, 'create', [vals])

def write_record(models, uid, model, ids, vals):
    """Helper to write record"""
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, 'write', [ids, vals])

def main():
    print("=" * 60)
    print("SALES REPORTS - DEMO DATA INJECTION")
    print("=" * 60)
    
    uid, models = get_connection()
    print(f"✓ Connected to {ODOO_URL} as user ID {uid}")
    
    # Get required reference data
    print("\n1. Fetching reference data...")
    
    # Get admin user
    admin_user = search_read(models, uid, 'res.users', [('login', '=', 'admin')], ['id', 'partner_id'])
    admin_id = admin_user[0]['id'] if admin_user else 1
    print(f"   Admin user ID: {admin_id}")
    
    # Get or create product lines
    print("\n2. Creating/Finding Product Lines...")
    product_lines = {}
    line_names = ['Legacy Products', 'CVM', 'Self Service', 'Media Analytics', 'Services']
    
    for name in line_names:
        existing = search_read(models, uid, 'product.line.ept', [('name', '=', name)], ['id'])
        if existing:
            product_lines[name] = existing[0]['id']
        else:
            product_lines[name] = create_record(models, uid, 'product.line.ept', {'name': name})
        print(f"   {name}: ID {product_lines[name]}")
    
    # Get countries
    print("\n3. Fetching countries...")
    countries = {}
    for code in ['AE', 'SA', 'JO', 'QA', 'KW', 'EG']:
        country = search_read(models, uid, 'res.country', [('code', '=', code)], ['id', 'name'])
        if country:
            countries[code] = {'id': country[0]['id'], 'name': country[0]['name']}
            print(f"   {code}: {country[0]['name']}")
    
    # Get or create industries
    print("\n4. Creating/Finding Industries...")
    industries = {}
    industry_names = ['Banking & Finance', 'Healthcare', 'Telecommunications', 'Government']
    
    for name in industry_names:
        existing = search_read(models, uid, 'res.partner.industry', [('name', '=', name)], ['id'])
        if existing:
            industries[name] = existing[0]['id']
        else:
            industries[name] = create_record(models, uid, 'res.partner.industry', {'name': name})
        print(f"   {name}: ID {industries[name]}")
    
    # Create demo customers
    print("\n5. Creating demo customers...")
    customers = []
    customer_data = [
        {'name': 'Emirates National Bank', 'country': 'AE', 'industry': 'Banking & Finance'},
        {'name': 'Dubai Health Authority', 'country': 'AE', 'industry': 'Healthcare'},
        {'name': 'Saudi Telecom Company', 'country': 'SA', 'industry': 'Telecommunications'},
        {'name': 'Ministry of Interior KSA', 'country': 'SA', 'industry': 'Government'},
        {'name': 'Jordan Islamic Bank', 'country': 'JO', 'industry': 'Banking & Finance'},
        {'name': 'Qatar National Bank', 'country': 'QA', 'industry': 'Banking & Finance'},
        {'name': 'Kuwait Finance House', 'country': 'KW', 'industry': 'Banking & Finance'},
    ]
    
    for cust in customer_data:
        existing = search_read(models, uid, 'res.partner', [('name', '=', cust['name'])], ['id'])
        if existing:
            cust_id = existing[0]['id']
        else:
            cust_id = create_record(models, uid, 'res.partner', {
                'name': cust['name'],
                'company_type': 'company',
                'country_id': countries[cust['country']]['id'],
                'industry_id': industries[cust['industry']],
                'customer_rank': 1,
            })
        customers.append({'id': cust_id, **cust})
        print(f"   {cust['name']}: ID {cust_id}")
    
    # Create demo products
    print("\n6. Creating demo products...")
    products = {}
    product_data = [
        {'name': 'Queue Management System', 'price': 15000, 'line': 'Legacy Products'},
        {'name': 'Customer Voice Module', 'price': 25000, 'line': 'CVM'},
        {'name': 'Self Service Kiosk', 'price': 35000, 'line': 'Self Service'},
        {'name': 'Digital Signage Analytics', 'price': 20000, 'line': 'Media Analytics'},
        {'name': 'Implementation Services', 'price': 10000, 'line': 'Services'},
        {'name': 'Annual Support Package', 'price': 5000, 'line': 'Services'},
    ]
    
    for prod in product_data:
        existing = search_read(models, uid, 'product.product', [('name', '=', prod['name'])], ['id'])
        if existing:
            prod_id = existing[0]['id']
        else:
            tmpl_id = create_record(models, uid, 'product.template', {
                'name': prod['name'],
                'type': 'service' if 'Services' in prod['line'] else 'consu',
                'list_price': prod['price'],
                'product_line_id': product_lines[prod['line']],
                'sale_ok': True,
            })
            prod_rec = search_read(models, uid, 'product.product', [('product_tmpl_id', '=', tmpl_id)], ['id'])
            prod_id = prod_rec[0]['id']
        products[prod['name']] = prod_id
        print(f"   {prod['name']}: ID {prod_id}")
    
    # Create Budget Entries
    print("\n7. Creating budget entries...")
    
    budget_data = [
        # 2024 budgets (for previous year comparison)
        {'year': '2024', 'country': 'AE', 'line': 'Legacy Products', 'amount': 120000},
        {'year': '2024', 'country': 'AE', 'line': 'CVM', 'amount': 150000},
        {'year': '2024', 'country': 'SA', 'line': 'Legacy Products', 'amount': 250000},
        {'year': '2024', 'country': 'SA', 'line': 'Self Service', 'amount': 200000},
        {'year': '2024', 'country': 'JO', 'line': 'Legacy Products', 'amount': 80000},
        
        # 2025 budgets
        {'year': '2025', 'country': 'AE', 'line': 'Legacy Products', 'amount': 150000},
        {'year': '2025', 'country': 'AE', 'line': 'CVM', 'amount': 200000},
        {'year': '2025', 'country': 'AE', 'line': 'Services', 'amount': 80000},
        {'year': '2025', 'country': 'SA', 'line': 'Legacy Products', 'amount': 300000},
        {'year': '2025', 'country': 'SA', 'line': 'Self Service', 'amount': 250000},
        {'year': '2025', 'country': 'SA', 'line': 'Services', 'amount': 100000},
        {'year': '2025', 'country': 'JO', 'line': 'Legacy Products', 'amount': 100000},
        {'year': '2025', 'country': 'QA', 'line': 'Legacy Products', 'amount': 120000},
        {'year': '2025', 'country': 'KW', 'line': 'CVM', 'amount': 90000},
        
        # 2026 budgets
        {'year': '2026', 'country': 'AE', 'line': 'Legacy Products', 'amount': 180000},
        {'year': '2026', 'country': 'AE', 'line': 'CVM', 'amount': 220000},
        {'year': '2026', 'country': 'SA', 'line': 'Legacy Products', 'amount': 350000},
        {'year': '2026', 'country': 'SA', 'line': 'Self Service', 'amount': 280000},
    ]
    
    for budget in budget_data:
        if budget['country'] not in countries:
            continue
        existing = search_read(models, uid, 'sales.budget.entry', [
            ('year', '=', budget['year']),
            ('country_id', '=', countries[budget['country']]['id']),
            ('product_line_id', '=', product_lines[budget['line']]),
            ('salesperson_id', '=', admin_id),
        ], ['id'])
        
        if not existing:
            create_record(models, uid, 'sales.budget.entry', {
                'year': budget['year'],
                'salesperson_id': admin_id,
                'country_id': countries[budget['country']]['id'],
                'product_line_id': product_lines[budget['line']],
                'budget_amount': budget['amount'],
            })
            print(f"   ✓ Created: {budget['year']} - {budget['country']} - {budget['line']}: ${budget['amount']:,.0f}")
        else:
            print(f"   - Exists: {budget['year']} - {budget['country']} - {budget['line']}")
    
    # Create Sale Orders
    print("\n8. Creating sale orders...")
    
    sale_orders_data = [
        # 2024 Orders (for previous year comparison)
        {
            'customer': 'Emirates National Bank',
            'date': '2024-03-15',
            'lines': [
                {'product': 'Queue Management System', 'qty': 5, 'price': 15000},
                {'product': 'Implementation Services', 'qty': 1, 'price': 20000},
            ],
            'recognition': [
                {'date': '2024-03-15', 'amount': 47500},
                {'date': '2024-06-15', 'amount': 47500},
            ]
        },
        {
            'customer': 'Saudi Telecom Company',
            'date': '2024-06-01',
            'lines': [
                {'product': 'Self Service Kiosk', 'qty': 10, 'price': 35000},
            ],
            'recognition': [
                {'date': '2024-06-01', 'amount': 175000},
                {'date': '2024-09-01', 'amount': 175000},
            ]
        },
        
        # 2025 Orders
        {
            'customer': 'Emirates National Bank',
            'date': '2025-01-15',
            'lines': [
                {'product': 'Customer Voice Module', 'qty': 3, 'price': 25000},
                {'product': 'Annual Support Package', 'qty': 3, 'price': 5000},
            ],
            'recognition': [
                {'date': '2025-01-15', 'amount': 30000},
                {'date': '2025-04-15', 'amount': 30000},
                {'date': '2025-07-15', 'amount': 30000},
            ]
        },
        {
            'customer': 'Dubai Health Authority',
            'date': '2025-02-01',
            'lines': [
                {'product': 'Queue Management System', 'qty': 8, 'price': 15000},
                {'product': 'Digital Signage Analytics', 'qty': 5, 'price': 20000},
            ],
            'recognition': [
                {'date': '2025-02-01', 'amount': 110000},
                {'date': '2025-05-01', 'amount': 110000},
            ]
        },
        {
            'customer': 'Saudi Telecom Company',
            'date': '2025-03-01',
            'lines': [
                {'product': 'Self Service Kiosk', 'qty': 15, 'price': 35000},
                {'product': 'Implementation Services', 'qty': 1, 'price': 50000},
            ],
            'recognition': [
                {'date': '2025-03-01', 'amount': 145000},
                {'date': '2025-06-01', 'amount': 145000},
                {'date': '2025-09-01', 'amount': 145000},
                {'date': '2025-12-01', 'amount': 140000},
            ]
        },
        {
            'customer': 'Ministry of Interior KSA',
            'date': '2025-04-15',
            'lines': [
                {'product': 'Queue Management System', 'qty': 20, 'price': 15000},
                {'product': 'Customer Voice Module', 'qty': 10, 'price': 25000},
            ],
            'recognition': [
                {'date': '2025-04-15', 'amount': 137500},
                {'date': '2025-07-15', 'amount': 137500},
                {'date': '2025-10-15', 'amount': 137500},
                {'date': '2026-01-15', 'amount': 137500},  # Carry forward to 2026
            ]
        },
        {
            'customer': 'Jordan Islamic Bank',
            'date': '2025-05-01',
            'lines': [
                {'product': 'Queue Management System', 'qty': 4, 'price': 15000},
                {'product': 'Annual Support Package', 'qty': 4, 'price': 5000},
            ],
            'recognition': [
                {'date': '2025-05-01', 'amount': 40000},
                {'date': '2025-11-01', 'amount': 40000},
            ]
        },
        {
            'customer': 'Qatar National Bank',
            'date': '2025-06-15',
            'lines': [
                {'product': 'Queue Management System', 'qty': 6, 'price': 15000},
                {'product': 'Implementation Services', 'qty': 1, 'price': 15000},
            ],
            'recognition': [
                {'date': '2025-06-15', 'amount': 52500},
                {'date': '2025-09-15', 'amount': 52500},
            ]
        },
        {
            'customer': 'Kuwait Finance House',
            'date': '2025-07-01',
            'lines': [
                {'product': 'Customer Voice Module', 'qty': 4, 'price': 25000},
            ],
            'recognition': [
                {'date': '2025-07-01', 'amount': 50000},
                {'date': '2025-10-01', 'amount': 50000},
            ]
        },
        
        # Multi-year recognition order
        {
            'customer': 'Saudi Telecom Company',
            'date': '2025-09-01',
            'lines': [
                {'product': 'Self Service Kiosk', 'qty': 30, 'price': 35000},
                {'product': 'Annual Support Package', 'qty': 30, 'price': 8000},  # 3-year support
            ],
            'recognition': [
                {'date': '2025-09-01', 'amount': 390000},
                {'date': '2025-12-01', 'amount': 390000},
                {'date': '2026-03-01', 'amount': 130000},  # C/F 2026
                {'date': '2026-06-01', 'amount': 130000},  # C/F 2026
                {'date': '2026-09-01', 'amount': 130000},  # C/F 2026
                {'date': '2027-01-01', 'amount': 65000},   # C/F 2027
                {'date': '2027-06-01', 'amount': 65000},   # C/F 2027
            ]
        },
    ]
    
    for so_data in sale_orders_data:
        # Find customer
        customer = search_read(models, uid, 'res.partner', [('name', '=', so_data['customer'])], ['id'])
        if not customer:
            print(f"   ✗ Customer not found: {so_data['customer']}")
            continue
        customer_id = customer[0]['id']
        
        # Check if order already exists
        existing = search_read(models, uid, 'sale.order', [
            ('partner_id', '=', customer_id),
            ('date_order', '=', so_data['date']),
        ], ['id'])
        
        if existing:
            print(f"   - Order exists for {so_data['customer']} on {so_data['date']}")
            continue
        
        # Create order lines
        order_lines = []
        for line in so_data['lines']:
            order_lines.append((0, 0, {
                'product_id': products[line['product']],
                'product_uom_qty': line['qty'],
                'price_unit': line['price'],
            }))
        
        # Create sale order
        so_id = create_record(models, uid, 'sale.order', {
            'partner_id': customer_id,
            'date_order': so_data['date'],
            'order_line': order_lines,
            'user_id': admin_id,
        })
        print(f"   ✓ Created SO#{so_id}: {so_data['customer']} - {so_data['date']}")
        
        # Confirm the order
        try:
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'sale.order', 'action_confirm', [[so_id]])
            print(f"      ✓ Confirmed")
        except Exception as e:
            print(f"      ! Could not confirm: {e}")
        
        # Create recognition schedule
        if so_data.get('recognition'):
            for rec in so_data['recognition']:
                try:
                    create_record(models, uid, 'sale.order.recognition.schedule', {
                        'sale_order_id': so_id,
                        'recognition_date': rec['date'],
                        'amount': rec['amount'],
                        'description': f"Recognition for {so_data['customer']}",
                    })
                except Exception as e:
                    print(f"      ! Recognition schedule error: {e}")
            print(f"      ✓ Added {len(so_data['recognition'])} recognition entries")
    
    print("\n" + "=" * 60)
    print("DEMO DATA INJECTION COMPLETE!")
    print("=" * 60)
    print("\nYou can now test the reports:")
    print("  1. Go to Sales → Reports → Sales Analysis Wizard")
    print("     - Select Year: 2025")
    print("     - Select Report Type: By Country/Region or By Salesperson")
    print("     - Click Generate Report")
    print("")
    print("  2. Go to Sales → Reports → Sales Recognition Report")
    print("     - Select Year: 2025")
    print("     - Click Generate Report")
    print("")
    print("Expected data summary:")
    print("  - 7 Customers across UAE, Saudi, Jordan, Qatar, Kuwait")
    print("  - 6 Products across 5 Product Lines")
    print("  - Budget entries for 2024, 2025, 2026")
    print("  - ~10 Sale Orders with recognition schedules")
    print("  - Multi-year recognition extending to 2026, 2027")

if __name__ == '__main__':
    main()
