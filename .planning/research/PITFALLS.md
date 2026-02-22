# Domain Pitfalls: BPM Automation Engine in Odoo 18

**Domain:** BPM / Workflow Engine inside Odoo 18 Enterprise
**Researched:** 2026-02-22
**Sources:** Odoo 18 source code (verified in-repo), `base_automation`, `ir_cron`, `ir_actions`, `safe_eval`, and existing custom modules

---

## Critical Pitfalls

Mistakes that cause infinite loops, data corruption, security breaches, or full rewrites.

---

### Pitfall 1: Infinite Trigger Loop — BPM Write Triggers Itself

**What goes wrong:**
A BPM step updates a field on a record (e.g., sets `bpm_state = 'step_2'`). That write is observed by the same or another `base.automation` rule whose condition also matches, re-firing the BPM engine. The loop continues until a stack overflow or transaction timeout kills the process.

**Why it happens:**
`base_automation._register_hook()` monkey-patches `create`/`write`/`_compute_field_value` at the ORM class level. Every write on a watched model fires the patched method regardless of who initiated the write. The BPM engine writing to a watched model is indistinguishable from a user writing to it.

**Root cause (code evidence):**
Odoo 18's own `base_automation` uses `__action_done` in `self.env.context` as a recursion guard (see `base_automation.py:_process`, line 687–703). It deduplicates automations per record per transaction. But this guard is **only effective within the same `base.automation` call chain**. A custom BPM engine that calls `record.write(...)` directly will not inherit `__action_done` from its context unless explicitly threaded through.

**Consequences:**
- Transaction-level deadlock or infinite recursion (Python `RecursionError`)
- Phantom workflow instances created in a loop (thousands of `bpm.instance` records)
- Database connection exhaustion

**Prevention:**
1. **Context flag guard.** Before any BPM-driven write, inject a context key:
   ```python
   record.with_context(bpm_engine_write=True).write({'state': 'done'})
   ```
   In the BPM trigger hook (or patched `write`), check:
   ```python
   if self.env.context.get('bpm_engine_write'):
       return  # skip trigger evaluation
   ```
2. **Optionally reuse `__action_done`.** Propagate `__action_done` from the current context into BPM step execution so it is compatible with `base.automation` deduplication.
3. **Do NOT trigger BPM from computed stored fields.** `_compute_field_value` is also patched by `base_automation` and fires on every recomputation. BPM triggers should only attach to explicit user actions or cron, not to stored compute chains.

**Detection (warning signs):**
- `bpm.instance` or step records multiplying unexpectedly
- Transaction rollbacks with `RecursionError` in Odoo server logs
- CPU usage spikes when saving a record

**Phase to address:** Phase 1 (Core Engine) — build the context guard before any write-back logic is added.

---

### Pitfall 2: Raw `exec()` Instead of `safe_eval` for Python Code Steps

**What goes wrong:**
Using Python's `exec()` to run user-defined BPM step code (as seen in `ept_execute_python_code`, which calls `exec(obj.code, localdict)` with no sandboxing). An administrator with BPM step edit access can execute arbitrary OS commands, read environment variables, exfiltrate secrets, or destroy data.

**Why it happens:**
`exec()` is unrestricted. It gives full access to the Python runtime including `os`, `subprocess`, `__import__`, and frame inspection. The existing `ept_execute_python_code` module in this codebase demonstrates exactly this anti-pattern.

**Root cause (code evidence):**
`odoo/tools/safe_eval.py` provides a bytecode-level sandbox. It blocks `IMPORT_NAME`, `IMPORT_STAR`, `IMPORT_FROM`, `STORE_ATTR`, `DELETE_ATTR`, `STORE_GLOBAL`, `DELETE_GLOBAL` opcodes (lines 77–85). It also blocks all dunder attribute access via `assert_no_dunder_name`. Odoo's own `ir.actions.server` uses `safe_eval(code, eval_context, mode="exec")` (line 827 in `ir_actions.py`). This is the correct pattern.

**Consequences:**
- Remote code execution via any user who can edit a BPM step
- Data exfiltration, credential theft, ransomware-equivalent

**Prevention:**
1. **Always use `safe_eval` for user-defined code:**
   ```python
   from odoo.tools.safe_eval import safe_eval
   safe_eval(step.code.strip(), eval_context, mode="exec", nocopy=True)
   ```
2. **Validate code at save time using `test_python_expr`:**
   ```python
   from odoo.tools.safe_eval import test_python_expr
   msg = test_python_expr(expr=step.code.strip(), mode="exec")
   if msg:
       raise ValidationError(msg)
   ```
   (Odoo does this in `ir.actions.server._check_python_code`, line 772–777.)
3. **Restrict the eval context.** Only expose `env`, `record`, `datetime`, `time`, `logger`. Do not expose `self`, `model`, or anything that allows model meta-access beyond what the step needs.
4. **Gate the code field with `groups='base.group_system'`** so only Odoo administrators can write Python step code (matching how `ir.actions.server.code` is restricted).

**Detection (warning signs):**
- `exec()` anywhere in BPM step execution code
- BPM step model has `code` field without `groups` restriction
- No `test_python_expr` call in `@api.constrains('code')`

**Phase to address:** Phase 1 (Core Engine) — before any Python step type is exposed to users.

---

### Pitfall 3: Outbox Race Condition — Two Workers Claiming the Same Step

**What goes wrong:**
Two Odoo cron workers both read the BPM outbox (pending step executions) in the same polling interval. Both see a row with `state = 'pending'`. Both begin executing the same step, producing duplicate side-effects (two emails sent, two records created, two approvals submitted).

**Why it happens:**
The naive outbox polling pattern is:
```sql
SELECT * FROM bpm_outbox WHERE state = 'pending' LIMIT 10
```
Without row-level locking, two workers execute this simultaneously and get overlapping results.

**Root cause (code evidence):**
Odoo 18's `ir.cron._acquire_one_job` solves this exact problem using `FOR NO KEY UPDATE SKIP LOCKED` (line 295 in `ir_cron.py`). This is the established PostgreSQL pattern: the first worker locks the row, the second worker skips it. The BPM outbox must implement the same pattern.

**Consequences:**
- Duplicate step executions (double emails, double approvals, double inventory moves)
- Idempotency failures that corrupt workflow state
- Impossible to debug because it only manifests under load

**Prevention:**
1. **Use `FOR NO KEY UPDATE SKIP LOCKED` on outbox queries:**
   ```python
   self.env.cr.execute("""
       SELECT id FROM bpm_outbox
       WHERE state = 'pending' AND scheduled_at <= NOW()
       ORDER BY priority, id
       LIMIT %s
       FOR NO KEY UPDATE SKIP LOCKED
   """, [batch_size])
   ```
2. **Add an idempotency key column** (`idempotency_key = uuid`) on outbox rows. Before executing, attempt an `UPDATE ... WHERE idempotency_key = %s AND state = 'pending'` returning `id`. If 0 rows updated, another worker claimed it.
3. **Transition outbox state atomically** from `pending` → `processing` in the same SQL statement that acquires the lock, not in a subsequent ORM write.
4. **Never use ORM `search()` for outbox polling in multi-worker deployments.** ORM search has no locking semantics.

**Detection (warning signs):**
- Duplicate chatter messages on workflow records
- `bpm.outbox` rows in `processing` state that never clear (worker crashed mid-execution)
- Unexplained duplicate approval requests

**Phase to address:** Phase 2 (Orchestrator / Outbox) — the entire outbox design must be built around this constraint.

---

### Pitfall 4: Cron Job Overlap — Orchestrator Runs While Previous Instance Is Still Running

**What goes wrong:**
The BPM orchestrator cron runs every 1 minute. A batch of 500 pending steps takes 90 seconds to process. The cron fires again at the 60-second mark, spawning a second orchestrator that begins working on the same records the first orchestrator is still handling.

**Why it happens:**
`ir.cron` in Odoo does NOT have a built-in "skip if already running" guard. It uses `FOR NO KEY UPDATE SKIP LOCKED` only to prevent two cron *processes* from running the same cron job *concurrently in the same instant*. If a cron job takes longer than its interval, the next scheduled invocation will run as a separate job.

**Root cause (code evidence):**
The `_acquire_one_job` query checks `nextcall <= NOW()`, but after a job is acquired, `nextcall` is updated immediately (before the job finishes). If the job takes longer than the interval, the updated `nextcall` will again be `<= NOW()` before the job is done. Odoo partially mitigates this with `MAX_BATCH_PER_CRON_JOB = 10`, meaning the cron processes at most 10 items per run and exits, relying on the next interval to process more.

**Consequences:**
- Multiple orchestrator instances compete for the same outbox items
- State machine corruption if two workers advance the same workflow instance simultaneously
- Database deadlocks from conflicting row locks

**Prevention:**
1. **Implement the same batch-cap pattern as Odoo's own cron.** Process at most N outbox items per cron invocation and exit. Let the interval handle the rest.
2. **Use `_try_lock()` pattern at the orchestrator level** — acquire a PostgreSQL advisory lock for the duration of the cron run:
   ```python
   acquired = self.env.cr.execute(
       "SELECT pg_try_advisory_xact_lock(%s)", [ORCHESTRATOR_LOCK_ID]
   )
   if not self.env.cr.fetchone()[0]:
       return  # another instance is running
   ```
3. **Keep cron interval ≥ expected processing time.** If processing 100 steps takes 30 seconds, set interval to 60 seconds minimum.
4. **Never put long-running I/O (HTTP calls, email sending) inside the cron transaction.** Use the outbox pattern: schedule the work, then execute it in small isolated transactions.

**Detection (warning signs):**
- `ir.cron` logs showing the BPM cron starting before the previous log shows it ending
- Deadlock errors (`deadlock detected`) in PostgreSQL logs
- Workflow instances stuck in intermediate states

**Phase to address:** Phase 2 (Orchestrator) — build the advisory lock and batch cap from day one.

---

### Pitfall 5: ORM Hook Ordering Conflict with Other Custom Modules

**What goes wrong:**
`base_automation._register_hook()` monkey-patches `create`/`write` on model classes at server startup. The BPM engine also needs to intercept `create`/`write` to detect trigger conditions. Both patches use `.origin` chaining (each patch saves the previous method as `method.origin`). If the BPM module and `base_automation` both patch the same model's `write`, and either unregisters its hook (e.g., when automation rules are modified), the other module's patch is silently dropped.

**Root cause (code evidence):**
`base_automation._unregister_hook()` calls `delattr(Model, name)` for every patched model (line 951–958). This removes the attribute from the class entirely, including any BPM patches that were layered on top. The `patched_models` defaultdict only tracks whether a model has been patched at all, not how many patches are layered.

**Consequences:**
- BPM triggers silently stop firing after any `base.automation` rule is created, modified, or deleted
- Extremely difficult to reproduce because it only happens after Automation Rules are changed in the UI
- No error is raised — the patch is just gone

**Prevention:**
1. **Do not monkey-patch `create`/`write` yourself.** Instead, hook into `base_automation`'s trigger system. Add a custom action type (`state = 'bpm_step'`) to `ir.actions.server` so BPM steps are executed as server actions within the existing `base_automation` chain. This is how Odoo's own mail, SMS, and studio modules extend automation.
2. **If you must patch, use `_register_hook`/`_unregister_hook` in the same style as `base_automation` and call `_update_registry()` after to notify all workers.** Do not patch outside this lifecycle.
3. **Test: create a `base.automation` rule after installing the BPM module, then trigger the BPM engine. Verify it still works.**

**Detection (warning signs):**
- BPM triggers stop firing after an admin creates or edits an Automation Rule
- Server restart restores BPM functionality (patches re-applied on startup)

**Phase to address:** Phase 1 (Core Engine) — architectural decision on whether to extend `ir.actions.server` or to monkey-patch independently must be made before any trigger code is written.

---

### Pitfall 6: Memory Leak in Long-Running Orchestrator Context

**What goes wrong:**
The BPM orchestrator accumulates records in an Odoo environment (`self.env`) that is reused across many loop iterations without flushing or clearing caches. After processing thousands of steps, the environment's record cache (`self.env.cache`) has grown to hold tens of thousands of records, consuming hundreds of megabytes of RAM.

**Why it happens:**
Odoo's `Environment` caches every record access in `self.env.cache`. In a long-running batch loop (e.g., processing 10,000 pending steps), every `record.browse()`, field access, and `search()` adds entries to this cache. The cache is never evicted until the environment is discarded (end of transaction or new cursor).

**Consequences:**
- Odoo worker process RAM grows unboundedly during cron runs
- Worker OOM-killed by the OS, leaving outbox items in `processing` state
- Subsequent cron run must detect and recover stuck items

**Prevention:**
1. **Use `self.env.cr.commit()` and create a fresh cursor/environment per batch chunk.** The standard Odoo cron pattern processes items in separate savepoints or sub-transactions.
2. **Call `self.env.invalidate_all()` periodically** (e.g., every 100 steps) to evict the record cache without committing:
   ```python
   if processed_count % 100 == 0:
       self.env.invalidate_all()
   ```
3. **Use `with_context(prefetch_fields=False)`** when reading outbox items in bulk to prevent Odoo's prefetch mechanism from loading entire recordsets into the cache.
4. **Structure the orchestrator cron as: acquire → process N items → exit.** Let the next cron invocation process the next N items. This naturally bounds memory per run.

**Detection (warning signs):**
- Odoo worker memory (`RSS`) grows monotonically during cron execution
- `MemoryError` or OOM kills in system logs after large BPM batches
- Cron run duration increases linearly with backlog size

**Phase to address:** Phase 2 (Orchestrator) — batch cap and cache invalidation must be part of the initial cron design.

---

### Pitfall 7: N+1 Queries in Step Execution Loop

**What goes wrong:**
The orchestrator fetches all pending outbox items, then iterates over each one. For each step, it reads `step.workflow_id`, then `step.workflow_id.model_id`, then `step.config_id.action_ids`, executing one SQL query per attribute access per step. Processing 500 steps generates 1,500+ queries, taking minutes instead of seconds.

**Why it happens:**
Odoo's ORM lazy-loads related fields. `step.workflow_id` issues one query. `step.workflow_id.model_id` issues another. In a loop over records, each iteration issues the same queries independently.

**Consequences:**
- Orchestrator cron takes 10x longer than necessary
- Database connection saturation under concurrent load
- Cron overlap (Pitfall 4) is more likely when each run is slow

**Prevention:**
1. **Prefetch all required fields in a single query** before the loop:
   ```python
   steps = self.env['bpm.outbox'].search(domain)
   # Force prefetch of all needed relational fields
   steps.mapped('step_id.workflow_id.model_id')
   steps.mapped('step_id.action_ids')
   ```
   After these `mapped()` calls, all subsequent accesses inside the loop use the cache.
2. **Use `read(['field1', 'field2', ...])` for bulk data extraction** when you need raw values (no ORM behavior needed):
   ```python
   steps.read(['state', 'step_id', 'record_ref', 'scheduled_at'])
   ```
3. **Search with domain joins using `read_group()` for statistics**, not looped `search_count()`.
4. **Profile with `odoo.sql_db` logging.** Add `--log-sql` during development to see every SQL statement. Any repeated identical query in a loop is an N+1.

**Detection (warning signs):**
- Orchestrator cron takes more than 2× longer as the number of pending steps doubles
- PostgreSQL `pg_stat_activity` shows hundreds of simple `SELECT` statements during cron
- `--log-sql` output shows the same query repeated in a loop

**Phase to address:** Phase 2 (Orchestrator) — audit the inner loop query count before the first load test.

---

### Pitfall 8: Human Task Assignment — Unassigned Task Silently Blocks Workflow

**What goes wrong:**
A workflow reaches a human task step. The step tries to find an assignee by evaluating a domain or calling a method (e.g., "assign to manager of the current user"). The result is an empty recordset (the user has no manager, or the domain matches no one). The step silently fails to assign, no task is created, no notification is sent, and the workflow instance hangs indefinitely with no observable state.

**Why it happens:**
Human task assignment logic typically assumes a valid assignee exists. When the assumption is wrong, the assignment returns `False`, `None`, or an empty `res.users` recordset. Without explicit handling, the step is marked as "waiting" for a task that was never created.

**Consequences:**
- Workflow instance permanently stuck in a "waiting" state
- No notification to anyone that a task wasn't created
- Business process blocked silently

**Prevention:**
1. **Always validate the assignee before creating the task.** If empty, escalate to a configured fallback user/group:
   ```python
   assignee = step._compute_assignee(record)
   if not assignee:
       assignee = step.workflow_id.fallback_user_id
   if not assignee:
       raise UserError(_("No assignee found and no fallback configured for step %s") % step.name)
   ```
2. **Use `approval.request` for all human task workflows** (as mandated in `CLAUDE.md`). `approval.request` has built-in assignee validation, escalation, and deadline handling.
3. **Implement a "stuck instance" detector** as a separate cron: find all instances in `waiting_human_task` state older than N hours where no active `approval.request` exists, and alert or escalate.
4. **Log the assignment attempt even if it fails**, so there is always a chatter entry explaining why the task is stuck.

**Detection (warning signs):**
- Workflow instances accumulating in a single state indefinitely
- `approval.request` count does not increase when expected
- No chatter entry on the workflow record at a task step

**Phase to address:** Phase 3 (Human Tasks) — design the assignment failure path before implementing the happy path.

---

### Pitfall 9: Parallel Branch Deadlock — Two Branches Update the Same Record

**What goes wrong:**
A workflow splits into two parallel branches. Branch A updates `sale.order.state` to `'approved'`. Branch B also tries to update `sale.order.state` to `'review'`. PostgreSQL issues a deadlock because Branch A holds a row lock on `sale.order` while waiting for a lock on `bpm.instance`, and Branch B holds a lock on `bpm.instance` while waiting for the same `sale.order` row.

**Why it happens:**
Parallel branches execute concurrently (or in rapid succession within the same transaction). If both branches write to the same target record, PostgreSQL's row-level locking causes a circular wait. This is worse in Odoo because the ORM buffers writes and flushes them at unpredictable times, making the lock acquisition order non-deterministic.

**Consequences:**
- `deadlock detected` PostgreSQL error, one transaction is forcibly rolled back
- Partial workflow execution (one branch advanced, one rolled back)
- Workflow instance left in an inconsistent intermediate state

**Prevention:**
1. **Never write to the same record from two parallel branches.** Enforce this as a design constraint: parallel branches operate on different records or different fields. Validate this in the workflow definition at save time.
2. **Execute parallel branches sequentially within a single transaction** if they must affect the same record. Use a "join gate" that collects all branch results before writing back.
3. **Use `select ... for update` with a consistent lock ordering** if concurrent writes are unavoidable. Always lock records in the same order (e.g., by `id` ascending) across all branches.
4. **Run parallel branches in separate cron jobs** (each branch becomes its own outbox item), so they execute in separate transactions and PostgreSQL handles conflicts via retry rather than deadlock.

**Detection (warning signs):**
- `deadlock detected` in PostgreSQL logs (`/var/log/postgresql/`)
- Workflow instances stuck at a parallel gateway with one branch completed and one in error state
- Inconsistent field values on the target record (set by one branch, reverted by rollback of the other)

**Phase to address:** Phase 4 (Parallel Gateways) — the join gate and lock ordering must be designed before any parallel execution is implemented.

---

### Pitfall 10: `safe_eval` Jinja Context Leakage via `env` Exposure

**What goes wrong:**
The BPM step eval context exposes `env` (the full Odoo `Environment`). A malicious (or misconfigured) step code does:
```python
env['res.users'].search([]).mapped('password')
```
or accesses the database cursor directly:
```python
env.cr.execute("SELECT * FROM res_users")
```
This bypasses all access control and exposes all users' data.

**Why it happens:**
`safe_eval` prevents *Python-level* sandbox escapes (no `__import__`, no dunder access). But if the eval context contains `env`, which is an ORM `Environment` with an active database cursor, the code can read and write anything in the database that the executing user's sudo context allows — without going through any access rights check.

**Consequences:**
- Unauthorized data access (all users, all passwords, all sensitive records)
- Privilege escalation via `env['res.users'].browse(1).write({'active': False})`
- This is a **business logic security hole**, not a Python sandbox escape — `safe_eval` does not protect against it

**Prevention:**
1. **Do not expose the full `env` in the step eval context.** Expose only `record` (the specific record being processed) and helper functions you explicitly define:
   ```python
   eval_context = {
       'record': record,
       'datetime': safe_eval_tools.datetime,
       'time': safe_eval_tools.time,
       'log': logger_proxy,
       # NO: 'env': self.env
   }
   ```
2. **If `env` access is required for a step, run it under a restricted user** using `self.env(user=restricted_user_id)` so ORM access checks apply.
3. **Gate Python step code behind `base.group_system`** (as Odoo does for `ir.actions.server.code`). Only Odoo administrators can write arbitrary code.
4. **For expression fields** (non-code, like filter domains or field mappings), use `safe_eval` in `expr` mode (not `exec` mode) with a context that contains only primitive values, no `env`.

**Detection (warning signs):**
- `env` is a key in any dict passed to `safe_eval(..., mode="exec")`
- BPM step code field is editable by non-system users
- No `groups` restriction on the BPM step code field

**Phase to address:** Phase 1 (Core Engine) — the eval context definition must be locked down before any user-editable code fields are exposed.

---

## Moderate Pitfalls

---

### Pitfall 11: Jinja Template Rendering on Untrusted Input (XSS / SSTI)

**What goes wrong:**
BPM step notifications use Jinja templates where the template content itself is user-defined. A user crafts a template containing `{{ config.__class__.__mro__[1].__subclasses__() }}` or similar SSTI payloads. Even though `safe_eval` blocks this at the Python level, Jinja's own template engine has a separate execution path.

**Prevention:**
1. **Use Odoo's `mail.template` model** for email content rather than raw Jinja rendering. `mail.template` uses `safe_eval` internally and has known-safe defaults.
2. **If using Jinja directly, use `jinja2.sandbox.SandboxedEnvironment`** (not the default `jinja2.Environment`):
   ```python
   from jinja2.sandbox import SandboxedEnvironment
   jinja_env = SandboxedEnvironment()
   result = jinja_env.from_string(template_code).render(context)
   ```
3. **Escape all user-supplied values** in the template context using `markupsafe.escape()`.

**Phase to address:** Phase 3 (Notifications) — before any user-defined template content is rendered.

---

### Pitfall 12: `approval.request` Created Without Confirmed Approver

**What goes wrong:**
An `approval.request` is created with an empty `approver_ids`. The request goes to "new" status and sits there forever because there is no one to approve it. No notification is sent (there are no followers to notify).

**Prevention:**
1. Always validate `approver_ids` is non-empty before calling `approval_request.action_confirm()`.
2. Configure a fallback approver at the `approval.category` level.
3. Add a `@api.constrains('approver_ids')` that raises if the list is empty on confirm.

**Phase to address:** Phase 3 (Human Tasks).

---

### Pitfall 13: Workflow Definition Modified While Instances Are Running

**What goes wrong:**
A workflow definition is updated (step renamed, transition deleted) while live workflow instances are mid-execution. Existing instances reference step IDs that no longer exist, causing `MissingError` when the orchestrator tries to advance them.

**Prevention:**
1. **Version workflow definitions.** Store a snapshot of the definition at instance creation time (or use a version number foreign key).
2. **Block definition edits if active instances exist.** Add a `@api.constrains` or a UI warning.
3. **Store `step_id` as a reference with `ondelete='restrict'`** so PostgreSQL prevents deletion of steps with active instances.

**Phase to address:** Phase 1 (Core Engine) — the instance-to-definition relationship must handle versioning from the start.

---

### Pitfall 14: Stored Computed Fields Triggering BPM — Cascade Effect

**What goes wrong:**
A BPM trigger fires when a stored computed field changes. That computed field is recomputed when any of its dependencies change. A single user action triggers a cascade: user saves → field A changes → field B recomputes → field C recomputes → BPM trigger fires 3 times for different computed fields, creating 3 workflow instances.

**Root cause (code evidence):**
`base_automation._register_hook()` also patches `_compute_field_value` (line 936), which means automation triggers fire not just on explicit writes but also when the ORM recomputes stored fields. The BPM engine must be careful not to attach triggers to fields that are the output of other triggers.

**Prevention:**
1. **Trigger BPM only on user-facing state fields** (`state`, `stage_id`, explicit boolean flags), not on computed fields.
2. **Use `trigger_field_ids` scoping** in `base.automation` to limit which fields actually fire the BPM trigger.
3. **Add a deduplication guard** at the instance creation level: check if an instance for this record + workflow + trigger already exists in the current transaction before creating a new one.

**Phase to address:** Phase 1 (Core Engine).

---

## Minor Pitfalls

---

### Pitfall 15: `nextcall` Not Updated on Cron Error

**What goes wrong:**
The BPM orchestrator cron raises an unhandled exception. Odoo's cron framework catches the exception but does NOT automatically advance `nextcall`. The cron remains scheduled for "now" and immediately retries on the next cron worker poll, hammering the database with failing requests.

**Prevention:**
Wrap the entire orchestrator body in a `try/except` that logs the error, increments a failure counter, and sets `nextcall` to `now + backoff_interval` before re-raising or returning. Alternatively, use sub-transactions (`savepoint`) per outbox item so a single item failure does not abort the entire batch.

**Phase to address:** Phase 2 (Orchestrator).

---

### Pitfall 16: `ir.cron` Trigger vs. Scheduled Time Confusion

**What goes wrong:**
`ir.cron.trigger` (the model, not the `trigger` field) is used to ask the cron to run "as soon as possible". If the BPM engine creates many `ir.cron.trigger` records (one per workflow event), the cron trigger table grows large and slows down the `_get_all_ready_jobs` query.

**Prevention:**
Use `ir.cron._trigger()` which deduplicates triggers — it only creates a new trigger if one is not already pending for the same cron (as shown in `product_images/models/ir_cron_trigger.py`). For BPM, a single "there are pending items" signal is sufficient; the cron will pick up all items in its next batch.

**Phase to address:** Phase 2 (Orchestrator).

---

### Pitfall 17: `with_context(active_test=False)` Forgetting Archived Records

**What goes wrong:**
BPM queries for active workflow steps using the default `active_test=True` domain. A step that was archived (soft-deleted via `active=False`) is skipped by the search. The outbox item for that step has no step to execute, raises a `MissingError`, and leaves the instance stuck.

**Prevention:**
For outbox processing, always use `with_context(active_test=False)` when fetching step definitions by ID. Validate step existence and active status explicitly and handle the "step is archived" case by moving the instance to an error state with a clear message.

**Phase to address:** Phase 2 (Orchestrator).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Core Engine — Trigger hooks | Infinite trigger loop (Pitfall 1) | Context flag guard; do not patch `write` directly |
| Core Engine — Python steps | `exec()` without sandbox (Pitfall 2) | Use `safe_eval` + `test_python_expr` always |
| Core Engine — Eval context | `env` leakage in safe_eval (Pitfall 10) | Minimal eval context; no `env` key |
| Core Engine — Step versioning | Live instances break on definition change (Pitfall 13) | `ondelete='restrict'`, version field |
| Core Engine — Stored computed fields | BPM fires multiple times per save (Pitfall 14) | Trigger only on explicit state fields |
| Orchestrator — Outbox | Two workers claim same step (Pitfall 3) | `FOR NO KEY UPDATE SKIP LOCKED` + idempotency key |
| Orchestrator — Cron overlap | Orchestrator runs concurrently with itself (Pitfall 4) | Advisory lock + batch cap |
| Orchestrator — Memory | Cache growth in long batch loops (Pitfall 6) | `invalidate_all()` per N steps |
| Orchestrator — Performance | N+1 queries in step loop (Pitfall 7) | `mapped()` prefetch before loop |
| Orchestrator — Error handling | Cron retry storm on exception (Pitfall 15) | Savepoint per item; backoff on failure |
| Human Tasks — Assignment | Unassigned task silently blocks workflow (Pitfall 8) | Fallback user; stuck instance detector |
| Human Tasks — Approvals | Empty `approver_ids` blocks forever (Pitfall 12) | Validate approvers before `action_confirm()` |
| Notifications — Templates | Jinja SSTI via user-defined templates (Pitfall 11) | `SandboxedEnvironment` or `mail.template` |
| Parallel Gateways | Deadlock on parallel writes to same record (Pitfall 9) | Join gate; sequential execution for same-record writes |
| Module Integration | ORM hook ordering breaks BPM triggers (Pitfall 5) | Extend `ir.actions.server`; avoid independent monkey-patching |

---

## Sources

- `odoo/ent_addons/base_automation/models/base_automation.py` — Hook lifecycle, recursion guard (`__action_done`), hook deregistration (verified in repo, HIGH confidence)
- `odoo/addons/base/models/ir_cron.py` — `FOR NO KEY UPDATE SKIP LOCKED`, `MAX_BATCH_PER_CRON_JOB`, `_acquire_one_job` (verified in repo, HIGH confidence)
- `odoo/tools/safe_eval.py` — Opcode blacklist, `assert_no_dunder_name`, `_ALLOWED_MODULES` (verified in repo, HIGH confidence)
- `odoo/addons/base/models/ir_actions.py` — `_run_action_code_multi` with `safe_eval`, `_check_python_code` with `test_python_expr`, eval context structure (verified in repo, HIGH confidence)
- `odoo/custom_addons/ept_execute_python_code/models/execute_python.py` — Anti-pattern: raw `exec()` without sandbox (verified in repo, HIGH confidence)
- `odoo/custom_addons/sale_extended_ept/models/sale_order.py` — `approval.request` creation pattern with context guard `from_approval` (verified in repo, HIGH confidence)
- `odoo/ent_addons/product_images/models/ir_cron_trigger.py` — Deduplication pattern for `ir.cron.trigger` (verified in repo, HIGH confidence)
