# Codebase Concerns

**Analysis Date:** 2026-02-12

## Tech Debt

**Hardcoded File I/O in UAE E-Invoicing Module:**
- Issue: `orchida_uae_e_invoicing/models/account_move.py` writes request data to local filesystem (`request_data.json`)
- Files: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py:140-141`
- Impact: File system pollution, security risk, non-idempotent operations, fails in containerized/multi-server environments
- Fix approach: Remove debug file write, implement proper logging via Odoo logger instead

**Debug Print Statement Left in Production:**
- Issue: `orchida_uae_e_invoicing/models/account_move.py` contains `print()` statement
- Files: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py:144`
- Impact: Output appears in console, not in Odoo logs; breaks containerized deployments where stdout is monitored
- Fix approach: Replace with `_logger.info()` or `_logger.debug()`

**Empty Exception Handler with Pass:**
- Issue: `customer_management_ept/models/res_partner.py:183` has conditional branch with only `pass` statement
- Files: `odoo/custom_addons/customer_management_ept/models/res_partner.py:183`
- Impact: Readability issue; unclear business logic intent; may hide future bugs
- Fix approach: Replace with explicit business logic or early return

**Unused Helper Export in Stock Picking:**
- Issue: `stock_extended_ept/models/stock_picking.py:86` contains template string literal that is never evaluated
- Files: `odoo/custom_addons/stock_extended_ept/models/stock_picking.py:86`
- Content: `'Incoterm': "'%s %s' % (incoterm.code, incoterm_location)"`
- Impact: Returns literal string instead of formatted incoterm; exports incorrect data to Excel reports
- Fix approach: Evaluate template before adding to dict: `f"{incoterm.code} {incoterm_location}"`

## Security Considerations

**Sudoed Operations Without Explicit Justification:**
- Risk: 35 instances of `.sudo()` in codebase lack consistent inline documentation
- Files affected:
  - `odoo/custom_addons/mrp_extended_ept/models/mrp_workcenter_productivity.py` (approval.category creation)
  - `odoo/custom_addons/sale_extended_ept/models/sale_order.py` (approval request creation)
  - `odoo/custom_addons/pilot_order_ept/models/sale_order.py` (approval and tag creation)
  - `odoo/custom_addons/stock_extended_ept/models/stock_quant.py` (approval.category creation)
  - `odoo/custom_addons/customer_management_ept/models/res_partner.py` (sequence operations)
- Current mitigation: Most `.sudo()` calls are for system-level data (approval categories, sequences) not user-sensitive data
- Recommendations:
  - Add `# NOTE: sudo() used for system-level creation` comments above each call
  - Audit `customer_management_ept` sequence operations to ensure user input isn't written with elevated permissions
  - Consider whether approval.category should be managed by admin role instead of sudo()

**Hardcoded API Endpoint URL:**
- Risk: `orchida_uae_e_invoicing/models/account_move.py:35` contains hardcoded development API URL
- Files: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py:34-36`
- Current URL: `https://dev.orchida-einvoice.com/api-pub/api/InvGenerateQr`
- Impact: Production invoicing will fail; endpoint is development-only; credentials exposure if URL changes
- Fix approach: Move to `ir.config_parameter` with environment variable fallback

**API Token in System Parameters Without Encryption:**
- Risk: API tokens stored as plain text in `ir.config_parameter`
- Files: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py:40`
- Current: `self.env['ir.config_parameter'].sudo().get_param('api_module.api_token')`
- Impact: Tokens visible in database backups, access logs, admin interface
- Recommendations: Use Odoo's encrypted parameter storage (if available) or external secret management

**Hardcoded Buyer/Seller Information in Invoice API:**
- Risk: Hardcoded test values in API payloads
- Files: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py:77-87`
- Examples: `"buyerCode": "1"`, `"buyerName": "buyerTest"`, `"buyerTaxID": "100820361200003"`
- Impact: All invoices sent with identical test buyer/seller info; incorrect invoicing records
- Fix approach: Map company and customer data to these fields; lookup from configuration or company record

## Performance Bottlenecks

**Large Report Models Without Pagination or Limits:**
- Problem: SQL view-based reports are read-only but may query millions of rows at once
- Files:
  - `odoo/custom_addons/sales_reports_ept/report/sales_recognition_report.py` (459 lines)
  - `odoo/custom_addons/sales_reports_ept/report/budget_vs_actual_report.py` (440 lines)
- Cause: Pivot reports fetch all records into memory before pivot table aggregation; no pagination
- Risk: Timeout on large datasets (>10k orders/budget lines); UI freezes; database load spikes
- Improvement path:
  - Add date range filters to limit report scope
  - Implement dashboard with pre-computed summaries instead of real-time pivots
  - Consider materialized views for frequently accessed reports
  - Add query execution time warnings in view

**Potential N+1 Query in Stock Picking Export:**
- Problem: `stock_extended_ept/models/stock_picking.py:31-35` and similar loops call `.write()` inside loops
- Files: `odoo/custom_addons/stock_extended_ept/models/stock_picking.py:31-35`
- Code: `for lot in lot_recs: lot.write({'bayan_code': picking.bayan_code})`
- Risk: One write per lot instead of batch update; if picking has 100 lots, 100 database writes
- Improvement path: Use `lot_recs.write()` for batch update instead of loop

**Large Wizard Without Progress Indication:**
- Problem: `mrp_extended_ept/wizards/component_availability_wizard.py` (386 lines) generates Excel workbooks synchronously
- Files: `odoo/custom_addons/mrp_extended_ept/wizards/component_availability_wizard.py`
- Risk: For BOMs with 1000+ components, workbook creation may timeout (>30s)
- Improvement path: Move to async job queue (Odoo cron); return task reference instead of immediate download

## Known Issues

**UAE E-Invoicing API Integration Incomplete:**
- Symptoms: Invoices may fail to send silently or with poor error feedback
- Files: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py`
- Issues:
  1. Hardcoded test data in payloads (above)
  2. No retry logic on timeout
  3. No error recovery workflow
  4. Response logged to database but not analyzed for business-level errors
  5. Silent failure: if `.sudo().create()` of api.sent.invoice fails, invoice marked as sent anyway
- Trigger: Create and post customer invoice with Orchida integration enabled
- Workaround: Manually verify invoice status in Orchida portal; resend via cron if needed
- Fix approach: Add proper error handling, separate validation, and webhook response parsing

**Inconsistent Discount Line Handling in Sale Orders:**
- Problem: Discount calculation in `discount_management_ept/models/sale_order.py` treats lines with negative price differently from discount-only lines
- Files: `odoo/custom_addons/discount_management_ept/models/sale_order.py:46-52`
- Impact: Global discounts (negative price lines) are correctly excluded from discount % calculation, but mixed discount types may cause approval issues
- Blocks: Cannot reliably audit total discounts when using both `discount` field and negative price lines

**Pilot Order Approval State Not Enforced at Validation:**
- Problem: `pilot_order_ept/models/sale_order.py:36-50` checks `pilot_approval_state` in `action_confirm()` but state can be changed externally
- Files: `odoo/custom_addons/pilot_order_ept/models/sale_order.py`
- Impact: Approvers may bypass workflow by editing state directly
- Fix approach: Add SQL constraint `CHECK(is_pilot_order=false OR pilot_approval_state IN ('draft', 'pending', 'approved'))`

## Fragile Areas

**Customer Validation Workflow with Hard-to-Predict Permissions:**
- Files: `odoo/custom_addons/customer_management_ept/models/res_partner.py` (209 lines)
- Why fragile:
  1. Field-level restrictions change based on `validation_status` (line 170-192)
  2. Two separate role groups check: `has_group('customer_management_ept.group_finance_team')`
  3. Customer ID auto-generation on create and on write (line 48, line 199)
  4. Unlink blocked for validated customers (line 205)
  5. Sequence creation is sudo-ed inside _generate_customer_id (line 62)
- Safe modification:
  - Always test permission changes with both Finance and Sales team roles
  - Add test for sequence generation in multi-company environments
  - Test unlink for validated vs unvalidated customers
  - Verify customer_id idempotency (write twice should not change sequence)

**Sales Recognition Report with Complex Revenue Schedule Logic:**
- Files: `odoo/custom_addons/sales_reports_ept/report/sales_recognition_report.py` (459 lines)
- Why fragile:
  1. Depends on `sale.order.recognition.schedule` model (not found in current codebase; may be external dependency)
  2. Joins across 5+ models (sale.order, sale.order.recognition.schedule, account.move, product.line.ept, res.partner)
  3. Payment status computed from linked invoice states (potential circular references)
  4. Monthly columns hardcoded (Jan-Dec); no multi-year view; calendar changes not handled
  5. Recognition coverage % computed with aggregator='avg' but should probably be 'sum'
- Safe modification:
  - Add precondition checks that `sale.order.recognition.schedule` exists
  - Add test with multiple orders having overlapping recognition schedules
  - Verify payment status updates when invoices change state
  - Check report with fiscal years that don't align to calendar year
  - Test coverage % calculation with multiple recognition lines per order
- Test coverage: Likely untested; recommend adding integration tests

**BPM Parallel Execution Model (Deleted from Repository):**
- Files: Originally `odoo/custom_addons/sedco_bpm_engine/` - **DELETED** (see git status)
- Impact: Any existing workflows referencing this module will fail on installation
- Risk: Production Odoo instances have BPM workflows stored in database that reference deleted models
- Current state: Module code exists in commit history (f24f704db06) but deleted from HEAD
- Fix approach:
  1. Either restore the module with migration script
  2. Or create database migration to clean up orphaned workflow records
  3. Confirm all instances have been migrated before deleting permanently

**Deleted Custom CRM Module Relationship:**
- Files: Originally `odoo/custom_addons/custom_crm/` - **DELETED** (see git status)
- Impact: 30 deleted files including views, models (crm_lead, crm_stage, vertical, utm_campaign, opportunity_rec_schedule)
- Risk: CRM customizations may have been superseded by `sedco_crm` or integrated elsewhere; unclear migration path
- Current state: `sedco_crm` and `sedco_crm_assignment_domain_bridge` exist as replacements
- Safe cleanup:
  1. Verify all custom_crm functionality has been replicated in sedco_crm
  2. Check database for orphaned model records from custom_crm
  3. Update any references in other modules

## Missing Critical Features

**No Test Coverage for Custom Modules:**
- What's missing: Zero test files in `odoo/custom_addons/` (searched for `test_*.py` and `*_test.py`)
- Problem: No automated validation of:
  - Approval workflows (35+ instances of approval.request creation)
  - Discount limits and calculation logic
  - Customer validation state machine
  - Pilot order approval enforcement
  - UAE invoice API integration
- Blocks: Cannot safely refactor any business logic without regression risk
- Priority: **HIGH** - Should add tests for approval, discount, and validation workflows
- Approach: Create test_*.py modules in each custom addon following Odoo test patterns

**No Error Logging Configuration:**
- Problem: Custom modules use print() and silent error swallowing (especially in orchida_uae_e_invoicing)
- Blocks: Cannot debug production issues; no audit trail for failed integrations
- Fix approach: Import logging module; create module-level logger; replace print() and bare except blocks

## Scaling Limits

**SQL View Reports Not Indexed for Large Datasets:**
- Current capacity: Tested up to ~5k sales orders
- Limit: Pivot tables on 50k+ orders may timeout
- Risk: Monthly end-of-period reporting becomes unreliable as order volume grows
- Scaling path:
  1. Add database indexes on join columns (sale_order.id, partner_id, invoice_date)
  2. Implement pre-computed summary tables (dashboard instead of real-time pivot)
  3. Add date range filters to enforce report scope limits
  4. Monitor query execution time; add warning if >30 seconds

**Approval Request Creation at Scale:**
- Current: Loops create approval requests one at a time (pilot_order_ept, discount_management_ept)
- Limit: If 100 sales orders are confirmed via API, 100 approval requests created sequentially
- Scaling path: Batch approval creation; consider async approval job queue

## Dependencies at Risk

**Orchida UAE E-Invoicing API Dependency:**
- Risk: API endpoint is hardcoded; response handling is basic; no fallback
- Impact: If Orchida service is down, all customer invoices fail silently
- Migration plan:
  1. Parameterize API endpoint
  2. Add retry logic with exponential backoff
  3. Implement webhook callback instead of blocking send on invoice post
  4. Queue failed invoices for manual resend

**External n8n Integration in Smart Report Builder (Deleted Module):**
- Risk: `smart_report_builder` module referenced in CLAUDE.md as reference implementation for n8n patterns, but not found in git
- Blocks: Cannot use n8n webhook patterns as documented
- Status: Likely implemented in earlier branch or deleted; unclear

---

*Concerns audit: 2026-02-12*
