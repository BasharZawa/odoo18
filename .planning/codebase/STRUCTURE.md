# Codebase Structure

**Analysis Date:** 2026-02-12

## Directory Layout

```
/home/bashar/odoo18/
├── odoo/                          # Odoo 18 Enterprise fork
│   ├── addons/                    # Standard Odoo modules (612+ modules)
│   ├── custom_addons/             # PRIMARY: 17 custom EPT/domain modules
│   └── ent_addons/                # Enterprise add-ons (localization, etc.)
├── custom_addons/                 # SECONDARY: 1 standalone module (test_report)
├── addons/                        # Additional third-party modules
├── docs/                          # Documentation and guides
├── mcp_dev/                       # MCP development and examples
├── .planning/                     # GSD planning documents
└── [Configuration & Docs]         # CLAUDE.md, README.md, etc.
```

## Directory Purposes

**`/home/bashar/odoo18/odoo/custom_addons/`** (Primary custom modules location)
- Purpose: Contains 17 production modules for Sales, Manufacturing, CRM, Finance
- Contains: Full-featured domain modules with models, views, security, data initialization
- Key modules:
  - `sale_extended_ept/` - Credit hold, approval integration
  - `sale_below_cost_approval_ept/` - Below-cost selling controls
  - `pilot_order_ept/` - Pilot order handling with change control
  - `discount_management_ept/` - Discount approval by job position
  - `quote_management/` - Quote lifecycle
  - `account_extended_ept/` - Invoice customization (Arabic, SEDCO templates)
  - `sales_reports_ept/` - Multi-type sales reporting
  - `customer_management_ept/` - Customer validation, invoicing/recognition/distribution schedules
  - `crm_extended_ept/` - Product model/nature fields for template-variant sync
  - `mrp_extended_ept/` - Work order costing, scrap tolerance, time tracking
  - `purchase_extended_ept/` - Purchase workflow
  - `stock_extended_ept/` - Picking, quant, lot enhancements
  - `vendor_tracking_ept/` - Vendor code generation and tracking
  - `quality_bulk_actions/` - Bulk quality check wizard
  - `orchida_uae_e_invoicing/` - UAE e-invoice compliance
  - `ept_execute_python_code/` - Secure code execution
  - `extend_distribution_method/` - Distribution method extensions

**`/home/bashar/odoo18/custom_addons/`** (Standalone modules)
- Purpose: Modules developed outside main codebase or POCs
- Contains:
  - `test_report/` - Example database view model (pivot/list/form pattern)

**`/home/bashar/odoo18/docs/`** (Documentation)
- Purpose: Developer guides and reference documentation
- Contains:
  - `ODOO_18_GUIDE.md` - ORM, views, performance reference
  - `AI_REFERENCE.md` - AI integration patterns
  - `plans/` - Sprint and action plans

**`/home/bashar/odoo18/mcp_dev/`** (MCP tooling)
- Purpose: MCP server development and tool creation
- Contains:
  - `examples/` - Example MCP tool implementations
  - MCP server code and schemas

**`/home/bashar/odoo18/.planning/codebase/`** (This directory)
- Purpose: GSD analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Used by: `/gsd:plan-phase` and `/gsd:execute-phase` orchestration

## Key File Locations

**Entry Points:**

- `odoo/custom_addons/{module}/__manifest__.py` - Module declaration (dependencies, data files, version)
- `odoo/custom_addons/{module}/__init__.py` - Module initialization (imports model classes)
- `odoo/custom_addons/{module}/models/__init__.py` - Model registration (imports all model files)

**Configuration:**

- `CLAUDE.md` - Development rules, patterns, and module overview (loaded every session)
- `MCP_DEVELOPMENT_GUIDE.md` - MCP tool development guide (FastMCP, Pydantic)
- `MCP_SERVER_README.md` - MCP server features and tool list
- `.env` - Environment variables (NOT committed - contains secrets)

**Core Logic:**

- `odoo/custom_addons/{module}/models/*.py` - Model definitions (`_inherit` based)
- `odoo/custom_addons/{module}/models/request_approval.py` - Approval request customizations
- `odoo/custom_addons/{module}/models/sale_order.py`, `res_partner.py`, etc. - Extended models

**User Interface:**

- `odoo/custom_addons/{module}/views/*.xml` - Form/list/kanban/pivot view definitions
- `odoo/custom_addons/{module}/static/src/js/` - Custom JavaScript
- `odoo/custom_addons/{module}/static/src/css/` - Custom styling

**API & Integration:**

- `odoo/custom_addons/{module}/controllers/*.py` - HTTP route handlers
- `odoo/custom_addons/{module}/controllers/controllers.py` - Main controller (entry point for routes)

**Testing & Fixtures:**

- `odoo/custom_addons/{module}/demo/demo.xml` - Demo data records
- `odoo/custom_addons/{module}/tests/` - Unit/integration tests (if present)

**Workflows & Automation:**

- `odoo/custom_addons/{module}/wizard/*.py` - TransientModel wizards for multi-step processes
- `odoo/custom_addons/{module}/wizard/*_views.xml` - Wizard form templates
- `odoo/custom_addons/{module}/data/ir_cron.xml` - Scheduled jobs
- `odoo/custom_addons/{module}/data/approval_category_data.xml` - Approval definitions

**Security & Access:**

- `odoo/custom_addons/{module}/security/ir.model.access.csv` - CRUD permissions by model and group
- `odoo/custom_addons/{module}/security/*.xml` - Security group definitions

**Reports:**

- `odoo/custom_addons/{module}/report/*.py` - Report model definitions (`_auto=False` views)
- `odoo/custom_addons/{module}/report/*.xml` - Report template definitions

## Naming Conventions

**Files:**

- Model files: snake_case matching model name (e.g., `sale_order.py` for `sale.order` inheritance)
- View files: `{model}_views.xml` or `{model}_{view_type}.xml` (e.g., `sale_order_views.xml`, `sale_order_form.xml`)
- Wizard files: `{action}_wizard.py` + `{action}_wizard_views.xml` (e.g., `sale_below_cost_wizard.py`)
- Report files: `{report_name}_report.xml` (e.g., `sale_report.xml`)
- Transient models: `{action}_{transient}.py` (e.g., `e_invoice_setting.py` for TransientModel config)

**Directories:**

- `models/` - All model classes
- `views/` - All view definitions
- `controllers/` - HTTP route handlers
- `wizard/` - TransientModel wizards
- `report/` - Report definitions (both model and template XML)
- `security/` - Access control and group definitions
- `data/` - Initial data records (sequences, approval categories, CRON, groups)
- `demo/` - Demo/test fixtures
- `static/src/` - Frontend assets (js, css, xml templates)

**Modules:**

- `*_extended_ept` - Extends standard Odoo module (e.g., `sale_extended_ept` extends `sale_management`)
- `*_management_ept` - Adds new management features (e.g., `customer_management_ept` for customer workflow)
- `*_ept` - General EPT-authored utility (e.g., `ept_execute_python_code`)
- `sedco_*` (not in current codebase) - Company-specific SEDCO modules
- Standard name - Third-party or POC modules (e.g., `test_report`)

## Where to Add New Code

**New Sales/Finance Feature:**
- Primary code: `odoo/custom_addons/sale_extended_ept/models/{model_name}.py`
- Tests: Create `odoo/custom_addons/sale_extended_ept/tests/test_{model}.py`
- Views: `odoo/custom_addons/sale_extended_ept/views/{model}_views.xml`
- Add to manifest: `odoo/custom_addons/sale_extended_ept/__manifest__.py` → `data` list

**New CRM/Vendor Feature:**
- Primary code: `odoo/custom_addons/customer_management_ept/models/{model_name}.py` (if customer-related) or `vendor_tracking_ept/models/{model}.py` (if vendor-related)
- Tests: `odoo/custom_addons/{module}/tests/test_{model}.py`
- Views: `odoo/custom_addons/{module}/views/{model}_views.xml`

**New Manufacturing Feature:**
- Primary code: `odoo/custom_addons/mrp_extended_ept/models/{model_name}.py`
- Views: `odoo/custom_addons/mrp_extended_ept/views/{model}_views.xml`
- Tests: `odoo/custom_addons/mrp_extended_ept/tests/test_{model}.py`

**New Approval Workflow:**
- Approval category: `odoo/custom_addons/{target_module}/data/approval_category_data.xml` (add `<record model="approval.category">`)
- Approval trigger: In model's `action_*()` or `write()` method, call `self._create_approval_request()`
- Example: See `sale_extended_ept/models/sale_order.py` line ~200 for pattern

**New Wizard/Dialog:**
- File: `odoo/custom_addons/{module}/wizard/{action}_wizard.py` (TransientModel class)
- Form: `odoo/custom_addons/{module}/wizard/{action}_wizard_views.xml`
- Button: Add to target model view with `type="object"` action pointing to method on wizard
- Example: See `sale_below_cost_approval_ept/wizard/sale_below_cost_wizard.py`

**New Report:**
- SQL View Model: `odoo/custom_addons/{module}/report/{report_name}.py` (use `_auto=False`, `init()` method)
- View Template: `odoo/custom_addons/{module}/report/{report_name}_views.xml` (list/pivot/form)
- Example: See `custom_addons/test_report/models/test_report.py`

**New API Endpoint:**
- File: `odoo/custom_addons/{module}/controllers/controllers.py`
- Route: Add `@http.route('/path/to/endpoint', auth='user')` decorated method
- Example: See `quality_bulk_actions/controllers/controllers.py` (commented-out example)

**New Utility Function:**
- Shared helpers: `odoo/custom_addons/{module}/models/helpers.py` (import in `__init__.py`)
- Or add as classmethod/staticmethod in relevant model

**New Scheduled Job (CRON):**
- File: `odoo/custom_addons/{module}/data/ir_cron.xml`
- Method: Add `def _scheduled_*()` in relevant model
- Example: See `vendor_tracking_ept/data/ir_cron_data.xml`

## Special Directories

**`/home/bashar/odoo18/addons/`:**
- Purpose: Third-party modules (hr_org_chart, spreadsheet modules, localization)
- Generated: No (pre-installed Odoo modules)
- Committed: Yes (part of official Odoo)

**`/home/bashar/odoo18/deprecated/`:**
- Purpose: Old/removed modules (no longer active)
- Generated: No (historical)
- Committed: Yes (for reference)

**`/home/bashar/odoo18/.planning/codebase/`:**
- Purpose: GSD analysis documents
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes (for team reference, updated regularly)

**`/home/bashar/odoo18/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (Python interpreter)
- Committed: No (.gitignore excludes)

---

*Structure analysis: 2026-02-12*
