# SEDCO Metabase Reports — Next Phase Tasks

> Backlog from Codex adversarial review (2026-04-25). Three findings on the
> current module; all confirmed against the implementation.

## Phase: Hardening (Stage F)

### Task 1 — Restrict configuration action and tighten model ACLs

**Severity:** High — auth boundary failure
**Files:**
- `views/metabase_dashboard_views.xml:61-65`
- `security/ir.model.access.csv:2-7`

**Problem:**
The `ir.actions.act_window` (`action_metabase_dashboard`) has no `groups_id`,
so any authenticated user can reach it directly via `/web#action=<id>` or RPC.
Combined with the read ACL granted to `group_mb_viewer` and `group_mb_ops` on
`metabase.dashboard` and `metabase.sync.model`, non-managers can enumerate
dashboard codes, Metabase IDs, allowed groups, locked parameter names, and
sync model mappings — i.e., the configuration metadata that the menu hides.

**Acceptance criteria:**
- [ ] Add `<field name="groups_id" eval="[(4, ref('group_mb_manager'))]"/>` to
  `action_metabase_dashboard`.
- [ ] Decide whether viewer/ops actually need to *read* `metabase.dashboard`.
  - If only the controller needs to read, drop the viewer/ops rows entirely
    (controller already uses `sudo()`).
  - If end users must read some records, add a `ir.rule` that filters records
    by `allowed_group_ids` membership for non-managers.
- [ ] Same review for `metabase.sync.model` — the controller is the only
  consumer; viewer/ops read may be unnecessary.
- [ ] Add an integration test where a viewer user attempts to:
  - Load `action_metabase_dashboard` directly → expect access denied.
  - `search_read` on `metabase.dashboard` → expect empty/restricted result.

---

### Task 2 — Move on-demand sync off the request path

**Severity:** High — performance/availability risk
**Files:** `controllers/main.py:78-143`

**Problem:**
Dashboard sync can still run synchronously on an embed request when
`open_sync_mode` is `full` or `incremental`. There is no lock, debounce
window, or deduplication yet. Concurrent opens of the same dashboard, page
refreshes, or multiple tabs can still fire overlapping POSTs to
`/api/OdooSyncReload`. Under load this can stampede UXServer and block the
HTTP worker for up to `sync_timeout_seconds` (default 25s).

**Acceptance criteria:**
- [ ] Replace inline `urlopen` with a queued/dispatched job. Options:
  - Odoo `ir.cron` with a state field (`metabase.sync.request`) that
    deduplicates by model set and recency.
  - Or a deduplicated "in-flight" cache keyed by sorted-model-tuple in
    `ir.config_parameter` / a small `metabase.sync.lock` model.
- [ ] Enforce a minimum refresh interval per dashboard (e.g.,
  `min_refresh_seconds`, default 60s). If the last successful sync is
  newer than that, skip the request entirely.
- [ ] Embed page should *display* last-sync metadata (timestamp, status)
  instead of *causing* the sync.
- [ ] Add a "Refresh now" manager-only button that enqueues a sync and
  returns immediately.
- [ ] Load test: 10 concurrent opens of `sales_orders` should result in
  ≤1 outbound request to UXServer within the refresh window.

---

### Task 3 — Validate UXServer sync response, don't trust HTTP 200

**Severity:** Medium → High under load (silent stale data)
**Files:** `controllers/main.py:129-132`

**Problem:**
The success path is `with urlopen(req): pass` — it only catches `HTTPError`
and ignores the response body. UXServer can return:
- `202 Accepted` for an async job that hasn't run yet.
- `200 OK` with `{"success": false, "error": "..."}` for app-level failures.
Both are silently treated as "sync complete, render the dashboard."

**Acceptance criteria:**
- [ ] Define the response contract with UXServer (coordinate with the
  `OdooSyncService.js` owner). Recommended:
  ```json
  {
    "success": true,
    "job_id": "uuid",
    "completed_at": "2026-04-25T10:30:00Z",
    "models": ["sale.order", "..."]
  }
  ```
- [ ] Parse the JSON body and require `success === true`. Reject 202 unless
  the controller polls a follow-up status endpoint.
- [ ] Log `job_id` on every sync request for traceability.
- [ ] Surface `completed_at` (or "stale since X") in the embed page header.
- [ ] Add a unit test for each branch: 200+success, 200+failure, 202,
  invalid JSON, timeout, HTTPError, ConnectionError.

---

## Cross-cutting items surfaced by the review

- [ ] Backfill `locked_parameter_name` on existing `metabase.dashboard`
  records during upgrade (referenced in the earlier working-tree review —
  silent fallback to legacy `salesperson_id` is a fail-open hazard).
- [ ] Add server-side validation on `locked_parameter_name`: trim, reject
  blank/whitespace, enforce a slug regex (e.g., `^[a-z][a-z0-9_]*$`).
- [ ] Auto-generate menu entries from `metabase.dashboard` records (current
  limitation noted in README) so the data-driven story is complete.

## References

- Adversarial review (working tree, 2026-04-23) — `locked_parameter_name`
  fallback + free-form validation findings.
- Adversarial review (full module, 2026-04-25) — three findings above.
