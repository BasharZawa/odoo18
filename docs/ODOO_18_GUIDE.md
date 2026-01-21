# Odoo 18 Comprehensive Technical Guide

> **Version**: Odoo 18.0 | **Last Updated**: January 2026  
> **Purpose**: Authoritative reference for developers and consultants with intermediate Odoo knowledge

---

## Table of Contents

1. [Core Architecture and Concepts](#1-core-architecture-and-concepts)
2. [Standard Modules and Business Flows](#2-standard-modules-and-business-flows)
3. [Customizations](#3-customizations)
4. [Configuration Best Practices](#4-configuration-best-practices)
5. [Performance, Security, and Scalability](#5-performance-security-and-scalability)
6. [Common Pitfalls and Solutions](#6-common-pitfalls-and-solutions)
7. [Appendix: Quick Reference](#7-appendix-quick-reference)

---

# 1. Core Architecture and Concepts

<!-- UPDATE_CHECK: v18.0 - Review for ORM changes -->

## 1.1 Odoo Architecture Overview

Odoo follows a **three-tier architecture**:

| Layer | Description |
|-------|-------------|
| **Data Layer** | PostgreSQL database storing all business data |
| **Logic Layer** | Python-based ORM and business logic (server-side) |
| **Presentation Layer** | Web client (JavaScript/OWL), XML views, QWeb templates |

### Directory Structure (Standard Installation)

```
/odoo
├── odoo/                    # Core framework
│   ├── addons/              # Core modules
│   ├── tools/               # Utility functions
│   └── models.py            # Base ORM classes
├── addons/                  # Enterprise/Community modules
└── custom_addons/           # Your custom modules
```

---

## 1.2 ORM Fundamentals

### Models

All business objects inherit from `models.Model`:

```python
from odoo import models, fields, api

class SaleOrder(models.Model):
    _name = 'sale.order'
    _description = 'Sales Order'
    _order = 'date_order desc, id desc'
    _rec_name = 'name'
    
    name = fields.Char(string='Order Reference', required=True)
    date_order = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    order_line_ids = fields.One2many('sale.order.line', 'order_id', string='Order Lines')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], default='draft')
```

**Model Types**:

| Type | Base Class | Purpose |
|------|-----------|---------|
| **Regular** | `models.Model` | Persistent data stored in database |
| **Transient** | `models.TransientModel` | Temporary wizard data (see note below) |
| **Abstract** | `models.AbstractModel` | Mixin classes, not instantiated directly |

> [!IMPORTANT]
> **TransientModel Garbage Collection**: Transient records are auto-cleaned by the scheduled action **"Base: Auto-vacuum internal data"** (typically runs hourly). Records older than ~1 hour are deleted. If your wizard data disappears unexpectedly, check this cron job's frequency. For longer-lived temporary data, consider using `models.Model` with manual cleanup instead.

### Fields Reference

<!-- UPDATE_CHECK: v18.0 - Check for new field types -->

| Field Type | Example | Notes |
|------------|---------|-------|
| `Char` | `name = fields.Char(size=100)` | String, optional max length |
| `Text` | `notes = fields.Text()` | Multi-line text |
| `Integer` | `sequence = fields.Integer()` | Integer values |
| `Float` | `amount = fields.Float(digits=(16,2))` | Decimal with precision |
| `Monetary` | `total = fields.Monetary(currency_field='currency_id')` | Currency-aware amounts |
| `Boolean` | `active = fields.Boolean(default=True)` | True/False |
| `Date` | `date = fields.Date()` | Date without time |
| `Datetime` | `timestamp = fields.Datetime()` | Date with time |
| `Selection` | `state = fields.Selection([...])` | Dropdown choices |
| `Many2one` | `partner_id = fields.Many2one('res.partner')` | FK relationship |
| `One2many` | `line_ids = fields.One2many('model', 'parent_id')` | Reverse of Many2one |
| `Many2many` | `tag_ids = fields.Many2many('res.tag')` | M2M relationship |
| `Html` | `description = fields.Html()` | Rich HTML content |
| `Binary` | `attachment = fields.Binary()` | File storage |

### Computed Fields

```python
class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    
    quantity = fields.Float(default=1.0)
    price_unit = fields.Float(string='Unit Price')
    subtotal = fields.Float(compute='_compute_subtotal', store=True)
    
    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
```

**Key Rules**:
- Use `@api.depends()` to declare dependencies
- Set `store=True` for database persistence (enables search/group)
- Without `store=True`, computed on-the-fly each access

### Inverse Methods

For editable computed fields:

```python
subtotal = fields.Float(
    compute='_compute_subtotal',
    inverse='_inverse_subtotal',
    store=True
)

def _inverse_subtotal(self):
    for line in self:
        if line.quantity:
            line.price_unit = line.subtotal / line.quantity
```

### Related Fields

Shortcut for accessing related record fields:

```python
partner_email = fields.Char(related='partner_id.email', store=True, readonly=False)
```

---

## 1.3 Inheritance Patterns

<!-- UPDATE_CHECK: v18.0 - Verify inheritance behavior -->

### Extension Inheritance (Most Common)

Extend an existing model:

```python
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    loyalty_points = fields.Integer(string='Loyalty Points', default=0)
    
    def action_add_loyalty_points(self, points):
        self.loyalty_points += points
```

### Classical Inheritance

Create a new model copying fields from parent:

```python
class VipPartner(models.Model):
    _name = 'vip.partner'
    _inherit = 'res.partner'  # Copies all fields
    _description = 'VIP Partner'
    
    vip_level = fields.Selection([('gold', 'Gold'), ('platinum', 'Platinum')])
```

### Delegation Inheritance

Embedded object pattern:

```python
class ProductProduct(models.Model):
    _name = 'product.product'
    _inherits = {'product.template': 'product_tmpl_id'}
    
    product_tmpl_id = fields.Many2one('product.template', required=True, ondelete='cascade')
    # All product.template fields accessible directly on product.product
```

**Comparison Table**:

| Pattern | `_inherit` | `_name` | Result |
|---------|-----------|---------|--------|
| Extension | `'res.partner'` | *(omit)* | Adds fields/methods to existing model |
| Classical | `'res.partner'` | `'vip.partner'` | New model with copied structure |
| Delegation | *(use `_inherits`)* | `'product.product'` | Embedded linked record |

---

## 1.4 Security Model

### Access Control Layers

```
User → Groups → Access Rights → Record Rules → Field-Level Access
```

### Groups (res.groups)

Defined in XML:

```xml
<record id="group_sale_manager" model="res.groups">
    <field name="name">Sales Manager</field>
    <field name="category_id" ref="base.module_category_sales"/>
    <field name="implied_ids" eval="[(4, ref('group_sale_user'))]"/>
</record>
```

### Access Rights (ir.model.access)

CSV file `security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sale_order_user,sale.order.user,model_sale_order,group_sale_user,1,1,1,0
access_sale_order_manager,sale.order.manager,model_sale_order,group_sale_manager,1,1,1,1
```

### Record Rules (ir.rule)

Row-level security:

```xml
<record id="sale_order_personal_rule" model="ir.rule">
    <field name="name">Personal Orders</field>
    <field name="model_id" ref="sale.model_sale_order"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('group_sale_user'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
</record>
```

### Superuser Bypass

```python
# Bypass access rights (use sparingly!)
self.env['sale.order'].sudo().search([])

# Switch user context
self.env['sale.order'].with_user(other_user).search([])
```

---

## 1.5 Module Structure

### Standard Layout

```
my_module/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── my_model.py
├── views/
│   └── my_model_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   └── initial_data.xml
├── static/
│   └── description/
│       └── icon.png
├── controllers/
│   └── main.py
└── wizard/
    └── my_wizard.py
```

### Manifest File

```python
# __manifest__.py
{
    'name': 'My Custom Module',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Short description',
    'description': """Long description with features""",
    'author': 'Your Company',
    'website': 'https://yourwebsite.com',
    'license': 'LGPL-3',
    'depends': ['sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/my_model_views.xml',
        'data/initial_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'my_module/static/src/js/*.js',
            'my_module/static/src/css/*.css',
        ],
    },
    'demo': ['demo/demo_data.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
```

---

# 2. Standard Modules and Business Flows

<!-- UPDATE_CHECK: v18.0 - Review flow changes in new version -->

## 2.1 Sales Flow

```
┌────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│ Quotation  │────►│ Sales Order  │────►│  Delivery   │────►│   Invoice   │
│  (draft)   │     │   (sale)     │     │   (done)    │     │   (posted)  │
└────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

### Key Models

| Model | Purpose |
|-------|---------|
| `sale.order` | Sales order header |
| `sale.order.line` | Order line items |
| `sale.order.template` | Quotation templates |

### Important Methods

```python
# Confirm quotation → Sales Order
order.action_confirm()

# Create invoice from sales order
order._create_invoices()

# Send quotation by email
order.action_quotation_send()
```

### Configuration: Settings → Sales

- **Quotation Validity**: Default validity days
- **Sales Warnings**: Product/customer warnings
- **Invoicing Policy**: Ordered quantities vs. delivered quantities

---

## 2.2 Purchase Flow

```
┌────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│    RFQ     │────►│    PO        │────►│   Receipt   │────►│    Bill     │
│  (draft)   │     │  (purchase)  │     │   (done)    │     │   (posted)  │
└────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
```

### Key Models

| Model | Purpose |
|-------|---------|
| `purchase.order` | Purchase order header |
| `purchase.order.line` | Order line items |
| `product.supplierinfo` | Vendor pricelists |

### Vendor Bills

Created from `account.move` with `move_type='in_invoice'`:

```python
# Match bill to PO receipt
bill.action_post()
```

---

## 2.3 Inventory and Warehouse

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Warehouse** | Physical location container |
| **Location** | Specific storage area (can be virtual) |
| **Stock Move** | Movement between locations |
| **Stock Quant** | Current quantity at location |
| **Stock Picking** | Group of moves (delivery, receipt) |

### Location Types

```python
# Internal: physical warehouse locations
# Customer: virtual, represents sold goods
# Supplier: virtual, represents incoming goods
# Inventory: virtual, for adjustments
# Production: for manufacturing consumption
```

### Transfers

```python
# Create picking
picking = self.env['stock.picking'].create({
    'picking_type_id': self.env.ref('stock.picking_type_out').id,
    'location_id': warehouse.lot_stock_id.id,
    'location_dest_id': customer_location.id,
})

# Validate transfer
picking.action_confirm()
picking.action_assign()  # Reserve stock
picking.button_validate()  # Complete transfer
```

### Routes and Rules

- **Push Rules**: Auto-move after arrival (e.g., reception → quality → stock)
- **Pull Rules**: Triggered by demand (e.g., MTO, replenishment)

---

## 2.4 Manufacturing (MRP)

### Key Models

| Model | Purpose |
|-------|---------|
| `mrp.bom` | Bill of Materials |
| `mrp.production` | Manufacturing Order |
| `mrp.workcenter` | Work centers |
| `mrp.workorder` | Work orders (if work centers used) |

### BOM Types

```python
# Normal: Finished product from components
# Kit: Auto-explode on sales (no MO needed)
# Subcontracting: External manufacturing
```

### Manufacturing Order Flow

```python
mo = self.env['mrp.production'].create({
    'product_id': product.id,
    'product_qty': 10,
    'bom_id': bom.id,
})
mo.action_confirm()   # Confirm MO
mo.action_assign()    # Reserve components
mo.button_mark_done() # Complete production
```

---

## 2.5 Accounting

<!-- UPDATE_CHECK: v18.0 - Check for new accounting features -->

> [!CAUTION]
> **Legacy Model Removed**: The `account.invoice` model was removed in Odoo 13+. All invoice operations now use `account.move`. Never reference `account.invoice` in new code.

### Core Models

| Model | Purpose |
|-------|---------|
| `account.move` | Journal entries (invoices, bills, entries) |
| `account.move.line` | Journal items |
| `account.journal` | Journals (sales, purchase, bank, etc.) |
| `account.account` | Chart of accounts |
| `account.tax` | Tax definitions |
| `account.partial.reconcile` | Links debits to credits (see Reconciliation) |

### Move Types

```python
# move_type values
'entry'        # Manual journal entry
'out_invoice'  # Customer invoice
'out_refund'   # Customer credit note
'in_invoice'   # Vendor bill
'in_refund'    # Vendor credit note
```

### Posting Entries

```python
invoice = self.env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': customer.id,
    'invoice_line_ids': [
        Command.create({
        'product_id': product.id,
        'quantity': 1,
     })
    ],
})
invoice.action_post()  # Validate and post
```

### Payment Reconciliation Triangle

> [!WARNING]
> **Critical Architecture**: In Odoo 18, payments are **never directly linked** to invoices via foreign key. The relationship is managed through `account.partial.reconcile`.

```
┌─────────────────────┐                    ┌─────────────────────┐
│ Invoice (account.move) │                    │ Payment (account.payment) │
│                     │                    │                     │
│ Posts DEBIT on A/R  │                    │ Posts CREDIT on A/R │
└─────────┬───────────┘                    └──────────┬──────────┘
          │                                           │
          │         ┌───────────────────────┐         │
          └────────►│ account.partial.reconcile │◄────────┘
                    │   (glues debit + credit)  │
                    └───────────────────────┘
```

**Wrong approach**:
```python
# ❌ This does NOT work - there is no direct FK
payment.invoice_id = invoice.id
```

**Correct approach**:
```python
# ✅ Reconcile the journal entry lines
# Get the receivable line from invoice
invoice_receivable = invoice.line_ids.filtered(
    lambda l: l.account_id.account_type == 'asset_receivable'
)

# Get the receivable line from payment
payment_receivable = payment.move_id.line_ids.filtered(
    lambda l: l.account_id.account_type == 'asset_receivable'
)

# Reconcile them - this creates account.partial.reconcile records
(invoice_receivable + payment_receivable).reconcile()
```

### Analytic Accounting (v17/v18 Architecture Shift)

<!-- UPDATE_CHECK: v18.0 - Analytic Plans system -->

> [!IMPORTANT]
> **Breaking Change from v16+**: The legacy `analytic_account_id` Many2one field has been **removed** from line models. Odoo now uses a JSON-based `analytic_distribution` field, allowing one line to split across multiple analytic accounts.

**Legacy Concept (REMOVED)**:
```python
# ❌ OLD (v15 and earlier) - NO LONGER EXISTS
line.analytic_account_id = account.id  # One line → One account
```

**Current Architecture (v17/v18)**:
```python
# ✅ NEW - JSON-based distribution
line.analytic_distribution = {
    str(analytic_account_1.id): 60.0,  # 60% to Marketing
    str(analytic_account_2.id): 40.0,  # 40% to Sales
}
# Keys are STRINGIFIED analytic account IDs
# Values are PERCENTAGES (must sum to 100 or less)
```

**Reading Analytic Data**:
```python
# Parse the JSON distribution
for line in invoice.invoice_line_ids:
    distribution = line.analytic_distribution or {}
    for account_id_str, percentage in distribution.items():
        account = self.env['account.analytic.account'].browse(int(account_id_str))
        amount = line.price_subtotal * (percentage / 100)
        print(f"{account.name}: {percentage}% = {amount}")
```

**Analytic Plans**: Distribution is now validated against `account.analytic.plan` configurations, which define required/optional plans per company.

### Automatic Analytic Distribution

Use `account.analytic.distribution.model` to auto-apply distributions:

```python
# When a product/partner/account matches, distribution is auto-set
distribution_rule = self.env['account.analytic.distribution.model'].create({
    'product_id': product.id,
    'analytic_distribution': {
        str(analytic_id): 100.0,
    },
})
```

---

## 2.6 CRM

### Lead/Opportunity Flow

```
Lead -> Opportunity -> New Quotation -> Quotation Confirmed -> Opportunity Won
┌──────────┐     ┌─────────────┐     ┌────────────┐
│   Lead   │────►│ Opportunity │────►│ Won / Lost │
└──────────┘     └─────────────┘     └────────────┘
```

### Key Fields

```python
class CrmLead(models.Model):
    _name = 'crm.lead'
    
    type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')])
    stage_id = fields.Many2one('crm.stage')
    probability = fields.Float()
    expected_revenue = fields.Monetary()
    user_id = fields.Many2one('res.users')  # Salesperson
    team_id = fields.Many2one('crm.team')   # Sales team
```

### Convert Lead to Opportunity

```python
lead.convert_opportunity(partner_id, user_ids, team_id)
```

---

# 3. Customizations

## 3.1 Python Customizations

### Extending Models

```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SaleOrderExtension(models.Model):
    _inherit = 'sale.order'
    
    # New field
    approval_required = fields.Boolean(compute='_compute_approval_required', store=True)
    approved_by = fields.Many2one('res.users', string='Approved By')
    
    @api.depends('amount_total')
    def _compute_approval_required(self):
        limit = float(self.env['ir.config_parameter'].sudo().get_param(
            'sale.approval_limit', default=10000
        ))
        for order in self:
            order.approval_required = order.amount_total > limit
    
    @api.constrains('amount_total', 'state')
    def _check_approval(self):
        for order in self:
            if order.state == 'sale' and order.approval_required and not order.approved_by:
                raise ValidationError("Orders above limit require approval!")
    
    def action_confirm(self):
        for order in self:
            if order.approval_required and not order.approved_by:
                raise ValidationError("Please get approval before confirming.")
        return super().action_confirm()
```

### Decorators Reference

| Decorator | Purpose |
|-----------|---------|
| `@api.depends('field')` | Computed field dependencies |
| `@api.constrains('field')` | Python validation constraints |
| `@api.onchange('field')` | Form-level pseudo-changes (not stored) |
| `@api.model` | Class method (no recordset) |
| `@api.model_create_multi` | Batch create optimization |

### Overriding CRUD Methods

```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('my.model')
    return super().create(vals_list)

def write(self, vals):
    if 'state' in vals and vals['state'] == 'done':
        self._validate_completion()
    return super().write(vals)

def unlink(self):
    if any(rec.state != 'draft' for rec in self):
        raise ValidationError("Can only delete draft records!")
    return super().unlink()
```

---

## 3.2 XML View Customizations

<!-- UPDATE_CHECK: v18.0 - Check for new view elements -->

### View Inheritance

```xml
<record id="view_sale_order_form_custom" model="ir.ui.view">
    <field name="name">sale.order.form.custom</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="priority">20</field>
    <field name="arch" type="xml">
        <!-- Add field after existing field -->
        <field name="partner_id" position="after">
            <field name="approval_required" readonly="1"/>
        </field>
        
        <!-- Add to notebook -->
        <xpath expr="//notebook" position="inside">
            <page string="Custom Info">
                <group>
                    <field name="approved_by"/>
                </group>
            </page>
        </xpath>
        
        <!-- Add button to header -->
        <xpath expr="//button[@name='action_confirm']" position="before">
            <button name="action_request_approval" 
                    string="Request Approval"
                    type="object"
                    invisible="not approval_required or approved_by"/>
        </xpath>
        
        <!-- Modify existing attributes -->
        <field name="payment_term_id" position="attributes">
            <attribute name="required">1</attribute>
        </field>
    </field>
</record>
```

### XPath Reference

| Expression | Matches |
|------------|---------|
| `//field[@name='x']` | Field with name='x' |
| `//button[@name='x']` | Button with name='x' |
| `//page[@name='x']` | Notebook page |
| `//group[1]` | First group element |
| `//notebook/page[2]` | Second page in notebook |

### Position Values

| Position | Effect |
|----------|--------|
| `after` | Insert after matched element |
| `before` | Insert before matched element |
| `inside` | Insert as last child |
| `replace` | Replace matched element |
| `attributes` | Modify attributes |

### Form View Structure

```xml
<record id="view_my_model_form" model="ir.ui.view">
    <field name="name">my.model.form</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <form string="My Model">
            <header>
                <button name="action_confirm" string="Confirm" type="object" 
                        class="oe_highlight" invisible="state != 'draft'"/>
                <field name="state" widget="statusbar" 
                       statusbar_visible="draft,confirmed,done"/>
            </header>
            <sheet>
                <div class="oe_title">
                    <h1><field name="name" placeholder="Name..."/></h1>
                </div>
                <group>
                    <group>
                        <field name="partner_id"/>
                        <field name="date"/>
                    </group>
                    <group>
                        <field name="amount"/>
                        <field name="currency_id"/>
                    </group>
                </group>
                <notebook>
                    <page string="Lines" name="lines">
                        <field name="line_ids">
                            <tree editable="bottom">
                                <field name="product_id"/>
                                <field name="quantity"/>
                                <field name="price"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Notes" name="notes">
                        <field name="notes" nolabel="1"/>
                    </page>
                </notebook>
            </sheet>
            <div class="oe_chatter">
                <field name="message_follower_ids"/>
                <field name="activity_ids"/>
                <field name="message_ids"/>
            </div>
        </form>
    </field>
</record>
```

### Tree/List View

```xml
<record id="view_my_model_tree" model="ir.ui.view">
    <field name="name">my.model.tree</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <tree string="My Models" decoration-danger="state == 'cancel'"
              decoration-success="state == 'done'">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="date"/>
            <field name="amount" sum="Total"/>
            <field name="state" widget="badge" 
                   decoration-success="state == 'done'"
                   decoration-warning="state == 'draft'"/>
        </tree>
    </field>
</record>
```

---

## 3.3 JavaScript (OWL Framework)

<!-- UPDATE_CHECK: v18.0 - OWL version and API changes -->

### Odoo 18 Uses OWL 2

OWL (Odoo Web Library) is the component framework for Odoo's web client.

### Basic Component Structure

```javascript
/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MyComponent extends Component {
    static template = "my_module.MyComponent";
    static props = {
        title: { type: String, optional: true },
    };
    
    setup() {
        this.state = useState({
            counter: 0,
        });
    }
    
    increment() {
        this.state.counter++;
    }
}

// Register as action
registry.category("actions").add("my_custom_action", MyComponent);
```

### Component Template (QWeb)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <t t-name="my_module.MyComponent">
        <div class="my-component">
            <h2 t-esc="props.title or 'Default Title'"/>
            <p>Count: <t t-esc="state.counter"/></p>
            <button class="btn btn-primary" t-on-click="increment">
                Increment
            </button>
        </div>
    </t>
</templates>
```

### Using Services

```javascript
import { useService } from "@web/core/utils/hooks";

class MyComponent extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
    }
    
    async fetchData() {
        const records = await this.orm.searchRead(
            "res.partner",
            [["is_company", "=", true]],
            ["name", "email"]
        );
        return records;
    }
    
    showNotification() {
        this.notification.add("Operation successful!", { type: "success" });
    }
    
    openForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            views: [[false, "form"]],
            target: "current",
        });
    }
}
```

### Form View Field Widget

```javascript
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";

class ColoredCharField extends CharField {
    static template = "my_module.ColoredCharField";
}

const coloredCharField = {
    ...charField,
    component: ColoredCharField,
};

registry.category("fields").add("colored_char", coloredCharField);
```

### Assets Declaration

```python
# In __manifest__.py
'assets': {
    'web.assets_backend': [
        'my_module/static/src/js/**/*.js',
        'my_module/static/src/xml/**/*.xml',
        'my_module/static/src/css/**/*.css',
    ],
},
```

---

## 3.4 Spreadsheet Reporting (v17/v18 Standard)

<!-- UPDATE_CHECK: v18.0 - Spreadsheet feature additions -->

> [!NOTE]
> **Architecture Shift**: In Odoo 17/18, internal business reporting (Sales Analysis, Stock Aging, Budget Reports) has moved from QWeb/Pivot views to **Odoo Spreadsheet**, reducing the need for custom Python `read_group` queries.

### When to Use Spreadsheet vs. QWeb

| Report Type | Technology | Notes |
|-------------|------------|---------|
| PDF Output (Invoice, Delivery) | QWeb Reports | Traditional, still standard |
| Internal Analysis (Sales, Stock) | Spreadsheet | Live data, user-customizable |
| Dashboard KPIs | Spreadsheet | Embedded in views |
| Complex Business Logic | Custom Python + QWeb | When calculations are complex |

### Spreadsheet Architecture

**Key Components**:
- `spreadsheet.document`: Stores spreadsheet definitions (JSON data)
- `spreadsheet.template`: Reusable templates for reports
- Live ORM integration via `ODOO.PIVOT` and `ODOO.LIST` formulas

**Creating a Spreadsheet Template**:
```python
# Spreadsheet templates are typically created via UI, but can be defined:
template = self.env['spreadsheet.template'].create({
    'name': 'Sales Analysis Template',
    'data': json.dumps(spreadsheet_data_structure),
})
```

### Spreadsheet Formulas

```javascript
// In spreadsheet cells - these pull live Odoo data:

// Pivot table formula
=ODOO.PIVOT(1, "probability")  // Returns probability measure from pivot 1

// List formula
=ODOO.LIST(1, 1, "name")  // Returns name field from row 1 of list 1

// Filtered pivot
=ODOO.PIVOT(1, "expected_revenue", "stage_id", "Won")
```

### Developer Implications

1. **Less Python Reporting Code**: Standard analytics use Spreadsheet UI, not custom models
2. **Dynamic Updates**: Users modify report structure without developer involvement  
3. **Export Capability**: Spreadsheets export to Excel natively

### When You Still Need Custom Code

```python
# Complex calculations requiring server logic
class CustomReport(models.AbstractModel):
    _name = 'report.my_module.custom_report'
    
    def _get_report_values(self, docids, data=None):
        # Complex aggregations, cross-model logic, etc.
        return {
            'docs': self.env['sale.order'].browse(docids),
            'summary': self._compute_complex_summary(docids),
        }
```

---

## 3.5 Odoo Studio

### Capabilities

- Add custom fields (all types)
- Modify views (form, list, kanban, calendar)
- Create automated actions
- Build reports
- Add approval workflows
- Create custom apps

### Limitations

> **Warning**: Studio customizations have significant limitations:

1. **No Python Logic**: Cannot add complex business logic
2. **No Custom Methods**: Cannot override ORM methods
3. **Migration Risk**: Studio changes may conflict with module updates
4. **Limited Inheritance**: Cannot properly extend Python models
5. **Performance**: Some Studio automations less efficient than code

### When to Use Studio vs. Code

| Use Case | Studio | Code |
|----------|--------|------|
| Add simple field | ✅ | ✅ |
| Modify view layout | ✅ | ✅ |
| Complex computed field | ❌ | ✅ |
| API integration | ❌ | ✅ |
| Business logic constraints | ❌ | ✅ |
| Custom reports | ⚠️ Limited | ✅ |
| Approval workflows | ✅ Simple | ✅ Complex |

### Exporting Studio Changes

Studio creates the `studio_customization` module. Export via:
Settings → Technical → Studio → Export Customizations

---

## 3.5 Custom Module Development

### Scaffolding New Module

```bash
# From odoo directory
./odoo-bin scaffold my_module addons/
```

### Module Checklist

- [ ] `__manifest__.py` with correct dependencies
- [ ] `__init__.py` files in all directories
- [ ] `security/ir.model.access.csv` for all models
- [ ] Proper `_description` on all models
- [ ] Unit tests in `tests/` directory
- [ ] i18n translations if needed

### Recommended init.py Pattern

```python
# models/__init__.py
from . import my_model
from . import another_model

# Main __init__.py
from . import models
from . import controllers
from . import wizard
```

---

# 4. Configuration Best Practices

## 4.1 Multi-Company Setup

<!-- UPDATE_CHECK: v18.0 - Multi-company behavior changes -->

### Configuration

1. **Enable Multi-Company**: Settings → Users & Companies → Companies → Create
2. **User Access**: Assign users to companies (Allowed Companies)
3. **Default Company**: Set per user

### Code Considerations

```python
# Company-dependent fields
class MyModel(models.Model):
    _name = 'my.model'
    
    company_id = fields.Many2one(
        'res.company', 
        default=lambda self: self.env.company,
        required=True
    )

# Filter by current company
@api.model
def _search(self, args, **kwargs):
    args = args + [('company_id', 'in', self.env.companies.ids)]
    return super()._search(args, **kwargs)
```

### Inter-Company Transactions

Enable in Settings → General Settings → Multi-Company:
- Synchronize sales/purchase orders
- Automatic invoice creation

---

## 4.2 Chart of Accounts

### Setup Approach

1. **Localized Package**: Use fiscal localization module (e.g., `l10n_us`, `l10n_ae`)
2. **Custom Chart**: Settings → Invoicing → Fiscal Localization

### Account Structure

```
1xxx - Assets
2xxx - Liabilities
3xxx - Equity
4xxx - Revenue
5xxx - COGS
6xxx - Expenses
7xxx - Other Income/Expense
```

### Fiscal Positions

Map taxes and accounts for different scenarios:

```xml
<record id="fiscal_position_export" model="account.fiscal.position">
    <field name="name">Export (Tax-Free)</field>
    <field name="tax_ids" eval="[(0, 0, {
        'tax_src_id': ref('tax_sale_15'),
        'tax_dest_id': False,
    })]"/>
</record>
```

---

## 4.3 Warehouse Configuration

### Single Warehouse (Simple)

- Input/Quality/Stock locations auto-created
- 1-step receipt: direct to stock
- 1-step delivery: direct from stock

### Multi-Step Operations

Settings → Inventory → Warehouse:

**Incoming (3-step)**:
```
Vendor → Input → Quality → Stock
```

**Outgoing (3-step)**:
```
Stock → Pick → Pack → Ship → Customer
```

### Routes Configuration

```
Product → Can be Sold + Can be Purchased
    ├─ Make to Stock (default)
    ├─ Make to Order (on-demand purchase/manufacturing)
    └─ Buy / Manufacture routing
```

---

## 4.4 Email Configuration

### Outgoing Mail Server

Settings → Technical → Email → Outgoing Mail Servers

```
SMTP Server: smtp.yourprovider.com
SMTP Port: 587
Security: TLS
Username: your@email.com
Password: app-specific-password
```

### Incoming Mail (Fetchmail)

Settings → Technical → Email → Incoming Mail Servers

Use for:
- Auto-create leads from email
- Process helpdesk tickets
- Handle email aliases

### Mail Templates

```xml
<record id="email_template_sale_confirm" model="mail.template">
    <field name="name">Sales Order Confirmation</field>
    <field name="model_id" ref="sale.model_sale_order"/>
    <field name="email_from">{{ object.company_id.email }}</field>
    <field name="email_to">{{ object.partner_id.email }}</field>
    <field name="subject">Order {{ object.name }} Confirmed</field>
    <field name="body_html">
        <![CDATA[
        <p>Dear {{ object.partner_id.name }},</p>
        <p>Your order {{ object.name }} has been confirmed.</p>
        ]]>
    </field>
</record>
```

---

## 4.5 User Permissions Strategy

### Role-Based Access Pattern

```
Base Groups (inherited by higher levels):
├── User: Basic access
└── Manager: User + Full access

Department-Specific:
├── Sales User / Sales Manager
├── Purchase User / Purchase Manager
├── Inventory User / Inventory Manager
└── Accounting User / Accounting Manager
```

### Permission Matrix Example

| Action | User | Manager | Admin |
|--------|------|---------|-------|
| Create | ✅ | ✅ | ✅ |
| Read (own) | ✅ | ✅ | ✅ |
| Read (all) | ❌ | ✅ | ✅ |
| Edit (own) | ✅ | ✅ | ✅ |
| Edit (all) | ❌ | ✅ | ✅ |
| Delete | ❌ | ❌ | ✅ |
| Archive | ❌ | ✅ | ✅ |

---

# 5. Performance, Security, and Scalability

## 5.1 Database Optimization

<!-- UPDATE_CHECK: v18.0 - Performance tools changes -->

### Index Recommendations

Add indexes for frequently searched/filtered fields:

```python
class MyModel(models.Model):
    _name = 'my.model'
    
    # Indexed by default: name, create_date
    reference = fields.Char(index=True)
    date = fields.Date(index=True)
    partner_id = fields.Many2one('res.partner', index=True)
```

### Query Analysis

```python
# Enable SQL logging
import logging
_logger = logging.getLogger(__name__)

def my_method(self):
    self.env.cr.execute("EXPLAIN ANALYZE SELECT ...")
    _logger.info(self.env.cr.fetchall())
```

```sql
-- PostgreSQL: Find slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 20;
```

### Prefetching Optimization

```python
# Bad: N+1 queries
for order in orders:
    partner_name = order.partner_id.name  # Separate query each time

# Good: Prefetch
orders = self.env['sale.order'].search([])
orders.mapped('partner_id')  # Single prefetch query
for order in orders:
    partner_name = order.partner_id.name  # From cache
```

### Aggregations: read_group vs _read_group

<!-- UPDATE_CHECK: v18.0 - _read_group API changes -->

> [!TIP]
> **Use `_read_group` for Performance**: In Odoo 17/18, the `_read_group` method (note underscore) was overhauled to return native Python tuples/dicts, making it significantly faster and easier to use for aggregations.

**Public `read_group` (Legacy Style)**:
```python
# Returns list of dicts with special formatting
results = self.env['sale.order'].read_group(
    domain=[('state', '=', 'sale')],
    fields=['amount_total:sum', 'partner_id'],
    groupby=['partner_id']
)
# Result: [{'partner_id': (1, 'Azure Interior'), 'amount_total': 5000.0, ...}]
```

**Private `_read_group` (Modern Preferred)**:
```python
# Returns raw tuples - faster and cleaner for Python processing
results = self.env['sale.order']._read_group(
    domain=[('state', '=', 'sale')],
    groupby=['partner_id'],
    aggregates=['amount_total:sum'],
)
# Result: [(partner_record, 5000.0), ...]
# Direct access to recordsets and values

# Example with multiple aggregates:
for partner, total_amount, order_count in self.env['sale.order']._read_group(
    domain=[('state', '=', 'sale')],
    groupby=['partner_id'],
    aggregates=['amount_total:sum', '__count'],
):
    print(f"{partner.name}: {order_count} orders, ${total_amount}")
```

**When to Use Which**:
| Method | Use Case |
|--------|----------|
| `read_group()` | Web client calls, backward compatibility |
| `_read_group()` | Python server code, performance-critical aggregations |

---

## 5.2 Caching Strategies

### ORM Cache

```python
# Recordset cache: automatic within transaction
# Ormcache: decorator for method caching

from odoo import tools

class MyModel(models.Model):
    @tools.ormcache('self.env.uid', 'key')
    def get_cached_value(self, key):
        # Expensive computation
        return result
    
    def clear_cache(self):
        self.get_cached_value.clear_cache(self)
```

### System Parameters Cache

```python
# Cached system parameter
@tools.ormcache()
def _get_param(self):
    return self.env['ir.config_parameter'].sudo().get_param('my.param', default='value')
```

---

## 5.3 Security Hardening

### Server Configuration

```ini
# odoo.conf
admin_passwd = strong-random-password
list_db = False  # Hide database list on login
proxy_mode = True  # When behind reverse proxy
limit_time_cpu = 120
limit_time_real = 240
limit_memory_hard = 2684354560  # 2.5GB
limit_memory_soft = 2147483648  # 2GB
```

### HTTPS Setup (nginx)

```nginx
server {
    listen 443 ssl;
    server_name odoo.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /longpolling {
        proxy_pass http://127.0.0.1:8072;
    }
}
```

### Security Best Practices

1. **Database Access**: Never expose PostgreSQL publicly
2. **File Permissions**: Restrict access to config files
3. **Admin Account**: Disable or protect master admin
4. **API Access**: Use API keys, not passwords
5. **SQL Injection**: Always use parameterized queries
6. **Regular Updates**: Apply security patches promptly

---

## 5.4 Scalability

### Horizontal Scaling Pattern

```
                    ┌──────────────┐
                    │ Load Balancer│
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐        ┌─────────┐        ┌─────────┐
   │ Odoo 1  │        │ Odoo 2  │        │ Odoo 3  │
   └────┬────┘        └────┬────┘        └────┬────┘
        │                  │                  │
        │           ┌──────┴──────┐           │
        └───────────► PostgreSQL  ◄───────────┘
                    │  (Primary)  │
                    └─────────────┘
```

### Multi-Worker Configuration

```ini
# odoo.conf for production
workers = 4  # CPU cores * 2 (rule of thumb)
max_cron_threads = 2
limit_time_cpu = 600
limit_time_real = 1200
```

### Database Connection Pooling

Use PgBouncer for connection pooling:

```ini
# pgbouncer.ini
[databases]
odoo = host=localhost dbname=odoo

[pgbouncer]
listen_port = 6432
pool_mode = transaction
default_pool_size = 100
```

---

## 5.5 Backup and Disaster Recovery

### Automated Backup Script

```bash
#!/bin/bash
BACKUP_DIR=/var/backups/odoo
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=odoo_production

# Database backup
pg_dump -Fc $DB_NAME > $BACKUP_DIR/db_$DATE.dump

# Filestore backup
tar -czf $BACKUP_DIR/filestore_$DATE.tar.gz /var/lib/odoo/filestore/$DB_NAME

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -mtime +7 -delete
```

### Restoration Process

```bash
# Restore database
pg_restore -d odoo_restored /var/backups/odoo/db_backup.dump

# Restore filestore
tar -xzf /var/backups/odoo/filestore_backup.tar.gz -C /var/lib/odoo/filestore/
```

---

# 6. Common Pitfalls and Solutions

## 6.1 ORM Performance Anti-Patterns

### Problem: N+1 Queries

```python
# ❌ Bad: Creates N+1 queries
for order in orders:
    total += order.partner_id.credit_limit

# ✅ Good: Single query with prefetch
partner_ids = orders.mapped('partner_id')
for order in orders:
    total += order.partner_id.credit_limit
```

### Problem: Looping with Create/Write

```python
# ❌ Bad: N database calls
for line in lines:
    self.env['my.model'].create({'name': line})

# ✅ Good: Batch create
vals_list = [{'name': line} for line in lines]
self.env['my.model'].create(vals_list)
```

### Problem: Computed Field Without Store

```python
# ❌ Issue: Computed every access, cannot search/group
total = fields.Float(compute='_compute_total')

# ✅ Better: Store when you need search/filter
total = fields.Float(compute='_compute_total', store=True)
```

---

## 6.2 Upgrade Compatibility

### Use `_inherit` Properly

```python
# ❌ Risky: Overriding core methods without super()
def action_confirm(self):
    # Custom logic only - breaks standard behavior
    self.state = 'confirmed'

# ✅ Safe: Extend with super()
def action_confirm(self):
    res = super().action_confirm()
    # Additional custom logic
    self._notify_approval_team()
    return res
```

### Avoid Hardcoded XML IDs

```python
# ❌ Risky: Hardcoded reference may not exist
group = self.env.ref('sale.group_sale_manager')

# ✅ Safer: Handle missing reference
group = self.env.ref('sale.group_sale_manager', raise_if_not_found=False)
if group:
    # Use group
```

### Field Dependencies

```python
# ❌ Problem: Base field might change
@api.depends('order_line_ids.price_total')

# ✅ Solution: Also depend on underlying fields
@api.depends('order_line_ids.price_total', 'order_line_ids.product_uom_qty', 
             'order_line_ids.price_unit', 'order_line_ids.discount')
```

---

## 6.3 Data Migration

### XML Data Updates

```xml
<!-- Use noupdate="0" for data that should always update -->
<odoo noupdate="0">
    <record id="my_data" model="my.model" forcecreate="True">
        <field name="name">Updated Name</field>
    </record>
</odoo>
```

### Migration Scripts

```python
# migrations/18.0.1.0.1/pre-migration.py
def migrate(cr, version):
    from odoo.tools.sql import column_exists
    if not column_exists(cr, 'my_table', 'new_column'):
        cr.execute("ALTER TABLE my_table ADD COLUMN new_column VARCHAR")

# migrations/18.0.1.0.1/post-migration.py
def migrate(cr, version):
    cr.execute("""
        UPDATE my_table 
        SET new_column = old_column 
        WHERE new_column IS NULL
    """)
```

---

## 6.4 Integration Challenges

### External API Calls

```python
# ❌ Problem: Blocking call in transaction
def action_sync(self):
    response = requests.get('https://external-api.com/data')  # Blocks!
    self.process_data(response.json())

# ✅ Solution: Use queue_job or scheduled action
def action_sync(self):
    self.with_delay().process_external_sync()  # Async with queue_job

def process_external_sync(self):
    response = requests.get('https://external-api.com/data', timeout=30)
    self.sudo().process_data(response.json())
```

### Error Handling

```python
import requests
from odoo.exceptions import UserError

def call_external_api(self):
    try:
        response = requests.post(
            'https://api.service.com/endpoint',
            json=self._prepare_payload(),
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        raise UserError("API request timed out. Please try again.")
    except requests.HTTPError as e:
        raise UserError(f"API error: {e.response.status_code}")
    except Exception as e:
        _logger.exception("Unexpected API error")
        raise UserError("An unexpected error occurred during API call.")
```

---

## 6.5 Studio vs. Code Customizations

### Migration Path

When Studio customizations become limiting:

1. Export Studio customization module
2. Analyze generated code
3. Recreate as proper Python module
4. Test thoroughly
5. Uninstall Studio customization
6. Install code-based module

### Avoiding Conflicts

```xml
<!-- Priority to ensure code wins over Studio -->
<record id="view_form_inherit" model="ir.ui.view">
    <field name="inherit_id" ref="base_view"/>
    <field name="priority">50</field>  <!-- Higher than Studio's default -->
</record>
```

---

# 7. Appendix: Quick Reference

## 7.1 Common ORM Methods

| Method | Description |
|--------|-------------|
| `search(domain)` | Find records matching domain |
| `search_fetch(domain, field_names) | Find records matching domain and fetch specific fields |
| `browse(ids)` | Get recordset from IDs |
| `create(vals)` | Create new record(s) |
| `write(vals)` | Update records |
| `unlink()` | Delete records |
| `copy()` | Duplicate record |
| `read(['fields'])` | Read as dictionaries |
| `search_read(domain, fields)` | Combined search + read |
| `read_group(domain, fields, groupby)` | Aggregate queries |
| `exists()` | Filter existing records |
| `filtered(lambda)` | Filter by function |
| `mapped('field')` | Extract field values |
| `sorted('field')` | Sort recordset |

## 7.2 Domain Operators

| Operator | Example | Notes |
|----------|---------|-------|
| `=`, `!=` | `[('state', '=', 'done')]` | Equals, not equals |
| `<`, `<=`, `>`, `>=` | `[('amount', '>', 100)]` | Comparisons |
| `like`, `ilike` | `[('name', 'ilike', '%test%')]` | Pattern matching |
| `=like`, `=ilike` | `[('name', '=ilike', 'test%')]` | Exact pattern |
| `in`, `not in` | `[('state', 'in', ['a', 'b'])]` | List membership |
| `child_of` | `[('category_id', 'child_of', 1)]` | Hierarchy |
| `parent_of` | `[('category_id', 'parent_of', 1)]` | Hierarchy |
| `&` (AND) | `['&', ('a', '=', 1), ('b', '=', 2)]` | Logical AND |
| `|` (OR) | `['|', ('a', '=', 1), ('b', '=', 2)]` | Logical OR |
| `!` (NOT) | `['!', ('a', '=', 1)]` | Logical NOT |

## 7.3 Field Attributes

| Attribute | Description |
|-----------|-------------|
| `string` | Display label |
| `required` | Must have value |
| `readonly` | Cannot edit |
| `index` | Database index |
| `default` | Default value (value or callable) |
| `compute` | Computed field method |
| `inverse` | Inverse method (for writable computed) |
| `store` | Store computed field in DB |
| `copy` | Include in duplicate (default True) |
| `groups` | Access groups restriction |
| `company_dependent` | Per-company value |
| `tracking` | Track changes in chatter |

## 7.4 Useful Technical Settings

Access via: Settings → Technical

| Menu | Purpose |
|------|---------|
| Sequences | Auto-numbering |
| System Parameters | Key-value config |
| Scheduled Actions | Cron jobs |
| Server Actions | Automated server logic |
| Email Templates | Notification templates |
| Automation Rules | Auto-triggers |
| User Interface → Views | View definitions |
| User Interface → Actions | Window/Report actions |

## 7.5 Debugging Commands

```python
# In shell
./odoo-bin shell -d mydb

# Log SQL queries
import logging
logging.getLogger('odoo.sql_db').setLevel(logging.DEBUG)

# Interactive debugging
import pdb; pdb.set_trace()

# Or with ipdb
import ipdb; ipdb.set_trace()

# Print recordset info
record.read()  # Dict representation
record.fields_get()  # Field definitions
```

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.0.0 | January 2026 | Initial Odoo 18 guide |

---

<!-- 
UPDATE_CHECK: v18.0 
When Odoo 18 receives updates, review sections marked with UPDATE_CHECK comments.
Key areas to monitor:
- ORM API changes
- OWL framework updates
- New module features
- Security model changes
- Configuration options
-->
