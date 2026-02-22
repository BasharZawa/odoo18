# Architecture

**Analysis Date:** 2026-02-12

## Pattern Overview

**Overall:** Modular extension pattern layered on Odoo 18 Enterprise framework with inheritance-based customization, separation of concerns via dedicated feature modules, and cross-module integration through approval workflow orchestration.

**Key Characteristics:**
- **Inheritance-first design**: All custom logic extends Odoo base models via `_inherit` rather than creating standalone models
- **Separation of business domains**: Individual modules handle Sales, Manufacturing, CRM, Accounting independently
- **Centralized approval system**: All workflow decisions delegate to `approval.request` (no custom approval models)
- **Data integrity through validation**: TransientModel wizards validate and collect data before persistence
- **Report models as computed views**: Read-only SQL-backed models (`_auto=False`) for analytics

## Layers

**Presentation Layer:**
- Purpose: User interface and form/view interactions
- Location: `*/views/`, `*/static/src/`
- Contains: XML form/list/kanban/pivot views, static JS/CSS assets, wizard templates
- Depends on: Models (via ORM), security groups
- Used by: Frontend, API controllers

**Business Logic Layer:**
- Purpose: Core domain logic, state machines, validations, workflows
- Location: `*/models/`
- Contains: Model classes with `_inherit` (SaleOrder, ResPartner, PurchaseOrder, etc.), computed fields, state transitions
- Depends on: Base Odoo models, other custom models via ForeignKey/Many2one
- Used by: Controllers, wizards, reports, CRON jobs

**API & Integration Layer:**
- Purpose: HTTP endpoints, webhook receivers, external service connectors
- Location: `*/controllers/`
- Contains: HTTP routes (via `@http.route`), request validation, response formatting
- Depends on: Models, services
- Used by: External systems, n8n workflows, frontend JavaScript

**Data Persistence & Initialization:**
- Purpose: Initial data, security rules, sequences, approval category definitions
- Location: `*/data/*.xml`, `*/security/`, `*/demo/`
- Contains: Records for `approval.category`, sequences (ir_sequence), security groups, demo fixtures
- Depends on: None (initialization layer)
- Used by: Module installation, runtime lookups

**Transient/Wizard Layer:**
- Purpose: Multi-step workflows, approval dialogs, data collection before action
- Location: `*/wizard/`
- Contains: TransientModel classes with form collection, action buttons, validation
- Depends on: Models, approval system
- Used by: Button clicks, backend workflows

## Data Flow

**Sales Order Approval Workflow:**

1. User creates sale order with credit-limited customer
2. `SaleOrder.action_confirm()` invoked → checks customer credit (via `sale_extended_ept`)
3. If overdue invoices exist → order state set to `on_hold` (custom state added)
4. `_create_approval_request()` method called → creates `approval.request` record
5. Approval request triggers notification to Finance users (configurable approver_ids)
6. Approver approves via UI → `ApprovalRequestEPT.action_approve()` override fires
7. Override automatically transitions order from `on_hold` → `draft` → `confirmed` via `action_confirm()`
8. Order proceeds to fulfillment

**Customer Validation → Sales Blocking:**

1. New customer contact created in `res.partner`
2. `ResPartner` record inherits custom validation fields (customer_management_ept)
3. Finance team reviews and approves via approval workflow
4. Once approved, sales orders are allowed (check in order_line prevents unvalidated customer sales)
5. Validation status cached on partner record for quick lookup

**Reporting Flow:**

1. Reports defined in `*/report/` as SQL views (via `_auto=False`)
2. `init()` method drops and recreates SQL view on module install/upgrade
3. View joins transactional tables (sale_order, sale_order_line, res_partner, account_move)
4. UI loads report model as read-only pivot/list view
5. Filters apply to WHERE clause; aggregations handled in SQL

## Key Abstractions

**Approval Request Extension (ApprovalRequestEPT):**
- Purpose: Wraps Odoo's built-in `approval.request` to trigger automatic state transitions
- Examples: `sale_extended_ept/models/request_approval.py`
- Pattern: Override `action_approve()` to execute post-approval logic (e.g., confirm order, unlock fields)

**Model Extension via _inherit:**
- Purpose: Add fields and methods to base Odoo models without breaking standard behavior
- Examples:
  - `sale_extended_ept/models/sale_order.py` → extends `sale.order` with `on_hold` state and credit checks
  - `customer_management_ept/models/res_partner.py` → extends `res.partner` with validation workflow
  - `account_extended_ept/models/account_move.py` → extends `account.move` for invoice templating
- Pattern: `_inherit = "base.model.name"` + add fields and override/extend methods

**Wizard Pattern (TransientModel):**
- Purpose: Collect and validate multi-step inputs before persisting main record
- Examples: `sale_below_cost_approval_ept/wizard/sale_below_cost_wizard.py`
- Pattern: `models.TransientModel` with `Html` field for display, `default_get()` for population, button handlers for submission

**Report Model Pattern (_auto=False):**
- Purpose: Create computed analytics views without duplicating data
- Examples: `custom_addons/test_report/models/test_report.py`
- Pattern: `_auto=False`, `_rec_name` set to key field, `init()` method with `tools.drop_view_if_exists()` and `CREATE OR REPLACE VIEW`

**Security & Access Control:**
- Purpose: Restrict visibility/modification based on user groups
- Location: `*/security/ir.model.access.csv` (CRUD on models), `*.xml` group definitions
- Pattern: `ir.model.access` records link model name to group with create/read/write/delete flags

## Entry Points

**Module Installation:**
- Location: `__manifest__.py` (manifest declaration)
- Triggers: Module installation via Odoo UI or `odoo-bin -i module_name`
- Responsibilities: Define dependencies, data files to load, views to register

**Model Initialization:**
- Location: `models/__init__.py`
- Triggers: Python import when module loaded into Odoo
- Responsibilities: Import all model classes so ORM can register them

**HTTP API Endpoints:**
- Location: `*/controllers/controllers.py`
- Triggers: HTTP GET/POST to defined route (e.g., `/test_report/list`)
- Responsibilities: Parse request, call model methods, return JSON/HTML response

**CRON Jobs:**
- Location: `*/data/ir_cron.xml`
- Triggers: Scheduled execution (e.g., every hour, daily at midnight)
- Responsibilities: Call model method to perform background task (cleanup, sync, notifications)

**ORM Hooks:**
- Triggers: Database operations (create, write, unlink)
- Methods: `create()`, `write()`, `unlink()`, `_get_display_name()`
- Responsibilities: Validation, side effects (approval creation, notifications, state transitions)

## Error Handling

**Strategy:** Exceptions bubble to UI as user-facing error messages via `raise UserError()` or `ValidationError()`.

**Patterns:**
- `UserError` - User-actionable errors (e.g., "Customer has overdue invoices")
- `ValidationError` - Data constraint violations (e.g., "Product code is not unique")
- `AccessError` - Raised by security layer when user lacks permission
- `MissingError` - Record not found (e.g., trying to access deleted partner)

**Example from `sale_extended_ept`:**
```python
if customer_has_overdue_invoices:
    order.write({'state': 'on_hold'})
    raise UserError(_("Order placed on hold. Credit limit exceeded."))
```

## Cross-Cutting Concerns

**Logging:** Uses Python's `logging` module. Debug/info calls appear in Odoo logs (`/var/log/odoo/odoo.log`). Structured logging via `_logger.info()`.

**Validation:**
- Model-level: `_sql_constraints` (database constraints), `@api.constrains` (Python constraints)
- Form-level: `required=True`, field validators via `_check_*()` methods
- Workflow-level: State machine transitions guard illegal state changes

**Authentication:** Inherits Odoo session management. `self.env.user` gives current user. `sudo()` bypasses ACLs for internal operations. Role-based via security groups in `ir.model.access.csv`.

**Authorization:** Field-level visibility via `groups=` attribute. Model access via CRUD bits in `ir.model.access.csv`. Record-level via domain filters in views.

**Caching:** Odoo caches ORM records in memory within request. Invalidated on write/unlink. SQL views (report models) auto-cache as long as source tables unchanged.

---

*Architecture analysis: 2026-02-12*
