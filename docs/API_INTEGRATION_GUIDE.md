# Sales Order API Integration Guide

**Purpose:** Create sale orders in Odoo 18 (odoo.sh) from the legacy web app.

---

## 1. Authentication

Use **API Keys** — not user passwords. API keys don't expire with password changes and are scoped per user.

**Setup on odoo.sh:**
1. Create a dedicated user (e.g., `api-integration@sedco.com`) with the **Sales / User** role
2. Log in as that user → Settings → API Keys → New API Key
3. Store the key securely in your web app config — treat it like a password

**Authenticate via XML-RPC:**
```
POST https://<instance>.odoo.sh/xmlrpc/2/common
Call: authenticate(db, "api-integration@sedco.com", "<API_KEY>", {})
Returns: uid (integer)
```

**Or via JSON-RPC:**
```json
POST https://<instance>.odoo.sh/jsonrpc
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "service": "common",
    "method": "authenticate",
    "args": ["<db>", "api-integration@sedco.com", "<API_KEY>", {}]
  }
}
```

> Cache the `uid` — you don't need to authenticate on every request.

---

## 2. Prerequisites: Master Data Must Exist First

Before creating orders, the referenced records **must already exist** in Odoo.

| Data | Odoo Model | How to Resolve |
|------|-----------|----------------|
| Customer | `res.partner` | Search by VAT/name, or sync customers first |
| Product | `product.product` | Search by `default_code` (internal reference) |
| Pricelist | `product.pricelist` | Search by name or use customer's default |
| Salesperson | `res.users` | Search by email |

**Recommended approach:** Before creating an order, call `search_read` to resolve IDs:

```
# Find customer by VAT number
models.execute_kw(db, uid, key, "res.partner", "search_read",
    [[["vat", "=", "AE123456789"]]],
    {"fields": ["id", "name", "property_product_pricelist"], "limit": 1}
)

# Find product by internal reference (SKU)
models.execute_kw(db, uid, key, "product.product", "search_read",
    [[["default_code", "=", "PROD-001"]]],
    {"fields": ["id", "name", "list_price"], "limit": 1}
)
```

If a customer or product is not found, **stop and log the error** — do not create partial orders.

---

## 3. Creating a Sale Order

### 3a. Create as Draft (Recommended)

```python
order_id = models.execute_kw(db, uid, key, "sale.order", "create", [{
    "partner_id": 42,                          # REQUIRED - customer ID
    "client_order_ref": "LEGACY-SO-20260001",  # YOUR external reference (for dedup)
    "date_order": "2026-02-22 10:30:00",       # Order date from legacy system
    "user_id": 15,                             # Salesperson (Odoo user ID)
    "order_line": [
        (0, 0, {
            "product_id": 101,
            "product_uom_qty": 5,
            "price_unit": 150.00,              # Explicit price from legacy
            "discount": 10.0,                  # Discount percentage if any
        }),
        (0, 0, {
            "product_id": 205,
            "product_uom_qty": 2,
            "price_unit": 300.00,
        }),
    ],
}])
```

The order is created in **"draft"** state. A salesperson reviews and confirms it in Odoo.

### 3b. If You Need Auto-Confirmation (Use With Caution)

```python
# Step 1: Create the order (same as above)
order_id = models.execute_kw(db, uid, key, "sale.order", "create", [{...}])

# Step 2: Confirm it
models.execute_kw(db, uid, key, "sale.order", "action_confirm", [[order_id]])
```

**WARNING — Confirmation triggers these custom validations:**

| Check | Module | What Happens |
|-------|--------|-------------|
| Credit limit exceeded | `sale_extended_ept` | Order goes to **on_hold** state, creates approval request |
| Overdue invoices | `sale_extended_ept` | Order goes to **on_hold** state, creates approval request |
| Line priced below cost | `sale_below_cost_approval_ept` | Blocks confirmation, requires approval |
| Discount exceeds job limit | `discount_management_ept` | Blocks confirmation, requires approval |

If any of these trigger, `action_confirm` won't raise an error — the order silently moves to `on_hold` instead of `sale`. **Always read back the state after confirming:**

```python
result = models.execute_kw(db, uid, key, "sale.order", "read",
    [[order_id]], {"fields": ["state", "credit_on_hold", "name"]}
)
# state will be: "draft", "sale", or "on_hold"
```

---

## 4. Preventing Duplicates

Use `client_order_ref` as your idempotency key. Before creating, check if it already exists:

```python
existing = models.execute_kw(db, uid, key, "sale.order", "search",
    [[["client_order_ref", "=", "LEGACY-SO-20260001"]]]
)
if existing:
    # Order already synced — skip or update
    pass
else:
    # Safe to create
    order_id = models.execute_kw(db, uid, key, "sale.order", "create", [{...}])
```

---

## 5. Error Handling

| Scenario | What Happens | What to Do |
|----------|-------------|-----------|
| Invalid `partner_id` | `ValueError` / missing required field | Validate IDs exist before creating |
| Invalid `product_id` | `ValueError` | Validate IDs exist before creating |
| Network timeout | No response | Retry with dedup check (step 4) |
| `AccessError` | API user lacks permission | Check user role: needs Sales/User |
| `ValidationError` | Business rule violated | Log full error, fix data, retry |
| Order goes `on_hold` | Credit/discount approval needed | Log it — Odoo team handles approval |

**Always wrap calls in try/catch and log the full Odoo fault string.**

---

## 6. Reading Back Results

After creating an order, read back key fields for your records:

```python
models.execute_kw(db, uid, key, "sale.order", "read",
    [[order_id]],
    {"fields": ["name", "state", "amount_total", "client_order_ref"]}
)
# Returns: {"name": "S00042", "state": "draft", "amount_total": 1350.0, ...}
```

Store the Odoo `name` (e.g., `S00042`) in your legacy system for cross-reference.

---

## 7. Rate Limits & Performance (odoo.sh)

- **Do not** send hundreds of orders in a tight loop — odoo.sh has request limits
- Batch approach: create orders sequentially with a small delay (200-500ms between calls)
- For bulk historical migration, coordinate with the Odoo team to use direct import or scheduled jobs
- Each `create` call with order lines is a single transaction — keep line count reasonable (<50 lines per order)

---

## 8. Checklist Before Go-Live

- [ ] Dedicated API user created with correct roles
- [ ] API key generated and stored securely (not in source code)
- [ ] Customer sync verified — all active customers exist in Odoo with consistent identifiers (VAT, email, or external ID)
- [ ] Product sync verified — all products exist with matching `default_code`
- [ ] `client_order_ref` populated for every order (dedup key)
- [ ] Error logging captures full Odoo fault responses
- [ ] Retry logic includes dedup check before re-creating
- [ ] Orders created as **draft** during pilot phase
- [ ] Read-back after create to verify state and capture Odoo order number
- [ ] Tested against odoo.sh staging environment (not production)
