# Odoo 18 Development Guide

## Rules

- **Search before building.** Always search `odoo/custom_addons/` for existing functionality before creating anything new.
- **Use `approval.request`** for all approval workflows. Never create custom approval models.
- **Follow EPT naming:** `*_extended_ept` (extends standard module), `*_management_ept` (new features), `sedco_*` (company-specific).
- **Present a plan before coding.** Show what exists, what you'll reuse, and your approach.
- **Update this file** after completing any enhancement that adds modules, changes patterns, or adds integrations.

## Environment

- **Odoo:** 18.0 Enterprise fork
- **Database:** OdooE (PostgreSQL) — user: admin, password: admin
- **URL:** http://localhost:8069
- **Addons path:** addons, odoo/addons, custom_addons, odoo/custom_addons, odoo/ent_addons
- **MCP server:** `odoo_mcp_server.py` (50+ tools, FastMCP, config in `~/.config/Claude/claude_desktop_config.json`)

## Custom Modules (18 total in `odoo/custom_addons/` and `custom_addons/`)

### Sales & Finance
| Module | What it does |
|--------|-------------|
| sale_extended_ept | Credit limits, overdue invoice checks, on-hold status, approval.request |
| sale_below_cost_approval_ept | Blocks sales below cost, approval wizard |
| pilot_order_ept | Pilot order flagging, change control for tax/freight |
| discount_management_ept | Job-position-based discount limits, auto approval chains |
| quote_management | Quote/proposal lifecycle |
| account_extended_ept | Arabic addresses, SEDCO invoice templates, header images |
| sales_reports_ept | Multiple sales report types, recognition tracking |

### Manufacturing & Supply Chain
| Module | What it does |
|--------|-------------|
| mrp_extended_ept | Scrap tolerance, work order costing, time tracking approval |
| purchase_extended_ept | Purchase workflow enhancements |
| stock_extended_ept | Picking, quant, lot enhancements |
| vendor_tracking_ept | Vendor management and tracking |

### CRM & Customers
| Module | What it does |
|--------|-------------|
| customer_management_ept | Validation workflow, invoicing/recognition/distribution schedules |
| crm_extended_ept | Model number, product line, product nature fields (template-variant sync) |

### Workflow & Automation
| Module | What it does |
|--------|-------------|
| quality_bulk_actions | Bulk quality check operations |

### Reporting & Integration
| Module | What it does |
|--------|-------------|
| test_report | Database view model pattern (pivot/list/form, in `custom_addons/`) |
| orchida_uae_e_invoicing | UAE e-invoicing compliance |

### Utilities
| Module | What it does |
|--------|-------------|
| ept_execute_python_code | Secure Python execution within Odoo |
| extend_distribution_method | Distribution method extensions |

## Key Patterns

### Approval (used by all EPT modules)
```python
approval = self.env['approval.request'].create({
    'name': 'Description',
    'request_owner_id': self.env.user.id,
    'approver_ids': [(6, 0, approver_ids)],
    'category_id': category_id,
    'res_model': self._name,
    'res_id': self.id,
})
```

### n8n webhook pattern
Odoo controller sends HTTP POST to n8n webhook → n8n processes (Claude AI, transforms, etc.) → returns result to Odoo.

### Invoice change wizard pattern (purchase_extended_ept)
- Do not write directly to `account.move.name` for posted invoices when the goal is to adjust payment memo/reference.
- Keep sequence integrity by updating `payment_reference` (and vendor bill `ref` when needed) via wizard actions.
- Payment memo in `account.payment.register` uses `payment_reference or ref or name`, so this approach updates memo without overriding numbering.

## n8n Automation Skills

When the user asks about **n8n workflows, automation, or n8n-specific questions** (not Odoo model development), use these skills:

- **n8n-workflow-patterns** - Workflow architecture, webhooks, API integration patterns
- **n8n-code-javascript** - JavaScript Code nodes ($input, $json, $helpers syntax)
- **n8n-code-python** - Python Code nodes (_input, _json syntax)
- **n8n-expression-syntax** - Validate/fix {{}} expressions
- **n8n-node-configuration** - Configure HTTP Request, Database, Set nodes
- **n8n-validation-expert** - Troubleshoot validation errors
- **n8n-mcp-tools-expert** - Use n8n MCP tools (search nodes, validate workflows)

**Invoke these ONLY for n8n automation questions**, not when working on Odoo modules.

## Module Structure Template
```
module_name/
├── __init__.py
├── __manifest__.py        # version='18.0.1.0.0'
├── models/
├── views/
├── security/ir.model.access.csv
├── wizard/                # TransientModel for wizards
├── controllers/           # HTTP routes
└── data/
```

## Reference Docs
- `docs/ODOO_18_GUIDE.md` — Odoo 18 ORM, views, performance reference
- `docs/AI_REFERENCE.md` — AI integration patterns
- `MCP_DEVELOPMENT_GUIDE.md` — MCP tool development (FastMCP, Pydantic schemas, testing)
