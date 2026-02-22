# Architecture Patterns: BPM Workflow Engine (Odoo 18)

**Domain:** Async workflow engine embedded in Odoo 18 Enterprise
**Researched:** 2026-02-22
**Confidence:** HIGH — all critical patterns verified against Odoo 18 source in this repo

---

## Executive Assessment

The planned architecture (bpm.outbox + cron orchestrator + executor hierarchy) is sound and
follows patterns already established inside Odoo 18's own codebase. Key sources examined:

- `/home/bashar/odoo18/odoo/addons/base/models/ir_cron.py` — production FOR NO KEY UPDATE SKIP LOCKED
- `/home/bashar/odoo18/odoo/ent_addons/stock/models/stock_quant.py` — production SKIP LOCKED in business logic
- `/home/bashar/odoo18/odoo/tools/sql.py` — utility FOR UPDATE SKIP LOCKED helper
- `/home/bashar/odoo18/odoo/ent_addons/mail/models/mail_thread.py` — AbstractModel ORM override pattern
- `/home/bashar/odoo18/odoo/models.py` — TransientModel, create_multi, flush semantics

This document identifies **verified patterns to follow**, **gotchas that will cause failures**, and the
**correct build order** based on true inter-component dependencies.

---

## Recommended Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  DEFINITION LAYER (build first — pure data, no runtime deps)    │
│  bpm.workflow  →  bpm.workflow.step  →  bpm.action              │
│  bpm.trigger   →  bpm.webhook.endpoint                          │
└─────────────────────────────────────────────────────────────────┘
              ↓ triggers fire into ↓
┌─────────────────────────────────────────────────────────────────┐
│  QUEUE LAYER (build second — the reliability backbone)          │
│  bpm.outbox  (idempotency_key, state, scheduled_at, locked_by)  │
└─────────────────────────────────────────────────────────────────┘
              ↓ cron reads from ↓
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTION LAYER (build third — depends on queue + definitions) │
│  bpm.workflow.instance  →  bpm.instance.step.log                │
│  bpm.parallel.branch    →  bpm.execution.log                    │
└─────────────────────────────────────────────────────────────────┘
              ↓ executors dispatch to ↓
┌─────────────────────────────────────────────────────────────────┐
│  ENGINE LAYER (build fourth — stateless workers)                │
│  trigger_engine.py → orchestrator.py → executors/ → action_executors/ │
└─────────────────────────────────────────────────────────────────┘
              ↓ human work surfaces through ↓
┌─────────────────────────────────────────────────────────────────┐
│  TASK LAYER (build fifth — depends on instances + mail.activity)│
│  bpm.task  →  bpm.task.response                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `bpm.trigger.mixin` | Intercept ORM events, fire trigger engine | trigger_engine.py |
| `trigger_engine.py` | Match events to triggers, write bpm.outbox rows | bpm.outbox, bpm.workflow.instance |
| `bpm.outbox` | Durable queue; survives crashes | orchestrator.py reads it |
| `orchestrator.py` | Dequeue with SKIP LOCKED, dispatch to executors | executors/, bpm.instance.step.log |
| `executors/` | Pure step logic; return result dict, no direct DB writes | action_engine.py, bpm.parallel.branch |
| `action_executors/` | Side-effect workers (email, HTTP, record CRUD) | Odoo mail, requests, ir.actions |
| `bpm.task` | Human-facing work item | mail.activity, orchestrator (resume) |

---

## Patterns to Follow

### Pattern 1: FOR NO KEY UPDATE SKIP LOCKED (not FOR UPDATE)

**What:** Odoo's production code uses `FOR NO KEY UPDATE SKIP LOCKED`, not `FOR UPDATE SKIP LOCKED`.

**Why it matters:** `FOR UPDATE` conflicts with `KEY SHARE` row locks that PostgreSQL acquires
implicitly when foreign keys reference the locked row. This causes unnecessary blocking when
other transactions insert child records (e.g., bpm.instance.step.log rows pointing at a
bpm.outbox row). `FOR NO KEY UPDATE` is weaker — it conflicts with everything except `KEY SHARE`,
so foreign-key references never block queue dequeue.

**Source:** `ir_cron.py` line 295 — comment explains this explicitly:
> "Because we never delete acquired cron jobs, foreign keys are safe to concurrently reference
> cron jobs. Hence, the NO KEY UPDATE row lock is used."

**Implementation for outbox:**
```python
@api.model
def _acquire_batch(self, batch_size=50, worker_id=None):
    """Acquire pending outbox items without blocking sibling workers."""
    self.flush_model()   # Required: flush ORM cache before raw SQL
    self.env.cr.execute("""
        UPDATE bpm_outbox
        SET state = 'processing',
            locked_at = NOW() AT TIME ZONE 'UTC',
            locked_by = %s
        WHERE id IN (
            SELECT id FROM bpm_outbox
            WHERE state = 'pending'
              AND scheduled_at <= NOW() AT TIME ZONE 'UTC'
            ORDER BY scheduled_at, id
            LIMIT %s
            FOR NO KEY UPDATE SKIP LOCKED
        )
        RETURNING id
    """, [worker_id or 'cron', batch_size])
    ids = [row[0] for row in self.env.cr.fetchall()]
    self.invalidate_model(['state', 'locked_at', 'locked_by'])  # sync ORM cache
    return self.browse(ids)
```

**Confidence:** HIGH — verified against Odoo 18 source (ir_cron.py:295, stock_quant.py:1073)

---

### Pattern 2: Cron Opens Its Own Cursor (separate transaction)

**What:** `ir_cron._run_job()` opens a `pool.cursor()` that is entirely separate from the cron
scheduling cursor. It commits with `job_cr.commit()` at end of each batch iteration.

**Why it matters:** The orchestrator's `process_outbox()` must commit each item independently.
If you process 50 items in one transaction and item 30 fails, items 1-29 roll back — they go
back to 'pending' and will re-run on the next tick. This is both a reliability guarantee AND
a performance trap at scale.

**Correct pattern — commit per item:**
```python
@api.model
def process_outbox(self):
    """Called by ir.cron every minute. Processes one batch of outbox items."""
    batch = self._acquire_batch()
    for item in batch:
        try:
            self._process_item(item)
            self.env.cr.commit()   # commit each item independently
        except Exception as e:
            self.env.cr.rollback()
            self._handle_failure(item, str(e))
            self.env.cr.commit()   # commit the failure state
```

**Alternative (savepoint per item within one transaction):**
Use `self.env.cr.savepoint()` if you want atomicity within the batch but isolation between items:
```python
with self.env.cr.savepoint():
    self._process_item(item)
```
Savepoints roll back just that item on failure while the outer transaction continues.

**Recommendation:** Use separate commits per item for maximum resilience. Use savepoints only
if logging failures must be in the same transaction as the failure detection.

**Source:** `ir_cron.py` lines 413-449 — `pool.cursor()` + `job_cr.commit()` per iteration.
**Confidence:** HIGH

---

### Pattern 3: flush_model() Before Raw SQL on ORM-Managed Tables

**What:** The ORM buffers writes in a pending queue. Raw `cr.execute()` queries bypass this
buffer and see stale data unless you flush first.

**Where this bites the outbox:** If trigger_engine writes a `bpm.outbox` row via ORM and the
orchestrator cron immediately runs (same second, different worker), the SKIP LOCKED query
will not see the new row because it hasn't been flushed to the DB yet.

**Fix:**
```python
# In orchestrator._acquire_batch():
self.env['bpm.outbox'].flush_model()   # Push pending ORM writes to DB first

# After raw UPDATE:
self.env['bpm.outbox'].invalidate_model(['state', 'locked_at', 'locked_by'])
```

`flush_model()` was introduced in Odoo 16 and replaces the deprecated `_flush_search()`.
In Odoo 18, `_flush_search` emits a DeprecationWarning (models.py:5706).

**Source:** `models.py` line 5706 confirms `_flush_search` deprecated in 18.0.
**Confidence:** HIGH

---

### Pattern 4: ORM Trigger Mixin — Abstract Model, Not Regular Inheritance

**What:** `bpm.trigger.mixin` must be `models.AbstractModel` with `_name = 'bpm.trigger.mixin'`.
Target models use `_inherit = ['sale.order', 'bpm.trigger.mixin']`.

**Why it matters:**
- AbstractModel creates no database table — it is pure Python mixin behavior.
- The `_inherit` list order matters: `sale.order` must come first so the mixin overrides
  sit on top of the existing model's methods in the MRO chain.
- If you set `_inherit = ['bpm.trigger.mixin', 'sale.order']` (reversed), the mixin's
  `create/write/unlink` will be shadowed by sale.order's implementations.

**Critical ORM behavior:** In Odoo 18, `@api.model_create_multi` is the correct decorator
for `create()` overrides. The older `@api.model` + single dict is deprecated and will cause
warnings or silent failures when bulk-creating records.

```python
class BpmTriggerMixin(models.AbstractModel):
    _name = 'bpm.trigger.mixin'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('bpm_skip_triggers'):
            # Do NOT call trigger engine synchronously here.
            # Write to bpm.outbox instead — never block the user's transaction.
            self._bpm_enqueue_create(records)
        return records

    def write(self, vals):
        old_values = {}
        if not self.env.context.get('bpm_skip_triggers'):
            old_values = self._bpm_capture_old_values(vals)
        result = super().write(vals)
        if not self.env.context.get('bpm_skip_triggers'):
            self._bpm_enqueue_write(self, vals, old_values)
        return result

    def unlink(self):
        if not self.env.context.get('bpm_skip_triggers'):
            self._bpm_enqueue_delete(self)
        return super().unlink()
```

**Source:** `mail_thread.py:256-351` — production ORM mixin override pattern with context flags
(`tracking_disable`, `mail_notrack`). Same pattern used here with `bpm_skip_triggers`.
**Confidence:** HIGH

---

### Pattern 5: Trigger-to-Outbox Must Be Within the SAME Transaction

**What:** The trigger mixin fires when a user writes a record. The workflow instance creation
and the first outbox entry MUST be written in the same transaction as the user's write.

**Why:** If the trigger writes the instance but the user's transaction rolls back (e.g., a
validation error raises after the write), the instance would be orphaned in the DB.

**Correct approach:** Write `bpm.workflow.instance` and `bpm.outbox` via standard ORM inside
the trigger mixin methods. They participate in the user's transaction. If the user's write
commits, so do the instance and outbox entry. If the user's write rolls back, so do they.

**Implication for `_bpm_enqueue_create`:**
```python
def _bpm_enqueue_create(self, records):
    """
    Called inside user's transaction. Create instance + outbox entry.
    Do NOT commit — let the caller's transaction handle commit.
    """
    triggers = self.env['bpm.trigger'].sudo()._get_create_triggers(self._name)
    for trigger in triggers:
        for record in records:
            instance = self.env['bpm.workflow.instance'].sudo().create({...})
            self.env['bpm.outbox'].sudo().create({
                'instance_id': instance.id,
                'idempotency_key': f'create-{self._name}-{record.id}-{trigger.id}',
                ...
            })
```

**Gotcha:** Never call `self.env.cr.commit()` inside a trigger mixin method. This commits
the user's in-progress work prematurely and breaks transaction safety.
**Confidence:** HIGH

---

### Pattern 6: Context Propagation Through Workflow Steps

**What:** Workflow context (the `context_json` blob on `bpm.workflow.instance`) is the shared
state that flows between steps. Executors read it, may add to it, and the orchestrator
merges updates back.

**Odoo constraint:** `env.context` is immutable at the Python level (it's a frozen mapping).
Use `self.env['bpm.workflow.instance'].with_context(...)` only for Odoo's own context keys
(lang, allowed_company_ids, etc.). Never conflate Odoo's env.context with BPM workflow context.

**Recommended pattern:**
```python
# Build execution context for each step
def _build_exec_context(self, instance, step_log):
    return {
        'record': self.env[instance.res_model].browse(instance.res_id),
        'instance': instance,
        'workflow': instance.workflow_id,
        'step': step_log.step_id,
        'user': self.env.user,
        'company': self.env.company,
        'ctx': json.loads(instance.context_json or '{}'),  # workflow-level vars
        'prev_output': json.loads(step_log.input_context or '{}'),
    }

# After step completes, merge context updates
def _merge_context_updates(self, instance, updates):
    current = json.loads(instance.context_json or '{}')
    current.update(updates)
    instance.context_json = json.dumps(current)
```

**Parallel branch context isolation:** Each branch should copy the parent context at split
time but write its own output to its branch-scoped log. The join step aggregates branch
outputs from `bpm.instance.step.log` rows for each branch.
**Confidence:** HIGH (derived from Odoo env/context semantics, verified in models.py)

---

### Pattern 7: Parallel Join — Atomic Check-and-Enqueue

**What:** When a branch completes, it must check whether to trigger the join step. This
check ("am I the last branch?") and the join enqueue must be atomic to prevent two branches
completing simultaneously from both enqueuing the join.

**Implementation using database-level atomicity:**
```python
def _complete_branch(self, branch):
    """Called when a branch finishes. Must be atomic."""
    branch.write({'state': 'done', 'ended_at': fields.Datetime.now()})

    join_step = branch.join_step_id
    split_log = branch.split_step_log_id

    # Count remaining active branches in a single query that locks the rows
    self.env.cr.execute("""
        SELECT COUNT(*) FROM bpm_parallel_branch
        WHERE split_step_log_id = %s
          AND state NOT IN ('done', 'failed', 'cancelled')
        FOR UPDATE
    """, [split_log.id])
    remaining = self.env.cr.fetchone()[0]

    join_type = split_log.step_id.join_type
    should_proceed = (join_type == 'all' and remaining == 0) or \
                     (join_type == 'any' and remaining < total_branches - 1)

    if should_proceed:
        # Cancel remaining branches (for 'any' type)
        if join_type == 'any':
            self._cancel_remaining_branches(split_log)
        # Enqueue join step exactly once (idempotency_key prevents duplication)
        self.env['bpm.outbox'].create({
            'instance_id': branch.instance_id.id,
            'step_id': join_step.id,
            'idempotency_key': f'join-{split_log.id}',
            ...
        })
```

The `idempotency_key` UNIQUE constraint on `bpm.outbox` is the final safety net. If two
branches race past the check, only the first INSERT succeeds; the second raises a unique
violation that can be caught and ignored.
**Confidence:** HIGH (design derived from outbox idempotency principle, verified against planned schema)

---

### Pattern 8: Stale-Lock Recovery for Crashed Workers

**What:** A worker processing an outbox item may crash mid-execution, leaving the item
in `state = 'processing'` with a `locked_at` timestamp but never completing.

**Odoo 18 ir.cron behavior:** Odoo tracks `timed_out_counter` in `ir_cron_progress` table.
It automatically deactivates crons that time out too many consecutive times. The BPM cron
needs its own stale-lock recovery.

**Recovery query — runs at top of each cron tick before acquiring new items:**
```python
@api.model
def _recover_stale_locks(self, stale_after_minutes=10):
    self.env.cr.execute("""
        UPDATE bpm_outbox
        SET state = 'pending', locked_at = NULL, locked_by = NULL
        WHERE state = 'processing'
          AND locked_at < NOW() AT TIME ZONE 'UTC' - INTERVAL '%s minutes'
    """, [stale_after_minutes])
    self.env['bpm.outbox'].invalidate_model()
```

This must run in the orchestrator BEFORE `_acquire_batch()`. The `stale_after_minutes`
value should be longer than the longest expected step execution time (recommend 10 minutes).
**Confidence:** MEDIUM (pattern is established; exact timeout value is environment-specific)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous Execution in Trigger Mixin

**What goes wrong:** Calling `trigger_engine.fire()` → `orchestrator.execute_step()` directly
inside the mixin's `write()` override.

**Why bad:**
- Blocks the user's save operation for the full workflow execution time.
- If a step fails, it raises an exception into the user's write and rolls back their change.
- Creates unbounded call depth when actions write records that have the mixin.

**Instead:** Mixin writes to `bpm.outbox` only. Orchestrator runs via cron.

---

### Anti-Pattern 2: FOR UPDATE Without SKIP LOCKED

**What goes wrong:** Two cron workers both try to acquire outbox items. Without `SKIP LOCKED`,
the second worker blocks until the first commits. Both then process the same items.

**Why bad:** Duplicate execution. Items marked 'processing' by worker 1 are re-acquired by
worker 2 when it unblocks.

**Instead:** Always use `FOR NO KEY UPDATE SKIP LOCKED`. Items already locked by worker 1
are invisibly skipped by worker 2.

---

### Anti-Pattern 3: Single Transaction for Entire Batch

**What goes wrong:** Acquiring 50 outbox items and processing them all in one transaction,
then committing at the end.

**Why bad:** A failure on item 30 rolls back items 1-29 as well. They return to 'pending'
with their attempt counts not incremented. The retry counter never works correctly.

**Instead:** Commit (or rollback) after each item, or use savepoints per item.

---

### Anti-Pattern 4: Recursive Trigger Loops Without Context Guard

**What goes wrong:** A workflow action updates a field on a record that has `bpm.trigger.mixin`.
This fires another trigger. Which fires another action. Stack overflow.

**Why bad:** System crashes, locks pile up, users cannot save records.

**Verified prevention:** The `bpm_skip_triggers` context flag is the correct mechanism.
Mail.thread uses exactly this pattern: `tracking_disable`, `mail_notrack`, `mail_create_nolog`
(verified in mail_thread.py:263-310).

```python
# In action executors that write records
def _update_record_safely(self, record, vals):
    record.with_context(bpm_skip_triggers=True).write(vals)
```

All action executors that write Odoo records MUST set this context flag.

---

### Anti-Pattern 5: TransientModel for Orchestrator/Executors with Long Lifetimes

**What goes wrong:** TransientModel records are auto-vacuumed by Odoo after `_transient_max_hours`
(default 1 hour). If the orchestrator or executor uses TransientModel to store state, that
state may vanish mid-execution.

**Why bad:** `BpmOrchestrator(models.TransientModel)` as shown in the architecture plan is fine
for the orchestrator itself (it holds no persistent state — it's just a method host). But any
state that must survive beyond a single cron tick must be in a proper `Model`, not `TransientModel`.

**Rule:** Use `TransientModel` for the orchestrator/executors as method namespaces only.
All runtime state lives in `bpm.workflow.instance`, `bpm.instance.step.log`, `bpm.outbox`.
**Confidence:** HIGH (verified TransientModel vacuum behavior in models.py:651-654)

---

### Anti-Pattern 6: Using `_flush_search()` in Odoo 18

**What goes wrong:** Any code calling `_flush_search()` will emit a DeprecationWarning in
Odoo 18 (models.py:5706). This is dead code from Odoo 16.

**Instead:** Use `flush_model()`, `flush_recordset()`, or `self.env.flush_all()` depending
on scope needed.

---

## Build Order (Mandatory Sequence)

Build phases have hard dependencies. Skipping this order causes import errors or missing
foreign key references.

```
Phase 1: Module scaffold + security groups
         (no dependencies — enables subsequent model registration)

Phase 2: Definition models — pure schema, no engine deps
         bpm.workflow → bpm.workflow.step → bpm.action → bpm.action.field.map
         bpm.trigger → bpm.webhook.endpoint → bpm.schedule.job

Phase 3: Queue and execution schema
         bpm.outbox (referenced by everything downstream)
         bpm.workflow.instance → bpm.instance.step.log
         bpm.parallel.branch → bpm.execution.log
         bpm.config.setting → bpm.action.registry

         CRITICAL: bpm.outbox must exist before trigger_engine.py can write to it.
         Do not skip to Phase 4 without Phase 3 working end-to-end.

Phase 4: ORM Trigger Mixin (bpm.trigger.mixin as AbstractModel)
         — depends on bpm.outbox existing (writes to it)
         — test with one model only (e.g., sale.order) before enabling globally

Phase 5: Trigger Engine (trigger_engine.py)
         — reads bpm.trigger config (Phase 2)
         — writes bpm.workflow.instance + bpm.outbox (Phase 3)
         — no step execution yet; just event → queue

Phase 6: Orchestrator (orchestrator.py) + Base Executor
         — reads bpm.outbox (Phase 3)
         — implements SKIP LOCKED acquire + stale lock recovery
         — implements commit-per-item transaction pattern
         — wire up ir.cron job (1 minute interval)
         — at this point: outbox items are dequeued but not processed (executor is a stub)

Phase 7: Step Executors (executors/)
         condition → delay → stop (simplest first, validates executor contract)
         human_task → wait_event (introduces task model dependency)
         parallel_split → parallel_join (most complex; requires bpm.parallel.branch)

Phase 8: Action Engine + Action Executors (action_executors/)
         update_record → create_record (must set bpm_skip_triggers context)
         send_email → create_activity (mail integration)
         http_request → webhook_call (external I/O; needs timeout + retry)
         execute_python (highest risk; build last, test hardest)

Phase 9: Human Task System
         bpm.task → bpm.task.response → mail.activity integration → escalation cron

Phase 10: Webhook Controller + REST API
          (external surface; build after internal engine is stable)

Phase 11: Dashboard + Monitoring Views
          (UI layer; depends on all execution models existing)

Phase 12: Configuration UI, Wizards, Polish

Phase 13: Tests
          Unit test each executor independently
          Integration test: trigger → outbox → execute → instance complete
          Concurrency test: two workers, SKIP LOCKED, no duplicates
```

---

## Critical Integration Points

### Integration Point 1: Trigger Mixin ↔ ORM Override Chain

When `sale.order` inherits both `mail.thread` and `bpm.trigger.mixin`, the MRO determines
execution order. Both mixins override `create/write/unlink`. The order of `_inherit` list
controls which mixin's `super()` calls which.

**Safe pattern:**
```python
class SaleOrder(models.Model):
    _inherit = ['sale.order', 'bpm.trigger.mixin']
    # bpm.trigger.mixin sits on top of sale.order in MRO
    # mail.thread is already in sale.order's MRO
    # BPM fires AFTER mail.thread's tracking (correct)
```

**Validate with:** `SaleOrder.__mro__` in a shell to confirm order.

### Integration Point 2: Outbox → Cron → Separate DB Cursor

The cron's `ir_cron._run_job()` opens a fresh `pool.cursor()`. The BPM orchestrator executes
in this fresh cursor context. This means:

- `self.env.cr` in the orchestrator is a DIFFERENT connection than the trigger that wrote the outbox entry.
- This is intentional and correct. The trigger's transaction committed; the orchestrator reads committed data.
- Do NOT expect env.cache state from the triggering request to be present in the orchestrator.

### Integration Point 3: bpm.task Resume ↔ Orchestrator

When a user approves/rejects a task (`bpm.task.action_approve()`), it must resume the paused
workflow instance. Resume = write a new `bpm.outbox` entry pointing at the `on_approve_step_id`.

The user's `action_approve()` call runs in the user's web request transaction. The new outbox
entry commits with that transaction. The orchestrator picks it up on the next cron tick.

This means task approval has a ~1 minute latency before the next step executes. Acceptable for
human approval workflows. Document this as expected behavior.

### Integration Point 4: Parallel Branch Join — Race Condition Window

Two branches completing within the same cron tick (same second) will both call `_complete_branch()`.
The `FOR UPDATE` lock on `bpm_parallel_branch` rows in `_complete_branch()` plus the UNIQUE
constraint on `bpm.outbox.idempotency_key` are the two-layer protection:

- Layer 1: `FOR UPDATE` on branch rows forces serial execution of `_complete_branch()` for
  the same split step — only one wins the check.
- Layer 2: Even if layer 1 fails (e.g., different transactions), the UNIQUE constraint on
  `idempotency_key` makes the second INSERT fail, which is caught and ignored.

Both layers are required. Implementing only one is insufficient.

---

## Scalability Considerations

| Concern | At 100 instances | At 10K instances | At 1M instances |
|---------|-----------------|-----------------|-----------------|
| Outbox query | Single index scan on (state, scheduled_at) | Same, but add partial index WHERE state='pending' | Partition bpm_outbox by scheduled_at month |
| Cron frequency | 1 cron job, batch=50 | Multiple cron replicas or batch=500 | Dedicated worker processes (Celery/Dramatiq) |
| Instance log growth | Keep all logs | Retention policy: purge logs > 90 days | Separate log DB or object storage |
| Parallel branches | No issue | Monitor bpm_parallel_branch count | Archive completed branches |
| Trigger cache | In-memory dict, fine | Fine | Shard by model_name hash |

**Immediate recommendation:** Add partial index on `bpm_outbox` at schema creation time:
```sql
CREATE INDEX idx_bpm_outbox_pending ON bpm_outbox(scheduled_at, id)
WHERE state = 'pending';
```
This index is smaller and faster than a full-table index for the hot query path.

---

## Recommended Changes vs Planned Architecture

### Change 1: Use FOR NO KEY UPDATE, not FOR UPDATE (MEDIUM priority)

The plan's SQL uses `FOR UPDATE SKIP LOCKED`. Change to `FOR NO KEY UPDATE SKIP LOCKED`
to avoid blocking foreign key references from step logs pointing at outbox rows.

### Change 2: Commit Per Item, Not Per Batch (HIGH priority)

The plan describes a batch pattern but does not make explicit whether commit is per-item
or per-batch. Must be per-item (or savepoint per item within batch). Document this explicitly.

### Change 3: Add `_recover_stale_locks()` at Top of Each Cron Tick (HIGH priority)

Not mentioned in existing plans. Without this, crashed workers leave items permanently stuck
in `state = 'processing'`. Add it before `_acquire_batch()`.

### Change 4: Add Partial Index on bpm_outbox (LOW priority, big payoff)

The schema defines a standard index on `(state, scheduled_at)`. A partial index
`WHERE state = 'pending'` is smaller, faster, and avoids dead rows from completed items
slowing down the hot path.

### Change 5: Validate MRO Order for Target Model Inheritance (MEDIUM priority)

The plan shows `_inherit = ['sale.order', 'bpm.trigger.mixin']` — this is correct. Add a
comment or test that verifies this order is intentional and documents the consequence of
reversing it.

### Change 6: bpm.trigger.mixin Must Not Store State in AbstractModel (LOW priority)

Abstract models share no table. If the mixin has any stored `fields.*` declarations, Odoo
will raise an error at module install. Mixin methods should use `self.env['bpm.outbox']`
to read/write, not fields on the mixin itself.

---

## Odoo 18 ORM Behaviors That Affect the Design

### Transaction Behavior

Odoo 18 uses one PostgreSQL transaction per HTTP request (or per cron execution). The ORM
does NOT auto-commit between `write()` calls. All writes in a request are either committed
together at the end or rolled back together on exception.

**Impact on BPM:** The trigger mixin writes to `bpm.outbox` inside the user's transaction.
If the user's request fails AFTER the outbox write but BEFORE commit, the outbox entry
disappears. This is correct — no orphaned workflow instances. The trade-off is that a crash
right after the user's form saves but before the HTTP response is sent means the outbox
entry may or may not exist depending on whether the transaction committed.

### ORM Cache and Raw SQL

When mixing ORM writes and raw `cr.execute()` on the same table:
- ORM writes go to a pending buffer, not immediately to DB.
- Raw `cr.execute()` reads from DB, bypassing the ORM buffer.
- Always call `flush_model()` before raw reads on the same table.
- Always call `invalidate_model()` after raw writes to the same table.

### Deprecated APIs in Odoo 18

| Deprecated | Replacement | Notes |
|------------|-------------|-------|
| `_flush_search()` | `flush_model()` / `flush_recordset()` | Warns in 18.0 |
| `@api.model create(self, vals)` (single dict) | `@api.model_create_multi` | Use list of dicts |
| `self.env.cr.execute()` without flush | flush_model() first | Silent data inconsistency |

---

## Sources

| Source | Confidence | What It Establishes |
|--------|-----------|---------------------|
| `/home/bashar/odoo18/odoo/addons/base/models/ir_cron.py:253-295` | HIGH | FOR NO KEY UPDATE SKIP LOCKED pattern, per-item commit, separate cursor |
| `/home/bashar/odoo18/odoo/ent_addons/stock/models/stock_quant.py:1073` | HIGH | FOR NO KEY UPDATE SKIP LOCKED in production business logic |
| `/home/bashar/odoo18/odoo/tools/sql.py:645` | HIGH | FOR UPDATE SKIP LOCKED utility (simpler case without FK concerns) |
| `/home/bashar/odoo18/odoo/ent_addons/mail/models/mail_thread.py:256-351` | HIGH | AbstractModel ORM override pattern with context skip flags |
| `/home/bashar/odoo18/odoo/models.py:5706` | HIGH | `_flush_search()` deprecated in 18.0 |
| `/home/bashar/odoo18/odoo/models.py:651-654` | HIGH | TransientModel vacuum limits |
| `/home/bashar/odoo18/odoo/models.py:4949-4950` | HIGH | `@api.model_create_multi` as correct create decorator |
| `/home/bashar/odoo18/docs/plans/2026-01-30-bpm-architecture-review.md` | HIGH | Planned component structure and design decisions |
