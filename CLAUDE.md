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

## Custom Modules (30 total in `odoo/custom_addons/`)

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
| custom_crm | CRM customizations |
| crm_extended_ept | Model number, product line, product nature fields (template-variant sync) |
| sedco_crm | SEDCO-specific CRM features |
| sedco_crm_assignment_domain_bridge | Domain-based lead/opportunity assignment |
| custom_partner_city | City-related partner features |
| customer_import_helper | Customer data import utilities |

### Workflow & Automation
| Module | What it does |
|--------|-------------|
| **sedco_bpm_engine** | BPMN visual editor (bpmn-js), JSON compilation, runtime orchestration, parallel/sequential execution. **Use for internal workflows.** |
| quality_bulk_actions | Bulk quality check operations |

### Reporting & Integration
| Module | What it does |
|--------|-------------|
| **smart_report_builder** | Claude AI + n8n integration for dynamic reports. **Reference implementation for n8n patterns.** |
| test_report | Database view model pattern (pivot/list/form) |
| custom_apis | HTTP routes and API endpoints |
| orchida_uae_e_invoicing | UAE e-invoicing compliance |

### Utilities
| Module | What it does |
|--------|-------------|
| todo_app | Task management |
| ept_execute_python_code | Secure Python execution within Odoo |
| extend_distribution_method | Distribution method extensions |
| presales_requests | Pre-sales request management |
| request | Base request model used by other modules |
| sedco_management | General SEDCO management features |

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

### When to use n8n vs BPM
- **n8n** → external APIs, AI processing, email automation, multi-service orchestration. Reference: `smart_report_builder`
- **sedco_bpm_engine** → internal Odoo workflows, visual BPMN design, approval chains

### n8n webhook pattern
Odoo controller sends HTTP POST to n8n webhook → n8n processes (Claude AI, transforms, etc.) → returns result to Odoo. See `smart_report_builder/controllers/` for implementation.

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
