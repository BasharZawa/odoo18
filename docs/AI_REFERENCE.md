# AI Reference (Odoo 18 Workspace)

**Purpose**: A single, consolidated reference for this workspace that captures the key constraints and patterns from:
- [docs/ODOO_18_GUIDE.md](docs/ODOO_18_GUIDE.md)
- [.github/copilot-instructions.md](../.github/copilot-instructions.md)
- [.github/agents/odoo.agent.md](../.github/agents/odoo.agent.md)

This document is written to be short, operational, and easy to scan during implementation work.

---

## 1) Non‑Negotiables (Enterprise Odoo 18)

- Assume **Odoo 18.0 Enterprise** patterns/APIs.
- Prefer upgrade-safe extension patterns; avoid hacks/monkey-patching.
- Respect ORM semantics, access rights, record rules, multi-company and multi-currency.
- Avoid `sudo()` unless there is a clear, documented business/security justification.
- Do not reference removed legacy models (e.g., `account.invoice`); use `account.move`.

---

## 2) Project Layout (Custom Modules)

Custom work typically lives in `custom_addons/custom_addons/` and `custom_addons/ent_addons/` via the external `custom_addons` submodule.

Required module structure pattern:

```
module_name/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── *.py
├── views/
│   └── *.xml
├── security/
│   └── ir.model.access.csv   # REQUIRED when adding new models
└── data/
    └── *.xml
```

---

## 3) ORM & Model Patterns

### Extend existing models (most common)

```python
from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = "crm.lead"

    custom_field = fields.Char("Custom Field")
```

### New models

```python
from odoo import models, fields

class ProductLine(models.Model):
    _name = "product.line.ept"
    _description = "Product Line"

    name = fields.Char(required=True)
```

### Decorators & overrides (v18 guidance)

- Computed fields: use `@api.depends(...)`; set `store=True` when you need search/grouping/perf.
- Editable computed fields: provide `inverse` when appropriate.
- Onchanges: only for UI convenience (not persistence).
- Constraints: use `@api.constrains(...)` for data integrity.
- Create override: use `@api.model_create_multi` for performance.

---

## 4) Views (XML) — Upgrade-safe inheritance

- Prefer view inheritance via XPath, minimal and targeted.
- Use clear XPath expressions and avoid long inheritance chains.

Example:

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

---

## 5) Security — Always think access first

- New models require `security/ir.model.access.csv`.
- Consider record rules (`ir.rule`) for row-level security.
- Avoid `sudo()` by default; prefer `with_user()` / correct groups/rules.

CSV format:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_product_line_user,product.line.user,model_product_line,base.group_user,1,1,1,0
```

---

## 6) Accounting (Key v18 architecture reminders)

- Invoices/bills/journal entries are `account.move` with `move_type`.
- **Payments are not linked by FK to invoices**; reconciliation happens through receivable/payable lines via `account.partial.reconcile`.

Reconcile approach:

```python
(invoice_receivable + payment_receivable).reconcile()
```

- Analytic: legacy `analytic_account_id` is removed from line models; use `analytic_distribution` (JSON dict of stringified IDs → percentages).

---

## 7) Web / OWL (Odoo 18)

- Odoo 18 uses OWL 2.
- Register components/widgets/actions through `registry` categories.
- Keep UI logic separate from business logic.

---

## 8) Working Style Expectations (Architect-level)

When implementing or reviewing changes:
- Explain *why* the chosen approach fits Odoo 18 patterns.
- Call out trade-offs when relevant.
- Mention performance/security implications.
- Highlight impacts on: data model, workflows, reporting, accounting, upgrade path.

---

## 9) How to Use This Reference

- Use this file as the “quick rules” checklist.
- For deeper detail, refer to:
  - Odoo technical guide: [docs/ODOO_18_GUIDE.md](docs/ODOO_18_GUIDE.md)
  - Workspace agent rules: [.github/agents/odoo.agent.md](../.github/agents/odoo.agent.md)
  - Repo Copilot rules: [.github/copilot-instructions.md](../.github/copilot-instructions.md)
