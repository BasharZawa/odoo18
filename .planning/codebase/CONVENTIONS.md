# Coding Conventions

**Analysis Date:** 2026-02-12

## Naming Patterns

**Files:**
- Module folders: lowercase with underscores: `sale_extended_ept`, `discount_management_ept`, `stock_extended_ept`
- Model files: snake_case matching the model name: `sale_order.py`, `mrp_workorder.py`, `res_partner.py`
- EPT modules use suffixes consistently: `*_extended_ept` (extends standard module), `*_management_ept` (new features), `sedco_*` (company-specific)

**Functions:**
- Private methods: prefixed with underscore: `_compute_credit_available()`, `_create_approval_request()`, `_get_overdue_invoices_domain()`
- Computed field methods: `_compute_*`: `_compute_credit_overdue_amount()`, `_compute_schedule_date_finished()`, `_compute_below_cost()`
- Action/wizard methods: start with `action_`: `action_confirm()`, `action_validate_customer()`, `action_download_packing_slip_xlsx_report()`
- Helper/internal methods: `_get_*`, `_prepare_*`, `_handle_*`, `_set_*`

**Variables:**
- camelCase for instance variables: `line_disc_prod`, `man_order_form`, `category_id`
- snake_case for function parameters and local variables: `product_type`, `partner_id`, `approval_request`
- Constants/field names: UPPERCASE in rare cases; mostly snake_case: `company_id`, `currency_id`, `order_id`

**Types/Models:**
- Model inheritance class names: descriptive with "Extended" suffix: `SaleOrderExtended`, `MrpWorkorderExtended`, `StockQuantExtend`
- Transient models (wizards): `NameWizard` or `NameTransient`: `SaleBelowCostWizard`

## Code Style

**Formatting:**
- UTF-8 encoding with `# -*- coding: utf-8 -*-` header (present in most files)
- Line length: Not explicitly constrained but follows Odoo convention (typically 100-120 chars observed)
- Indentation: 4 spaces (Python standard)
- Import statements: grouped at top of file

**Linting:**
- flake8 configuration present in `setup.cfg`
- Extended select includes RST directives for documentation
- No explicit per-module linting config

**Field Definitions:**
- Multi-line field declarations with consistent indentation:
  ```python
  credit_overdue_amount = fields.Monetary(
      string="Overdue Amount",
      currency_field="currency_id",
      compute="_compute_credit_overdue_amount",
      store=False,
  )
  ```
- String labels in `string=` parameter with proper capitalization
- Help text in `help=` parameter for clarity

## Import Organization

**Order:**
1. Standard library imports: `from datetime import date`, `import io`, `import base64`
2. Third-party libraries: `from openpyxl.styles import Font`, `from freezegun import freeze_time`
3. Odoo imports: `from odoo import fields, models, api, _`
4. Odoo exceptions: `from odoo.exceptions import UserError, ValidationError`
5. Odoo tools: `from odoo.tools import float_compare, float_is_zero`
6. Local imports: `from . import model_name`

**Path Aliases:**
- No explicit path aliases detected; direct imports from `odoo` package used throughout
- Relative imports in `__init__.py`: `from . import mrp_workorder`, `from . import stock_scrap`

## Error Handling

**Patterns:**
- Exceptions are raised with internationalization: `raise UserError(_("Message text"))`
- Two main exception types used:
  - `UserError`: For user-facing validation and business rule violations
  - `ValidationError`: For constraint violations and invalid data states
- Example from `sale_extended_ept/models/sale_order.py`:
  ```python
  if not self.approval_request_id:
      raise UserError(_("No approval request found for this order."))
  ```
- Example from `customer_management_ept/models/res_partner.py`:
  ```python
  if not self.country_id:
      raise UserError("Partner Country is not set.")
  ```

**No Try-Catch Blocks:**
- Errors are not caught in custom code; Odoo framework handles exception propagation
- Validation happens upfront with `ensure_one()` calls before operations

## Logging

**Framework:** console logging via `_logger` (not explicitly configured in custom modules)

**Patterns:**
- Not heavily used in custom addons; business events logged via chatter/message_post instead
- Example from `sale_extended_ept/models/sale_order.py`:
  ```python
  order.message_post(
      body=_("Order placed On Hold due to %s. Approval request has been created.") % reason_text,
      subtype_xmlid="mail.mt_note",
  )
  ```

## Comments

**When to Comment:**
- Sparse commenting; code is expected to be self-documenting via method names
- Explanatory comments for non-obvious logic (e.g., database compatibility notes in `sale_extended_ept/models/sale_order.py`):
  ```python
  # NOTE: Removed invoice_policy override with company_dependent=True as it causes
  # database column type conflicts (varchar -> jsonb conversion fails with existing data).
  ```
- Commented-out code blocks left in place (indicates evolving requirements):
  ```python
  # category = self.env.ref("sale_extended_ept.approval_category_sale_order_credit_hold")
  ```

**JSDoc/TSDoc:**
- Docstrings used for methods with complex logic:
  ```python
  def _compute_invoice_status(self):
      """
      Compute the invoice status of a SO line. Possible statuses:
      - no: if the SO is not in status 'sale'...
      - to invoice: ...
      """
  ```
- Docstrings follow PEP 257 convention (triple quotes, descriptive first line)
- Return value documentation: `return: None` or implicit if obvious

## Function Design

**Size:**
- Methods vary from 3-50 lines; preference for smaller, focused methods
- Compute methods typically 5-15 lines
- Action methods (wizards, confirmations) 20-40 lines

**Parameters:**
- `self` only for instance methods; class context (self.env, self.company_id) heavily used
- No *args/**kwargs patterns observed
- Keyword-only arguments used in Odoo API: `fields.Date.today()`, `self.env['model.name'].search([...], limit=1)`

**Return Values:**
- Model methods return `self` (for chaining) or action dictionaries for UI navigation:
  ```python
  return {
      "type": "ir.actions.act_window",
      "name": _("Approval Request"),
      "res_model": "approval.request",
      "res_id": self.approval_request_id.id,
      "view_mode": "form",
      "target": "new",
  }
  ```
- Compute methods return implicit (field assignment via `=`)
- Action buttons return action dicts or `True`/`False` for success/failure

## Module Design

**Exports:**
- No explicit `__all__` declarations; all models in `models/__init__.py` are imported:
  ```python
  from . import mrp_workorder
  from . import stock_scrap
  from . import sale_order
  from . import request_approval
  ```
- Non-exported models commented out with explanation (e.g., approval_category, approval_request)

**Barrel Files:**
- `__init__.py` in models/ imports submodules; ORM discovers models automatically
- Controllers/ and wizards/ follow same pattern

**Dependency Management:**
- EPT modules declare dependencies in `__manifest__.py`:
  ```python
  "depends": [
      "product",
      "sale_management",
      "account",
      "approvals",
      "stock_account"
  ],
  ```
- Heavy reliance on `approvals` module for all workflow functionality
- No circular dependencies detected

## Computed Fields Pattern

**Standard pattern across codebase:**
- Use `@api.depends()` decorator for dependency declaration
- Loop through records: `for rec in self:` or `for order in self:`
- Assign directly: `rec.field_name = computed_value`
- Multi-step computation delegated to helper methods: `_get_incoming_data()`, `_get_outgoing_data()`

Example from `mrp_extended_ept/models/mrp_workorder.py`:
```python
@api.depends('date_start', 'duration_expected')
def _compute_schedule_date_finished(self):
    for rec in self:
        if rec.duration_expected and rec.date_start:
            rec.schedule_date_finished = rec.date_start + timedelta(minutes=rec.duration_expected)
        else:
            rec.schedule_date_finished = False
```

## Approval Pattern

**Centralized pattern used by all EPT modules:**
- Search for approval category: `self.env['approval.category'].search([('approval_type', '=', 'type_name'), ...], limit=1)`
- Create approval request: `self.env["approval.request"].sudo().create({...})`
- Call confirmation: `approval_request.sudo().action_confirm()`
- Link back to source model via `sale_order_id`, `stock_quant_product_id`, etc.

Example from `sale_extended_ept/models/sale_order.py`:
```python
approval_request = self.env["approval.request"].sudo().create({
    "name": f"Credit Hold Approval - {self.name}",
    "category_id": category.id,
    "request_owner_id": self.user_id.id,
    "date": fields.Date.today(),
    "amount": self.amount_total,
    "partner_id": self.partner_id.id,
    "reference": self.name,
    "sale_order_id": self.id,
    "request_status": "new",
    "is_credit_req": True,
})
approval_request.sudo().action_confirm()
```

## Internationalization

**Pattern:**
- All user-facing strings wrapped in `_()` function: `_("Message")`, `_("Only orders on hold can resubmit approval.")`
- Used consistently in error messages, button labels, and log messages
- String formatting with `%` operator: `_("Credit Hold Approval - %s") % order.name`

## Security

**Groups and Permissions:**
- Referenced via group variables: `self.env.user.has_group('group_name')`
- Security rules in `security/ir.model.access.csv` files
- Most operations use `sudo()` for approval workflows: `self.env['approval.request'].sudo().create({...})`

---

*Convention analysis: 2026-02-12*
