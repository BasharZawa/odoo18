#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo Data Injection Script for Sales Reports
Runs via odoo-bin shell command
"""

from datetime import date, timedelta
import random

def inject_demo_data(env):
    """Inject demo data for testing Sales Reports"""
    print("=" * 60)
    print("SALES REPORTS - DEMO DATA INJECTION")
    print("=" * 60)
    
    # Get admin user
    admin_user = env['res.users'].search([('login', '=', 'admin')], limit=1)
    if not admin_user:
        admin_user = env.user
    print(f"✓ Admin user: {admin_user.name} (ID: {admin_user.id})")
    
    # 1. Create/Find Product Lines
    print("\n1. Creating/Finding Product Lines...")
    ProductLine = env['product.line.ept']
    product_lines = {}
    line_names = ['Legacy Products', 'CVM', 'Self Service', 'Media Analytics', 'Services']
    
    for name in line_names:
        pl = ProductLine.search([('name', '=', name)], limit=1)
        if not pl:
            pl = ProductLine.create({'name': name})
        product_lines[name] = pl
        print(f"   {name}: ID {pl.id}")
    
    # 2. Get Countries
    print("\n2. Fetching countries...")
    Country = env['res.country']
    countries = {}
    for code in ['AE', 'SA', 'JO', 'QA', 'KW', 'EG']:
        country = Country.search([('code', '=', code)], limit=1)
        if country:
            countries[code] = country
            print(f"   {code}: {country.name}")
    
    # 3. Create/Find Industries
    print("\n3. Creating/Finding Industries...")
    Industry = env['res.partner.industry']
    industries = {}
    industry_names = ['Banking & Finance', 'Healthcare', 'Telecommunications', 'Government']
    
    for name in industry_names:
        ind = Industry.search([('name', '=', name)], limit=1)
        if not ind:
            ind = Industry.create({'name': name})
        industries[name] = ind
        print(f"   {name}: ID {ind.id}")
    
    # 4. Create Demo Customers
    print("\n4. Creating demo customers...")
    Partner = env['res.partner']
    customers = {}
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
        if cust['country'] not in countries:
            continue
        partner = Partner.search([('name', '=', cust['name'])], limit=1)
        if not partner:
            partner = Partner.create({
                'name': cust['name'],
                'company_type': 'company',
                'country_id': countries[cust['country']].id,
                'industry_id': industries[cust['industry']].id,
                'customer_rank': 1,
            })
        customers[cust['name']] = partner
        print(f"   {cust['name']}: ID {partner.id}")
    
    # 5. Create Demo Products
    print("\n5. Creating demo products...")
    ProductTemplate = env['product.template']
    Product = env['product.product']
    products = {}
    product_data = [
        {'name': 'Queue Management System', 'price': 15000, 'line': 'Legacy Products', 'type': 'consu'},
        {'name': 'Customer Voice Module', 'price': 25000, 'line': 'CVM', 'type': 'consu'},
        {'name': 'Self Service Kiosk', 'price': 35000, 'line': 'Self Service', 'type': 'consu'},
        {'name': 'Digital Signage Analytics', 'price': 20000, 'line': 'Media Analytics', 'type': 'consu'},
        {'name': 'Implementation Services', 'price': 10000, 'line': 'Services', 'type': 'service'},
        {'name': 'Annual Support Package', 'price': 5000, 'line': 'Services', 'type': 'service'},
    ]
    
    for prod in product_data:
        product = Product.search([('name', '=', prod['name'])], limit=1)
        if not product:
            tmpl = ProductTemplate.create({
                'name': prod['name'],
                'type': prod['type'],
                'list_price': prod['price'],
                'product_line_id': product_lines[prod['line']].id,
                'sale_ok': True,
            })
            product = tmpl.product_variant_id
        products[prod['name']] = product
        print(f"   {prod['name']}: ID {product.id}")
    
    # 6. Create Budget Entries
    print("\n6. Creating budget entries...")
    BudgetEntry = env['sales.budget.entry']
    
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
        existing = BudgetEntry.search([
            ('year', '=', budget['year']),
            ('country_id', '=', countries[budget['country']].id),
            ('product_line_id', '=', product_lines[budget['line']].id),
            ('salesperson_id', '=', admin_user.id),
        ], limit=1)
        
        if not existing:
            BudgetEntry.create({
                'year': budget['year'],
                'salesperson_id': admin_user.id,
                'country_id': countries[budget['country']].id,
                'product_line_id': product_lines[budget['line']].id,
                'budget_amount': budget['amount'],
            })
            print(f"   ✓ Created: {budget['year']} - {budget['country']} - {budget['line']}: ${budget['amount']:,.0f}")
        else:
            print(f"   - Exists: {budget['year']} - {budget['country']} - {budget['line']}")
    
    # 7. Create Sale Orders with Recognition Schedules
    print("\n7. Creating sale orders...")
    SaleOrder = env['sale.order']
    RecognitionSchedule = env['sale.order.recognition.schedule']
    
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
        if so_data['customer'] not in customers:
            print(f"   ✗ Customer not found: {so_data['customer']}")
            continue
        
        customer = customers[so_data['customer']]
        
        # Check if order already exists
        existing = SaleOrder.search([
            ('partner_id', '=', customer.id),
            ('date_order', '=', so_data['date']),
        ], limit=1)
        
        if existing:
            print(f"   - Order exists for {so_data['customer']} on {so_data['date']}")
            continue
        
        # Create order lines
        order_lines = []
        for line in so_data['lines']:
            if line['product'] not in products:
                continue
            order_lines.append((0, 0, {
                'product_id': products[line['product']].id,
                'product_uom_qty': line['qty'],
                'price_unit': line['price'],
            }))
        
        if not order_lines:
            continue
        
        # Create sale order
        order = SaleOrder.create({
            'partner_id': customer.id,
            'date_order': so_data['date'],
            'order_line': order_lines,
            'user_id': admin_user.id,
        })
        print(f"   ✓ Created {order.name}: {so_data['customer']} - {so_data['date']}")
        
        # Confirm the order
        try:
            order.action_confirm()
            print(f"      ✓ Confirmed")
        except Exception as e:
            print(f"      ! Could not confirm: {e}")
        
        # Create recognition schedule
        if so_data.get('recognition'):
            for rec in so_data['recognition']:
                try:
                    RecognitionSchedule.create({
                        'sale_order_id': order.id,
                        'recognition_date': rec['date'],
                        'amount': rec['amount'],
                        'description': f"Recognition for {so_data['customer']}",
                    })
                except Exception as e:
                    print(f"      ! Recognition schedule error: {e}")
            print(f"      ✓ Added {len(so_data['recognition'])} recognition entries")
    
    env.cr.commit()
    
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

# Run when executed via odoo-bin shell
if __name__ == '__main__':
    inject_demo_data(env)
