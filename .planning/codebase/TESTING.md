# Testing Patterns

**Analysis Date:** 2026-02-12

## Test Framework

**Runner:**
- Odoo built-in test runner (via `odoo.tests`)
- Framework: pytest-compatible through Odoo's test utilities
- No explicit test framework config (setup.cfg has no pytest section)

**Assertion Library:**
- `odoo.tests` module: `Form`, `users`, `HttpCase`, `tagged`
- Standard Python `unittest.TestCase` assertions: `assertEqual()`, `assertAlmostEqual()`, `assertTrue()`, `assertFalse()`

**Run Commands:**
```bash
# Custom addons have NO tests defined
# Standard Odoo tests (for reference in /addons):
python -m odoo --test-enable -d OdooE
python -m odoo -d OdooE -i sale_extended_ept --test-enable
```

## Test File Organization

**Location:**
- Custom addons (`odoo/custom_addons/`): No test files present
- Standard Odoo addons (`addons/`): Tests in `tests/` directory
- Pattern: co-located with models but in separate `tests/` subdirectory

**Naming:**
- Test files: `test_*.py`
- Test classes: `TestXxxYyy` (e.g., `TestMrpOrder`, `TestMrpCommon`)

**Structure:**
```
module_name/
├── models/
│   └── *.py
├── tests/
│   ├── __init__.py              # Imports all test modules
│   ├── test_basic.py
│   ├── test_workflow.py
│   └── common.py                # Shared fixtures and base classes
└── views/
```

## Test Structure

**Suite Organization** (from `addons/mrp/tests/test_order.py`):
```python
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, users
from odoo.tests.common import HttpCase, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon

class TestMrpOrder(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Class-level setup
        cls.env.ref('base.group_user').write({...})

    def test_access_rights_manager(self):
        """Checks an MRP manager can create, confirm and cancel a manufacturing order."""
        man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_manager))
        man_order_form.product_id = self.product_4
        man_order_form.product_qty = 5.0
        man_order = man_order_form.save()
        man_order.action_confirm()
        self.assertEqual(man_order.state, 'cancel', "Production order should be in cancel state.")
```

**Patterns:**
- Inherit from common test class with shared fixtures: `class TestXxx(TestMrpCommon):`
- `setUpClass()`: Class-level initialization for expensive operations
- Method names: `test_<scenario>()` with descriptive verbs
- Docstrings: One-sentence description of what test validates
- Assertions include failure message: `assertEqual(actual, expected, "Human-readable message")`

## Mocking

**Framework:** Odoo's built-in record mocking via `Form` and user context

**Patterns** (from `addons/mrp/tests/test_order.py`):
```python
# Create test records via Form API
man_order_form = Form(self.env['mrp.production'].with_user(self.user_mrp_manager))
man_order_form.product_id = self.product_4
man_order_form.product_qty = 5.0
man_order = man_order_form.save()

# User context isolation
with_user(user_obj)
without_context(...)
with_context(context_key=value)
```

**What to Mock:**
- User context: `.with_user(user_obj)` for permission testing
- Company context: `.with_company(company_id)` for multi-company scenarios
- Records: Create actual test records via ORM (not mocking)

**What NOT to Mock:**
- Database operations: Tests use real database
- Model methods: Test actual implementations
- External APIs: Tests do NOT call real APIs (but no API calls in custom addons observed)

## Fixtures and Factories

**Test Data** (from `addons/mrp/tests/common.py`):
- Common base class pattern: `class TestMrpCommon(TransactionCase):`
- Shared models: `cls.product_1`, `cls.product_2`, `cls.bom_1`, `cls.warehouse_1`
- User fixtures: `cls.user_mrp_manager`, `cls.user_mrp_user`
- Initialized in `setUpClass()` for performance

Pattern:
```python
class TestMrpCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_4 = cls.env['product.product'].create({
            'name': 'Product 4',
            'is_storable': True,
        })
        cls.bom_1 = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_4.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {...})],
        })
```

**Location:**
- `tests/common.py` for shared fixtures
- `tests/__init__.py` imports all test modules

## Coverage

**Requirements:**
- Not enforced at codebase level
- No coverage configuration in `setup.cfg` or pytest config

**View Coverage:**
- Tests run with `odoo --test-enable` flag
- No explicit coverage report command observed

## Test Types

**Unit Tests:**
- Scope: Individual model methods and computed fields
- Approach: Create minimal records, call method, assert field values
- Example: Verify `_compute_schedule_date_finished()` calculates correct datetime
- Location: `test_*.py` in `tests/` directory

**Integration Tests:**
- Scope: Model interactions, workflows, state transitions
- Approach: Create complete order/production with components, execute workflow, verify cascading changes
- Example: Create MRP production order, confirm, partially produce, handle backorder
- Transactions: Tests run in database transactions and roll back after completion

**E2E Tests:**
- Framework: `HttpCase` for browser-based testing
- Not used in custom addons; standard Odoo has `@tagged('post_install', 'at_install')` tests
- Would test full UI workflows if present

## Common Patterns

**Async Testing:**
- Not applicable; Odoo uses synchronous request handling
- Cron jobs tested via direct method calls: `model._action_cron_method()`

**Error Testing**:
```python
from odoo.exceptions import UserError, ValidationError

def test_error_case(self):
    """Verify error raised when condition met"""
    product = self.env['product.product'].create({'name': 'Test'})
    with self.assertRaises(UserError):
        product.action_that_raises()
```

**Form-based Testing:**
```python
# Test through the UI form API
sale_form = Form(self.env['sale.order'])
sale_form.partner_id = self.partner
sale_form.order_line.add()
sale_form.order_line[0].product_id = self.product
order = sale_form.save()
self.assertEqual(order.state, 'draft')
```

**Command Usage for M2M Fields:**
```python
# From odoo import Command
record.write({
    'line_ids': [
        Command.create({'name': 'New line'}),
        Command.update(existing_id, {'value': 10}),
        Command.delete(other_id),
        Command.unlink(third_id),
    ]
})
```

## Custom Addons Testing Status

**No Tests in Custom Modules:**
- `odoo/custom_addons/` contains zero test files
- All modules are production-only without test coverage
- Implications:
  - Approval workflows not tested: `sale_extended_ept`, `discount_management_ept`, `stock_extended_ept`
  - Computed fields not validated: `mrp_extended_ept`, `customer_management_ept`
  - Wizard logic untested: `sale_below_cost_approval_ept`, `pilot_order_ept`

## How to Add Tests

**Template for new test file:**
```python
# odoo/custom_addons/module_name/tests/test_workflows.py
# -*- coding: utf-8 -*-

from odoo.tests import Form, users, TransactionCase
from odoo.exceptions import UserError, ValidationError

class TestModuleWorkflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'country_id': cls.env.ref('base.us').id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'standard_price': 50.0,
        })

    def test_sale_order_approval_creation(self):
        """Verify approval request created when credit limit exceeded"""
        # Create test data
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'price_unit': 100.0,
            })],
        })

        # Execute action
        sale_order.action_confirm()

        # Assert state
        self.assertEqual(sale_order.state, 'on_hold')
        self.assertTrue(sale_order.approval_request_id)
```

**Add to module `__init__.py`:**
```python
# __init__.py in tests/
from . import test_workflows
```

**Declare in `__manifest__.py`:**
```python
{
    'name': 'Module Name',
    'tests': [
        'tests.test_workflows',
    ],
}
```

---

*Testing analysis: 2026-02-12*
