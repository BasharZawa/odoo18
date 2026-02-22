# Project Research Summary

**Project:** bpm_automation — Odoo 18 Enterprise BPM Workflow Engine
**Domain:** Async multi-step workflow / BPM engine embedded in Odoo 18
**Researched:** 2026-02-22
**Confidence:** HIGH

## Executive Summary

The BPM automation engine fills a clear gap in Odoo 18's native tooling. While `base_automation` (ir.automation) provides powerful single-trigger-single-action rules and `marketing_automation` offers multi-step flows for email campaigns, neither supports what businesses actually need: multi-step sequential workflows with instance tracking, conditional branching, delay steps, and human task integration across arbitrary Odoo models. Every piece of infrastructure needed to build this engine already exists inside Odoo 18 -- `ir.cron` with `FOR NO KEY UPDATE SKIP LOCKED` for queue processing, `safe_eval` for sandboxed expression evaluation, `mail.template` for notifications, `ir.actions.server` for action delegation, and the `base_automation._register_hook()` pattern for ORM event interception. No external dependencies (Celery, Redis, Jinja2, BPMN libraries) are needed or advisable.

The recommended approach is an outbox-driven architecture with four distinct layers: definition models (workflow/step/trigger schema), a durable queue (`bpm.outbox` with SKIP LOCKED dequeue), an execution layer (workflow instances with per-step audit logs), and stateless engine workers (orchestrator + action executors). This architecture directly mirrors patterns already proven in Odoo 18's own cron system and stock quant reservation logic. The build order is strictly dictated by foreign key dependencies: schema first, queue second, trigger mixin third, orchestrator fourth, action executors fifth, human tasks sixth.

The primary risks are: (1) infinite trigger loops when BPM actions write back to watched models -- mitigated by a `bpm_skip_triggers` context flag modeled on `mail.thread`'s `tracking_disable`; (2) duplicate step execution from concurrent cron workers -- mitigated by `FOR NO KEY UPDATE SKIP LOCKED` plus idempotency keys; (3) security exposure from `safe_eval` contexts that include the full `env` object -- mitigated by restricting eval context to `record` plus primitive helpers only; and (4) ORM hook conflicts with `base_automation` when both modules patch `create`/`write` -- mitigated by extending `ir.actions.server` with a custom action type rather than independent monkey-patching. All four risks have verified prevention patterns from Odoo 18 source code.

## Key Findings

### Recommended Stack

The entire engine runs on Odoo 18's native stack with zero external dependencies. The key insight from stack research is that Odoo 18 has significantly improved its async processing infrastructure compared to earlier versions -- `FOR NO KEY UPDATE SKIP LOCKED` (replacing the old `FOR UPDATE`), the `ir.cron.progress` model with `_notify_progress()`, and the `odoo.tools.SQL` class for injection-safe raw queries are all new or improved in v18.

**Core technologies:**
- **Odoo ORM (models.Model):** All BPM entities as persistent models -- transactions, access control, search, and views come free
- **ir.cron + ir.cron.trigger:** Outbox poll orchestrator and delay/timer steps -- built-in distributed locking via SKIP LOCKED
- **PostgreSQL FOR NO KEY UPDATE SKIP LOCKED:** Queue worker exclusion -- weaker lock that avoids FK-reference deadlocks (critical difference from FOR UPDATE)
- **odoo.tools.safe_eval:** Condition expression and Python step evaluation -- bytecode-level opcode whitelist, already used by ir.actions.server
- **mail.render.mixin + inline_template:** Dynamic string rendering -- use `{{ expr }}` syntax backed by safe_eval, NOT Jinja2 directly
- **ir.actions.server delegation:** Action executors can delegate to native Odoo action types via `.run()` with proper context
- **cr.postcommit.add():** Wake orchestrator cron after outbox row is committed -- prevents processing before data is visible

**Critical version requirements:** Odoo 18.0+ mandatory. The `FOR NO KEY UPDATE` lock level, `ir.cron.progress`, `_notify_progress()`, and `SQL` class are 18-specific. Backporting to 16/17 would require rewriting the queue layer.

### Expected Features

**Must have (table stakes) -- without these, the module is just a wrapper around base.automation:**
- Multi-step sequential flow (trigger -> step 1 -> condition -> step 2 -> ...)
- Conditional branching (if/else routing, not just abort)
- Execution instance tracking ("record X is at step 3 of flow Y")
- All trigger types: on_create, on_write, on_delete, on_field_change, scheduled, deadline, webhook, manual
- All action executors: update_record, create_record, send_email, send_message, create_activity, http_request, execute_python, server_action
- Delay step (time-based wait mid-flow)
- Per-step filter/condition evaluation
- Audit log / execution history per workflow instance
- Error handling per step (stop vs. continue on failure)

**Should have (differentiators) -- the reasons to build this over using base.automation:**
- Parallel split/join ("notify team A AND send to system B, continue when both done")
- Human task step with assignment logic and fallback users
- Wait-event step ("wait until invoice is confirmed before proceeding")
- Per-step retry policy with exponential backoff
- Cross-object triggers ("when child picking is done, trigger flow on parent sale order")
- Manual trigger with optional context form
- Read-only visual flow view (ordered step list, not drag-drop canvas)

**Defer to v2+:**
- Full drag-drop visual flow builder (massive frontend investment, anti-feature for v1)
- Flow versioning (solve with "create new flow, deactivate old" in v1)
- Sub-process / reusable sub-flows (composition complexity, recursion risks)
- SLA/KPI monitoring dashboards (build after data model is proven)
- BPMN 2.0 import/export (zero real demand in Odoo shops)

### Architecture Approach

The architecture follows a layered outbox pattern: Definition Layer (pure schema, no runtime deps) -> Queue Layer (bpm.outbox as durable queue) -> Execution Layer (workflow instances, step logs) -> Engine Layer (stateless workers) -> Task Layer (human work items). Each layer depends only on the one above it. The outbox pattern decouples trigger detection from step execution -- the trigger mixin writes to the outbox within the user's transaction (ensuring atomicity), and the cron-driven orchestrator dequeues and processes items in separate transactions (ensuring isolation and fault tolerance).

**Major components:**
1. **bpm.trigger.mixin** (AbstractModel) -- intercepts ORM create/write/unlink events, writes outbox entries within the user's transaction
2. **bpm.outbox** -- durable queue with SKIP LOCKED dequeue, idempotency keys, and stale-lock recovery
3. **trigger_engine.py** -- matches ORM events to configured triggers, creates workflow instances
4. **orchestrator.py** -- cron-driven batch processor with per-item commit, advisory lock for overlap prevention, cache invalidation
5. **executors/** -- per-step-type logic (condition, delay, parallel_split, parallel_join, human_task, wait_event)
6. **action_executors/** -- per-action-type workers (update_record, create_record, send_email, http_request, execute_python)
7. **bpm.task** -- human-facing work items backed by mail.activity, with resume-via-outbox pattern

### Critical Pitfalls

1. **Infinite trigger loops** -- BPM actions writing to watched models re-fire triggers endlessly. **Prevent:** `bpm_skip_triggers` context flag on all BPM-driven writes, modeled on mail.thread's `tracking_disable`. Must be in place before any write-back logic.

2. **Duplicate step execution from concurrent workers** -- Two cron workers claim the same outbox item without row locking. **Prevent:** `FOR NO KEY UPDATE SKIP LOCKED` on outbox queries + idempotency key UNIQUE constraint as a second safety layer. Never use ORM `search()` for outbox polling.

3. **safe_eval context leakage** -- Exposing full `env` in eval context allows unrestricted database access bypassing all ACLs. **Prevent:** Eval context for expression fields contains only `record` and primitives. Full `env` access (for Python code steps) gated behind `base.group_system` and runs under restricted user.

4. **ORM hook conflicts with base_automation** -- Both modules patching `create`/`write` causes silent trigger deregistration when automation rules are edited. **Prevent:** Extend `ir.actions.server` with custom action type rather than independent monkey-patching. Alternatively, use `_register_hook` lifecycle with proper deregistration handling.

5. **Cron overlap and memory leaks** -- Long-running orchestrator batches cause concurrent cron instances and unbounded cache growth. **Prevent:** Advisory lock at orchestrator start, batch cap of N items per cron run, `invalidate_all()` every 100 steps, commit-per-item pattern.

## Implications for Roadmap

Based on combined research, the build order is dictated by hard foreign-key dependencies and the principle of proving the hardest architectural risk first. The execution instance model is the foundation everything depends on; no differentiator works without it.

### Phase 1: Module Foundation and Definition Schema
**Rationale:** Every subsequent phase depends on the definition models existing. No runtime code can be written without the schema to configure against. Security groups must be defined before any model access.
**Delivers:** Installable module with workflow definition CRUD (create/read/update workflows, steps, triggers, actions), security groups, and access rights. No runtime execution yet.
**Features addressed:** Active/inactive toggle per flow, workflow definition model
**Pitfalls to avoid:** Pitfall 13 (definition changes breaking instances) -- add `ondelete='restrict'` on step foreign keys and a version/active flag from day one
**Architecture components:** Definition Layer models (bpm.workflow, bpm.workflow.step, bpm.action, bpm.trigger)

### Phase 2: Outbox Queue and Orchestrator Core
**Rationale:** The outbox is the reliability backbone. Proving that items are enqueued, dequeued with SKIP LOCKED, and processed with per-item commit validates the entire async architecture before any business logic is added.
**Delivers:** bpm.outbox model with SKIP LOCKED dequeue, stale-lock recovery, cron job, advisory lock overlap prevention, batch cap, per-item commit. Orchestrator dequeues items but dispatches to a stub executor.
**Features addressed:** Error handling foundation, execution instance tracking (bpm.workflow.instance created here)
**Pitfalls to avoid:** Pitfall 3 (duplicate execution), Pitfall 4 (cron overlap), Pitfall 6 (memory leaks), Pitfall 7 (N+1 queries), Pitfall 15 (cron retry storm)
**Architecture components:** Queue Layer (bpm.outbox), Execution Layer (bpm.workflow.instance, bpm.instance.step.log)

### Phase 3: Trigger Engine and ORM Mixin
**Rationale:** Cannot test the full pipeline without events flowing into the outbox. The trigger mixin is the entry point. Must be built after the outbox exists (writes to it) and after the definition schema exists (reads triggers from it).
**Delivers:** bpm.trigger.mixin (AbstractModel), trigger_engine.py matching ORM events to triggers, webhook controller for external triggers. End-to-end: user saves record -> trigger fires -> outbox entry -> orchestrator dequeues.
**Features addressed:** All trigger types (on_create, on_write, on_delete, on_field_change, webhook, manual)
**Pitfalls to avoid:** Pitfall 1 (infinite loops) -- context flag guard; Pitfall 5 (ORM hook conflicts) -- extend ir.actions.server or use _register_hook properly; Pitfall 14 (computed field cascades) -- trigger only on explicit state fields
**Architecture components:** Trigger Mixin, Trigger Engine, Webhook Controller

### Phase 4: Sequential Steps, Conditions, and Delays
**Rationale:** These three step types together prove the core value proposition: "trigger -> action -> wait 3 days -> check condition -> route to different actions." This is what base.automation cannot do.
**Delivers:** Step executor dispatch, condition step (domain evaluation with if/else branching), delay step (cron-driven wait with resume), sequential step chaining.
**Features addressed:** Multi-step sequential flow, conditional branching, delay step, per-step filter/condition
**Pitfalls to avoid:** Pitfall 17 (archived steps) -- use `active_test=False` when fetching step definitions
**Architecture components:** Executors (condition, delay, stop)

### Phase 5: Action Executors
**Rationale:** Action executors give the engine practical utility. Without them, the engine can orchestrate but cannot do anything useful. Build from safest to riskiest: record CRUD -> email/activity -> HTTP -> Python code.
**Delivers:** All action executor types: update_record, create_record, link_records, send_email, send_message, send_sms, create_activity, http_request, webhook_call, execute_python, server_action delegation.
**Features addressed:** All action executors from spec
**Pitfalls to avoid:** Pitfall 1 (loop prevention) -- all record-writing executors MUST set `bpm_skip_triggers=True`; Pitfall 2 (raw exec) -- use safe_eval exclusively; Pitfall 10 (env leakage) -- restricted eval context for expression fields, group_system gate for code fields
**Architecture components:** Action Executors, Action Engine

### Phase 6: Audit Log and Monitoring
**Rationale:** Before exposing to real users, the engine needs observability. Audit logs make debugging possible and adoption viable. This phase also adds the monitoring views needed by operations teams.
**Delivers:** Per-instance execution history, per-step timing and status, error log with stack traces, instance list/form/search views, stuck instance detection.
**Features addressed:** Audit log / execution history, error handling visibility
**Architecture components:** bpm.execution.log, dashboard views

### Phase 7: Human Tasks and Approval Integration
**Rationale:** Human task steps depend on a stable instance model (to pause/resume) and a stable outbox (to re-enqueue on task completion). Building this before the engine is proven creates untestable complexity.
**Delivers:** bpm.task model backed by mail.activity, assignment logic with fallback users, integration with approval.request (not replacing it), task completion resuming workflow via outbox entry, escalation cron for overdue tasks.
**Features addressed:** Human task step, wait-event step, approval integration
**Pitfalls to avoid:** Pitfall 8 (unassigned task blocks workflow) -- validate assignee before creation, fallback user; Pitfall 12 (empty approver_ids) -- validate before action_confirm()
**Architecture components:** Task Layer (bpm.task, bpm.task.response)

### Phase 8: Parallel Split/Join
**Rationale:** Most complex orchestration feature. Requires rock-solid instance tracking and outbox idempotency. The atomic join check and double-layer race protection (FOR UPDATE + idempotency_key UNIQUE) demand careful implementation.
**Delivers:** Parallel split step (fork into N branches), parallel join step (wait for all/any), branch-scoped context isolation, atomic join gate.
**Features addressed:** Parallel split/join
**Pitfalls to avoid:** Pitfall 9 (parallel branch deadlock) -- branches must not write to the same record; enforce at definition time or use join gate to serialize writes
**Architecture components:** bpm.parallel.branch, parallel_split/parallel_join executors

### Phase 9: Polish, Testing, and Configuration UI
**Rationale:** After all runtime features work, build the user-facing configuration experience and comprehensive test suite.
**Delivers:** Configuration wizards, read-only flow visualization (ordered step list view), comprehensive unit/integration/concurrency tests, documentation.
**Features addressed:** Read-only visual flow view, per-step retry policy configuration UI
**Architecture components:** Views, wizards, test suite

### Phase Ordering Rationale

- **Phases 1-3 are strictly sequential** due to foreign key dependencies: definition schema -> outbox/instances -> trigger mixin (writes to outbox)
- **Phases 4-5 are the value delivery phases** and can be partially parallelized (step executors and action executors are independent dispatch targets)
- **Phase 6 before Phase 7** because human tasks need debugging infrastructure to be testable in a real environment
- **Phase 7 before Phase 8** because human tasks are far more commonly needed than parallel gateways and validate the pause/resume mechanism that parallel joins also use
- **Phase 8 is deliberately last** among runtime features because parallel execution is the highest-complexity, lowest-frequency feature -- most real workflows are sequential with conditions
- This ordering front-loads architectural risk (outbox + SKIP LOCKED + trigger loops) and back-loads feature complexity (parallel joins, human tasks)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Trigger Engine):** The decision between extending `ir.actions.server` vs. independent ORM patching has significant implications. Needs hands-on prototyping of both approaches with base_automation installed and rules being edited.
- **Phase 7 (Human Tasks):** Integration with `approval.request` needs careful scoping -- the boundary between "BPM task" and "approval request" must be defined precisely. Research how existing EPT modules create approval.requests.
- **Phase 8 (Parallel Split/Join):** The atomic join check pattern needs concurrency testing under actual multi-worker Odoo deployment. The two-layer protection (FOR UPDATE + idempotency UNIQUE) is theoretically sound but untested in this codebase.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Module Foundation):** Standard Odoo module scaffold -- well-documented, no unknowns.
- **Phase 2 (Outbox/Orchestrator):** Pattern directly copied from ir_cron.py with verified source code references. All SQL patterns are established.
- **Phase 5 (Action Executors):** Each executor delegates to existing Odoo APIs (mail.template, ir.actions.server, safe_eval). Patterns are individually well-documented.
- **Phase 6 (Audit/Monitoring):** Standard model + views, no architectural risk.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings verified directly from Odoo 18 source code in this repo. Zero external dependencies needed. Every API signature confirmed with line numbers. |
| Features | HIGH | Gap analysis performed against actual base_automation, marketing_automation, and web_studio source. Feature dependencies mapped from code inspection, not assumptions. |
| Architecture | HIGH | Every critical pattern (SKIP LOCKED, per-item commit, flush_model, AbstractModel mixin, context flags) verified against production Odoo 18 code with file paths and line numbers. |
| Pitfalls | HIGH | All 17 pitfalls sourced from actual Odoo 18 code behavior or existing anti-patterns in this codebase (e.g., ept_execute_python_code using raw exec). Prevention patterns verified against Odoo's own solutions to the same problems. |

**Overall confidence:** HIGH

### Gaps to Address

- **Trigger approach decision:** Extending `ir.actions.server` vs. independent `_register_hook` patching. Research provides arguments for both; the final decision requires a prototype spike in Phase 3 planning.
- **Performance benchmarks:** No load testing data exists for the outbox pattern at scale. The batch cap value (50? 100? 500?) needs tuning during Phase 2 implementation.
- **Stale lock timeout value:** Architecture research recommends 10 minutes but notes this is environment-specific. Needs to be configurable via `bpm.config.setting`.
- **Cross-object triggers:** Identified as a differentiator but architecture details are thin. Requires dedicated design work if included before Phase 8.
- **eval context security boundary:** The exact set of helpers to expose in non-code eval contexts (domain expressions, field mappings) needs specification during Phase 5 planning. The principle is clear (no `env`), but the specific allowed functions need enumeration.

## Sources

### Primary (HIGH confidence -- verified from Odoo 18 source in this repo)
- `odoo/addons/base/models/ir_cron.py` -- SKIP LOCKED queue pattern, cron progress, trigger API
- `odoo/addons/base/models/ir_actions.py` -- eval context, action runner, server action states
- `odoo/tools/safe_eval.py` -- opcode whitelist, test_python_expr, allowed builtins
- `odoo/tools/rendering_tools.py` -- inline template parsing and rendering
- `odoo/tools/sql.py` -- SQL class for injection-safe queries
- `odoo/sql_db.py` -- postcommit/precommit cursor callbacks
- `odoo/models.py` -- flush_model, TransientModel vacuum, create_multi decorator
- `odoo/ent_addons/base_automation/models/base_automation.py` -- hook lifecycle, recursion guard, trigger types
- `odoo/ent_addons/base_automation/controllers/main.py` -- webhook controller pattern
- `odoo/ent_addons/mail/models/mail_thread.py` -- AbstractModel mixin override pattern with context flags
- `odoo/ent_addons/mail/models/mail_template.py` -- send_mail/send_mail_batch API
- `odoo/ent_addons/marketing_automation/models/marketing_activity.py` -- multi-step flow reference (domain-locked)
- `odoo/ent_addons/web_studio/models/studio_approval.py` -- Studio approval model (separate from approval.request)
- `odoo/ent_addons/stock/models/stock_quant.py` -- SKIP LOCKED in production business logic
- `odoo/custom_addons/ept_execute_python_code/` -- anti-pattern: raw exec() without sandbox
- `odoo/custom_addons/sale_extended_ept/` -- approval.request creation pattern

### Secondary (MEDIUM confidence)
- `docs/plans/2026-01-30-bpm-architecture-review.md` -- planned component structure (design document, not verified implementation)

### Tertiary (LOW confidence)
- Stale lock timeout value (10 minutes) -- reasonable default but environment-specific, needs tuning
- Batch size recommendations -- extrapolated from Odoo's `MAX_BATCH_PER_CRON_JOB = 10`, needs load testing

---
*Research completed: 2026-02-22*
*Ready for roadmap: yes*
