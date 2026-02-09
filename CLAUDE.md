# Odoo 18 Custom Development - Repository Guide

> **Purpose:** Help Claude understand this Odoo 18 repository's structure, custom modules, and development guidelines.
> **Last Updated:** 2026-02-09

---

## Repository Overview

- **Type:** Odoo 18 Enterprise Edition fork with custom extensions
- **Database:** PostgreSQL (odoo/sedco@123)
- **Python:** 3.x with 100 pinned dependencies (see requirements.txt)
- **Focus Areas:** Sales Operations, Manufacturing, CRM, Workflow Automation, Financial Controls
- **Custom Modules:** 29 modules in `odoo/custom_addons/` + 1 in `custom_addons/` = 30 total
- **Tech Stack:** Python (ORM), OWL 2 (JS), PostgreSQL, n8n (workflows), Claude AI integration

---

## Directory Structure

```
/odoo18/
├── odoo/
│   ├── custom_addons/      # PRIMARY: 31 custom modules (EPT series, SEDCO, etc.)
│   ├── addons/             # Core Odoo framework modules
│   └── ent_addons/         # Enterprise addons mirror
├── custom_addons/          # SECONDARY: test_report module
├── addons/                 # Standard Odoo 18 modules (616 total)
├── docs/                   # Technical documentation
│   ├── ODOO_18_GUIDE.md    # Comprehensive Odoo 18 technical reference
│   ├── AI_REFERENCE.md     # AI integration patterns
│   └── plans/              # Architecture and implementation plans
├── venv/                   # Python virtual environment
├── odoo.conf              # Server configuration
├── requirements.txt        # Python dependencies (pinned versions)
└── odoo-bin               # Executable entry point
```

**Addons Path (odoo.conf):**
```
addons, odoo/addons, custom_addons, odoo/custom_addons, odoo/ent_addons
```

---

## Custom Modules by Domain

### Sales & Order Management

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **sale_extended_ept** | Financial security checks | Credit limits, overdue invoice detection, on-hold status, approval.request integration |
| **sale_below_cost_approval_ept** | Margin protection | Prevents sales below cost, requires special approval via wizard |
| **pilot_order_ept** | Pilot/trial order workflow | Pilot order flagging, change control for taxes/freight, approval for modifications |
| **quote_management** | Quote/proposal system | Quote lifecycle management |
| **sales_reports_ept** | Advanced sales analytics | Multiple report types, recognition tracking, sales analysis |

### Financial & Accounting

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **account_extended_ept** | Accounting customizations | Arabic address fields, invoice header images, SEDCO format templates |
| **discount_management_ept** | Hierarchical discount approvals | Job-position-based limits, automatic approval chains (supervisor→manager) |

### Manufacturing & Operations

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **mrp_extended_ept** | Manufacturing enhancements | Scrap tolerance validation, work order costing, time tracking approval, BOM component availability |
| **purchase_extended_ept** | Purchase order enhancements | Purchase workflow improvements |

### Inventory & Stock

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **stock_extended_ept** | Stock management | Pickings, quants, lot enhancements |
| **vendor_tracking_ept** | Vendor & purchase tracking | Vendor management and tracking features |

### Customer & Partner Management

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **customer_management_ept** | Customer relationship enhancements | Validation workflow, invoicing/recognition/distribution schedules linked to sales orders |
| **custom_crm** | CRM customizations | CRM-specific enhancements |
| **crm_extended_ept** | Product master extensions | Model number, product line, product nature fields with template-variant sync |
| **custom_partner_city** | Partner city management | City-related partner features |
| **customer_import_helper** | Data import utilities | Customer data import helpers |

### CRM & Sales Operations

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **sedco_crm** | SEDCO CRM customizations | Company-specific CRM features |
| **sedco_crm_assignment_domain_bridge** | CRM assignment logic | Domain-based lead/opportunity assignment |

### Workflow & Automation

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **sedco_bpm_engine** | BPMN workflow engine | Visual BPMN editor (bpmn-js), JSON compilation, runtime orchestration, parallel/sequential execution |
| **quality_bulk_actions** | Quality control operations | Bulk quality check operations |

### Reporting & Analytics

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **smart_report_builder** | AI-powered reporting | Claude API integration, n8n workflow automation, dynamic report generation |
| **test_report** | Sales analysis reporting | Database view model with pivot/list/form views for sales analysis |

### E-Invoicing & Compliance

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **orchida_uae_e_invoicing** | UAE e-invoicing | UAE compliance, electronic invoicing integration |

### Productivity & Task Management

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **todo_app** | To-Do task management | Task creation, completion tracking, priority organization, progress monitoring |

### Data Management & Utilities

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **custom_apis** | Custom API endpoints | HTTP routes and API integrations |
| **ept_execute_python_code** | Code execution | Secure Python code execution within Odoo |
| **extend_distribution_method** | Distribution extensions | Distribution method enhancements |
| **presales_requests** | Pre-sales workflow | Pre-sales request management |
| **request** | Generic request model | Base request functionality used by other modules |
| **sedco_management** | General SEDCO features | Company-specific management features |

---

## Development Guidelines

### Before Adding Features

1. **Search existing EPT modules** - Many patterns already exist:
   ```bash
   # Find similar functionality
   grep -r "approval.request" odoo/custom_addons/
   grep -r "your_field_name" odoo/custom_addons/
   ```

2. **Check field/model dependencies:**
   ```bash
   # Find where a model/field is used
   grep -r "model.name" odoo/custom_addons/ addons/
   grep -r "field_name" odoo/custom_addons/ addons/
   ```

3. **Review manifest dependencies:**
   ```bash
   # Check what depends on a module
   grep -r "'module_name'" odoo/custom_addons/*/__manifest__.py
   ```

4. **Consult documentation:**
   - `/docs/ODOO_18_GUIDE.md` - Comprehensive technical reference
   - `/odoo/custom_addons/README.md` - EPT module overview
   - Individual module READMEs for specific features

### Approval Workflows

**CRITICAL:** ALL EPT modules use Odoo's built-in `approval.request` mechanism for exception handling.

**Do NOT create custom approval systems.** Instead:
```python
# Create approval request
approval = self.env['approval.request'].create({
    'name': 'Request Description',
    'request_owner_id': self.env.user.id,
    'approver_ids': [(6, 0, approver_ids)],
    'category_id': category_id,
    # Link to source document
    'res_model': self._name,
    'res_id': self.id,
})
```

**EPT modules using approval.request:**
- sale_extended_ept (credit limit, overdue checks)
- sale_below_cost_approval_ept (margin validation)
- pilot_order_ept (change control)
- discount_management_ept (hierarchical approvals)
- mrp_extended_ept (time tracking approval)

### Odoo 18 Specifics to Consider

**New in Odoo 18:**
```python
# 1. Precompute - compute fields before form display (performance)
field_name = fields.Selection(
    compute='_compute_field',
    precompute=True,  # NEW in Odoo 18
    store=True,
    readonly=False
)

# 2. Auto company context filtering
class MyModel(models.Model):
    _check_company_auto = True  # NEW in Odoo 18

# 3. Enhanced SQL utilities
from odoo.tools import SQL, create_index, float_is_zero

# 4. Field Command API
from odoo.fields import Command
partner_ids = [(Command.link(partner.id))]
```

**Common patterns:**
```python
# Multiple inheritance (mixins)
class SaleOrder(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

# Field tracking in chatter
partner_id = fields.Many2one('res.partner', tracking=True)

# Company validation
partner_id = fields.Many2one('res.partner', check_company=True)

# Context-based dependencies
@api.depends_context('allowed_company_ids')
def _compute_available_products(self):
    pass
```

### Module Dependencies

**Check dependencies before cross-module references:**
```python
# __manifest__.py
{
    'depends': [
        'base',           # Core Odoo
        'sale',           # Parent module
        'account',        # If using account models
        'custom_module',  # Other custom modules
    ],
}
```

**Dependency chain example:**
```
sale_extended_ept
  ├─ depends: sale, account
  └─ used by: pilot_order_ept, quote_management

customer_management_ept
  ├─ depends: sale, crm
  └─ adds: recognition/invoicing/distribution schedules
```

### Standard Module Structure

```
module_name/
├── __init__.py              # Import submodules
├── __manifest__.py          # version='18.0.1.0.0', depends=[], data=[]
├── models/
│   ├── __init__.py
│   └── model_name.py        # Python ORM models
├── views/
│   └── view_name.xml        # Form, tree, pivot, kanban views
├── security/
│   ├── ir.model.access.csv  # Record-level access control
│   └── ir_rules.xml         # Domain-based security rules
├── wizard/                  # Transient models for wizards
│   └── wizard_name.py
├── controllers/             # HTTP routes/API endpoints
│   └── controllers.py
├── reports/                 # Report templates (QWeb)
│   └── report_name.xml
├── data/                    # Static data files
│   └── data.xml
├── static/                  # Frontend assets
│   ├── src/js/
│   ├── src/scss/
│   └── src/xml/
└── README.md               # Module documentation
```

### Database View Pattern (for reports)

```python
# Used by test_report module
class ReportModel(models.Model):
    _name = 'report.name'
    _auto = False              # Don't auto-create table
    _rec_name = 'display_field'

    field1 = fields.Char(readonly=True)
    field2 = fields.Float(readonly=True)

    def init(self):
        """Create database view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    field1,
                    SUM(field2) AS total
                FROM source_table
                GROUP BY field1
            )
        """ % self._table)
```

---

## Key Patterns in This Repo

### EPT Naming Convention

| Pattern | Meaning | Example |
|---------|---------|---------|
| `*_extended_ept` | Extends existing Odoo module | sale_extended_ept extends sale module |
| `*_management_ept` | New management features | customer_management_ept adds customer workflows |
| `*_ept` | EPT series module | All use approval.request for consistency |

### SEDCO-Specific Customizations

**SEDCO modules** (company-specific):
- `sedco_crm` - CRM customizations
- `sedco_management` - General management features
- `sedco_bpm_engine` - Workflow automation engine
- `sedco_crm_assignment_domain_bridge` - CRM assignment logic

**Company branding:**
- Invoice templates with SEDCO format (account_extended_ept)
- Arabic address fields (account_extended_ept)
- Custom header images on invoices

### Consistent Technical Patterns

| Pattern | Usage | Example |
|---------|-------|---------|
| **approval.request** | Exception handling | ALL EPT modules for credit limits, discounts, below-cost sales |
| **mail.thread inheritance** | Activity tracking | Most transactional models (sales, manufacturing, CRM) |
| **tracking=True** | Field change history | Key fields log changes to chatter |
| **check_company=True** | Multi-company validation | Relational fields validate company context |
| **Database views (_auto=False)** | Read-only reports | test_report, analytics modules |
| **TransientModel (wizard/)** | Temporary workflows | Approval wizards, data import helpers |

---

## Integration Points

### External Systems

| Integration | Module | Purpose |
|-------------|--------|---------|
| **n8n workflows** | smart_report_builder | Workflow automation and API orchestration |
| **Claude AI API** | smart_report_builder | AI-powered report generation |
| **BPMN-js** | sedco_bpm_engine | Visual workflow editor |
| **UAE e-Invoice API** | orchida_uae_e_invoicing | E-invoicing compliance |

### MCP (Model Context Protocol)

**Available tools:**
- crm_search_leads, crm_create_lead, crm_update_lead
- sale_search_orders
- partner_search, partner_create

See `/MCP_SETUP_COMPLETE.md` for configuration details.

---

## Common Tasks

### Adding a New Custom Module

1. Create directory in `odoo/custom_addons/`
2. Create `__manifest__.py` with version='18.0.1.0.0'
3. Add models/, views/, security/ as needed
4. If using approvals, follow approval.request pattern
5. Add to odoo.conf addons_path (already configured)
6. Update module: `./odoo-bin -u module_name -d database_name`

### Finding Dependencies

```bash
# What modules does X depend on?
cat odoo/custom_addons/module_name/__manifest__.py | grep depends

# What modules depend on X?
grep -r "'module_name'" odoo/custom_addons/*/__manifest__.py

# Where is a field used?
grep -r "field_name" odoo/custom_addons/ addons/ --include="*.py" --include="*.xml"
```

### Debugging Field Dependencies

```python
# In models, check @api.depends decorators
@api.depends('partner_id', 'date_order')
def _compute_validity_date(self):
    # This field recomputes when partner_id or date_order changes
    pass

# Check onchange methods
@api.onchange('product_id')
def _onchange_product(self):
    # This triggers when product_id changes in UI
    pass
```

### Testing Changes

```bash
# Start Odoo in development mode
./odoo-bin --dev=all -d database_name

# Update module after code changes
./odoo-bin -u module_name -d database_name

# Run unit tests
./odoo-bin --test-enable -i module_name -d test_database --stop-after-init
```

---

## References

### Primary Documentation
- **`/docs/ODOO_18_GUIDE.md`** - Comprehensive Odoo 18 technical reference (ORM, views, workflows, performance)
- **`/odoo/custom_addons/README.md`** - EPT module series documentation
- **`/docs/AI_REFERENCE.md`** - AI integration patterns
- **`/MCP_SETUP_COMPLETE.md`** - MCP server setup and tools

### Module-Specific READMEs
Check individual module directories for detailed documentation:
- `odoo/custom_addons/sedco_bpm_engine/README.md` - BPM engine architecture
- `odoo/custom_addons/smart_report_builder/README.md` - AI report builder
- `odoo/custom_addons/customer_management_ept/README.md` - Customer workflows
- `odoo/custom_addons/pilot_order_ept/README.md` - Pilot order change control
- `odoo/custom_addons/discount_management_ept/README.md` - Discount approval hierarchy

### External Resources
- **Odoo 18 Official Docs:** https://www.odoo.com/documentation/18.0/
- **Odoo Community:** https://www.odoo.com/forum
- **OCA (Odoo Community Association):** https://github.com/OCA

---

## Troubleshooting

### Common Issues

**Issue:** "Module not found"
```bash
# Check addons path in odoo.conf
grep addons_path odoo.conf

# Verify module directory exists
ls odoo/custom_addons/module_name/
```

**Issue:** "Field doesn't exist"
```bash
# Update module to apply model changes
./odoo-bin -u module_name -d database_name

# Check if field is in manifest data files
cat odoo/custom_addons/module_name/__manifest__.py
```

**Issue:** "Access denied"
```bash
# Check security CSV
cat odoo/custom_addons/module_name/security/ir.model.access.csv

# Verify user groups
# In Odoo UI: Settings → Users & Companies → Groups
```

---

**Last Updated:** 2026-02-09
**Odoo Version:** 18.0
**Python Version:** 3.x
**Database:** PostgreSQL 12+
