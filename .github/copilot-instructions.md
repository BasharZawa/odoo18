# Odoo 18 Development Guidelines for AI Agents

## Architecture Overview

This is an **Odoo 18** ERP codebase with a modular addon architecture:

- **`odoo/`** - Core framework: ORM (`models.py`, `fields.py`), API (`api.py`), HTTP layer
- **`addons/`** - Official Odoo community modules (CRM, Sale, Stock, etc.)
- **`odoo/ent_addons/`** - Enterprise addons
- **`odoo/custom_addons/`** - Custom SEDCO modules (primary development area)

Custom modules follow the pattern: `sedco_*`, `custom_*`, `x_*`, `quote_management`, etc.

## Module Structure (Required Pattern)

Every Odoo module must have:
```
module_name/
├── __init__.py          # Import models, controllers
├── __manifest__.py      # Module metadata, dependencies, data files
├── models/
│   ├── __init__.py      # Import all model files
│   └── model_name.py    # Model definitions
├── views/               # XML view definitions
├── security/
│   └── ir.model.access.csv  # Access rights (REQUIRED for new models)
└── data/                # Master data, cron jobs
```

## Model Inheritance Patterns

**Extend existing model** (most common):
```python
from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = "crm.lead"  # Extends existing model
    
    custom_field = fields.Char("Custom Field")
```

**Create new model**:
```python
class ProductLine(models.Model):
    _name = 'product.line.ept'
    _description = 'Product Line'
    
    name = fields.Char(required=True)
```

## Essential Decorators

```python
@api.depends('field1', 'field2')      # Computed field dependencies
def _compute_total(self):

@api.onchange('product_id')           # UI-triggered changes
def _onchange_product(self):

@api.constrains('discount')           # Validation rules
def _check_discount(self):

@api.model_create_multi                # Override create() in v18
def create(self, vals_list):
```

## View Inheritance (XML)

Extend views using XPath:
```xml
<record id="view_form_inherit" model="ir.ui.view">
    <field name="inherit_id" ref="module.original_view_id"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='partner_id']" position="after">
            <field name="custom_field"/>
        </xpath>
    </field>
</record>
```

## Security (ir.model.access.csv)

Required format for new models:
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_product_line_user,product.line.user,model_product_line,base.group_user,1,1,1,0
```

## Development Commands

```bash
# Activate virtualenv
source venv/bin/activate

# Scaffold new module
./odoo-bin scaffold module_name odoo/custom_addons

# Start server (uses odoo.conf)
./odoo-bin

# Update specific module
./odoo-bin -u module_name -d database_name

# Install module
./odoo-bin -i module_name -d database_name
```

## Configuration

`odoo.conf` defines:
- `addons_path`: `addons,odoo/addons,custom_addons,odoo/custom_addons,odoo/ent_addons`
- Database: PostgreSQL on localhost:5432

## Custom SEDCO Modules

Key custom modules in `odoo/custom_addons/`:

- **`sedco_crm`** - CRM extensions: lead lifecycle, SLA escalation, stage logging
- **`sedco_bpm_engine`** - BPMN workflow engine with visual editor
- **`quote_management`** - Sale order line extensions with approval workflows
- **`x_product`** - Product template extensions (product lines, natures)

## MCP Integration

The codebase includes an MCP server (`odoo_mcp_server.py`) for AI integration:
- Uses JSON-RPC to communicate with Odoo
- Configured via environment variables: `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`

## Field Types Reference

```python
fields.Char(string='Name')
fields.Text(string='Description')
fields.Integer(string='Quantity')
fields.Float(string='Price', digits=(16, 2))
fields.Boolean(string='Active')
fields.Date(string='Date')
fields.Datetime(string='Timestamp')
fields.Selection([('draft', 'Draft'), ('done', 'Done')], string='State')
fields.Many2one('res.partner', string='Partner')
fields.One2many('sale.order.line', 'order_id', string='Lines')
fields.Many2many('res.partner', string='Partners')
```

## Common Patterns in This Codebase

1. **Computed fields with store=True** for performance:
   ```python
   total = fields.Float(compute='_compute_total', store=True)
   ```

2. **Activity scheduling** for workflows:
   ```python
   lead.activity_schedule('mail.mail_activity_data_todo', user_id=user.id, summary='Follow up')
   ```

3. **Chatter integration** via `mail.thread` mixin:
   ```python
   _inherit = ['mail.thread', 'mail.activity.mixin']
   ```
