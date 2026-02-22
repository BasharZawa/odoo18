# Feature Landscape: BPM Automation Engine for Odoo 18

**Domain:** Workflow / BPM automation engine — Odoo 18 Enterprise custom module
**Researched:** 2026-02-22
**Confidence:** HIGH (primary source: direct codebase inspection of Odoo 18 base_automation, ir.actions.server, marketing_automation, web_studio models)

---

## Context: What Native Odoo Already Provides

This section is critical. Building what already exists wastes roadmap phases. Building what doesn't exist is the project's reason for being.

### ir.automation (base.automation) — Verified HIGH confidence

Source: `/home/bashar/odoo18/addons/base_automation/models/base_automation.py`

**Triggers it has:**
- `on_create`, `on_write`, `on_create_or_write` — record lifecycle
- `on_stage_set`, `on_state_set`, `on_priority_set`, `on_tag_set`, `on_user_set` — field-specific shortcuts
- `on_archive`, `on_unarchive` — archival
- `on_unlink` — deletion
- `on_change` — UI-only onchange (no persistence)
- `on_time`, `on_time_created`, `on_time_updated` — date-based scheduled
- `on_message_received`, `on_message_sent` — mail thread events
- `on_webhook` — incoming webhook with UUID-based URL and configurable payload parser

**Actions it has (via ir.actions.server):**
- `object_write` — update record fields
- `object_create` — create related record
- `code` — execute Python (admin only)
- `webhook` — POST to external URL
- `multi` — chain multiple server actions
- `mail_post` — send email via template (mail module)
- `next_activity` — create activity (mail module)
- `followers`, `remove_followers` — chatter followers (mail module)
- `sms` — send SMS via template (sms module)
- `whatsapp` — send WhatsApp message (ent whatsapp module)

**What it CANNOT do:**
- No multi-step sequential flow (trigger → step 1 → condition → step 2 → ...). Each rule is independent.
- No parallel branches / joins
- No human task / wait-for-approval step within a flow
- No wait-for-event mid-flow
- No instance state tracking (no concept of "this record is on step 3 of workflow X")
- No visual flow designer
- No retry / error handling per step
- No execution history / audit log per workflow instance
- No cross-record orchestration (can't wait for a child record to reach a state)
- Filter conditions exist but no branching — filters abort the whole rule, not route to alternate path

### Odoo Studio Workflows — Verified HIGH confidence

Source: `/home/bashar/odoo18/odoo/ent_addons/web_studio/models/studio_approval.py`

Studio adds `studio.approval.rule` — button-gated approval flows on any model. This is separate from `approval.request`. Studio approval is UI-button oriented, not process-oriented. It does not add workflow sequencing.

Studio's automation contribution is: a GUI wrapper over base.automation creation. It doesn't extend the underlying capability.

### marketing_automation — Verified HIGH confidence

Source: `/home/bashar/odoo18/odoo/ent_addons/marketing_automation/models/marketing_activity.py`

Marketing automation has a tree-structured flow (parent_id → child_ids) with conditional branching based on mail engagement events (open, click, bounce, reply). Activity types: `email` or `action` (server action). This is the closest native Odoo has to a multi-step flow — but it is domain-locked to mass mailing campaigns. Not generalizable to arbitrary business processes.

---

## Table Stakes

Features that users expect from any BPM engine. Missing = the module is pointless or just a wrapper around base.automation.

| Feature | Why Expected | Complexity | Gap vs ir.automation |
|---------|--------------|------------|----------------------|
| **Multi-step sequential flow** | Core BPM definition — trigger → step1 → step2 → ... | High | ir.automation has none; each rule is isolated |
| **Conditional branching (if/else)** | Every real process has paths | Medium | ir.automation filter_domain aborts entirely, no alternate path |
| **Execution instance tracking** | "Where is this record in the flow?" without this the engine has no memory | High | Completely absent in native tools |
| **All trigger types from project spec** | on_create, on_write, on_delete, on_field_change, scheduled, deadline, webhook, manual, API | Medium | Base covers most; deadline and manual/API triggers are gaps |
| **All action executors from project spec** | update_record, create_record, send_email, send_message, send_sms, create_activity, http_request, execute_python, server_action | Medium | Base covers most individually; missing link_records, http_request (outside webhook) |
| **Delay step (time-based wait mid-flow)** | Critical for: "send email, wait 3 days, check if responded, then escalate" | High | ir.automation time triggers exist but only at rule start, not mid-flow |
| **Filter/condition per step** | Evaluate domain against record state before proceeding | Low | ir.automation has filter_domain per rule but not per chained step |
| **Active/inactive toggle per flow** | Deployment safety — disable without deleting | Low | Present in ir.automation |
| **Audit log / execution history** | Debugging, compliance — "what ran, when, why" | Medium | Completely absent in native tools |
| **Error handling (stop vs continue on failure)** | Production stability — a failed HTTP call shouldn't silently kill the flow | Medium | Absent in native tools |

## Differentiators

Features that make this engine better than ir.automation. Not expected, but these are the reason to build this over using base.automation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Visual flow canvas (read-only)** | Operations can understand what a workflow does without reading configuration forms. Even a list-view "step 1 → step 2 → step 3" beats the current flat list. | High | Full drag-drop builder is an anti-feature (see below); read-only graph view is the right scope |
| **Parallel split / join** | "Notify team A AND send to system B simultaneously, then continue when both done" — common in purchase/manufacturing | High | Absent everywhere in native Odoo |
| **Human task step** | "Pause flow, assign to user, resume when they mark done" — bridges automation and human process | High | approval.request already handles approval; this is for non-approval tasks |
| **Wait-event step** | "Wait until invoice is confirmed before proceeding" — event-driven mid-flow | High | Absent in native tools; marketing_automation approximates for mail events only |
| **Execution instance state machine** | Each record running a workflow has an instance with state (running/paused/completed/error). Query: "show me all orders stuck on step 3" | High | Zero native equivalent |
| **Per-step retry policy** | "Retry HTTP call 3 times with exponential backoff before alerting admin" | Medium | Absent everywhere |
| **Webhook trigger with schema validation** | Validate incoming payload shape before running steps | Medium | ir.automation has webhook trigger but no schema validation |
| **Cross-object trigger (related record event)** | "When a child picking is done, trigger flow on parent sale order" | Medium | Not in base.automation; requires custom code today |
| **Manual trigger with context form** | User initiates flow with optional input (select assignee, enter note) before steps run | Medium | base.automation has no UI-triggered flows with input |
| **Flow versioning** | Deploy new version without breaking active instances running old version | High | Absent everywhere; critical for production stability |

## Anti-Features

Things to deliberately NOT build. These are feature bloat traps that would slow delivery and compete with native Odoo instead of complementing it.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Visual drag-drop flow builder** | Massive frontend investment (OWL canvas, drag-drop library, autolayout engine). Studio already wraps automation rules visually. Not justified for v1. | Ordered list view of steps with position field. Add graph view as a Phase 2+ differentiator only if adoption proves need. |
| **Approval steps inside BPM flows** | `approval.request` already handles this. Duplicating it creates two approval systems that drift apart. CLAUDE.md is explicit: "Never create custom approval models." | Use human_task step that can call `approval.request` as an action, not replace it. |
| **Custom form builder for human tasks** | Building a form designer is a separate product. Studio does this. | Human task references an existing Odoo view/form. The step just assigns and tracks completion. |
| **SLA / KPI monitoring dashboards** | Reporting on workflow performance is a Phase 3+ concern. Building it before instances are stable creates reports on bad data. | Log execution data in the instance model. Dashboards come after the data model is proven. |
| **Email / SMS template editor** | Odoo's `mail.template` and `sms.template` models already exist and are maintained. | Use existing template models as action configuration. Don't fork them. |
| **Role-based routing (RBAC per step)** | Odoo's standard `ir.rule` and group-based access already controls who can do what. Per-step RBAC on top creates two permission systems. | Apply Odoo's existing security model. Document which groups need access to which operations. |
| **BPMN 2.0 import/export** | XML interop with Camunda/Bizagi is a consultancy feature, not an internal tool feature. Zero real-world demand in Odoo shops. | Skip entirely. If demanded later, treat as a separate integration module. |
| **Real-time execution monitoring (websocket push)** | Prematurely complex. Requires longpolling / bus infrastructure. | Reload-on-demand list view of running instances. Sufficient for ops teams. |
| **Sub-process / reusable sub-flows** | Composition of flows is a v3+ feature after the base engine is proven. Adds graph complexity, recursion risks, and debugging difficulty. | Flat flows only in v1. Reference external ir.actions.server as an escape hatch. |

---

## Feature Dependencies

```
Trigger Engine
    └── Execution Instance (required for everything below)
            ├── Sequential Steps (requires instance state)
            │       ├── Condition/Branch Step (requires steps)
            │       ├── Delay Step (requires instance state + cron)
            │       ├── Parallel Split (requires steps + instance)
            │       │       └── Parallel Join (requires split)
            │       ├── Human Task Step (requires instance + activity)
            │       └── Wait-Event Step (requires instance + trigger engine)
            └── Audit Log (requires instance)
                    └── Error History (requires audit log)
```

Key dependencies:
- **Execution instance model must be built before any multi-step feature** — every differentiator depends on it
- **Sequential steps must work before branching** — branches require at least 2 step outputs
- **Delay step requires cron integration** — cannot be purely synchronous
- **Parallel join requires parallel split** — join has no meaning without a preceding split
- **Human task requires activity model** — leverages `mail.activity`, not a new model

---

## MVP Recommendation

The MVP must prove the core thing that ir.automation cannot do: multi-step flow with instance memory.

**Prioritize:**
1. **Execution instance model** — the state machine that tracks "record X is at step 3 of flow Y" (table stakes foundation)
2. **Sequential steps with delay** — trigger → action → delay → action — proves temporal orchestration works
3. **Condition/branch step** — if/else routing makes it a real BPM engine, not just a cron chain
4. **All 18+ action executors** — depth of available actions determines practical utility
5. **Audit log per instance** — without this, production debugging is impossible and adoption dies

**Defer:**
- Parallel split/join: Real complexity, rare in v1 use cases — defer to Phase 2
- Human task / wait-event: Valuable but requires robust instance model first — defer to Phase 2
- Visual canvas: Marketing not engineering — defer to Phase 3 if adoption justifies investment
- Flow versioning: Important but can be solved with "create new flow, migrate manually" in v1
- Cross-object triggers: Complex event subscription — defer to Phase 2

---

## Comparison: bpm_automation vs Native Tools

| Capability | ir.automation | marketing_automation | Studio | bpm_automation |
|------------|--------------|---------------------|--------|----------------|
| Multi-step flow | No | Yes (email campaigns only) | No | Yes (any model) |
| Condition branching | Abort only | Yes (mail events) | No | Yes (domain-based) |
| Parallel steps | No | No | No | Yes (Phase 2) |
| Human task / wait | No | No | Approval only | Yes |
| Instance state tracking | No | Yes (participant model) | No | Yes |
| Audit log | No | Partial (trace model) | No | Yes |
| Webhook trigger | Yes | No | No | Yes |
| Arbitrary model scope | Yes | No (contacts only) | Yes | Yes |
| Delay mid-flow | No | Yes (interval) | No | Yes |
| Python code executor | Yes (admin) | No | No | Yes (safe_eval) |
| Visual designer | No | Yes (basic) | Wrapper | Phase 3+ |
| n8n integration | Manual | No | No | Yes (http_request) |

---

## Sources

- `/home/bashar/odoo18/addons/base_automation/models/base_automation.py` — trigger types, filter_domain, time triggers, webhook (HIGH confidence, direct source)
- `/home/bashar/odoo18/addons/base_automation/models/ir_actions_server.py` — action state enumeration (HIGH confidence)
- `/home/bashar/odoo18/odoo/addons/base/models/ir_actions.py` — core server action state: object_write, object_create, code, webhook, multi (HIGH confidence)
- `/home/bashar/odoo18/addons/mail/models/ir_actions_server.py` — mail_post, next_activity, followers, remove_followers (HIGH confidence)
- `/home/bashar/odoo18/addons/sms/models/ir_actions_server.py` — sms action type (HIGH confidence)
- `/home/bashar/odoo18/odoo/ent_addons/whatsapp/models/ir_actions_server.py` — whatsapp action type (HIGH confidence)
- `/home/bashar/odoo18/odoo/ent_addons/marketing_automation/models/marketing_activity.py` — tree-flow, trigger_type, parent_id pattern (HIGH confidence)
- `/home/bashar/odoo18/odoo/ent_addons/web_studio/models/studio_approval.py` — Studio approval model (HIGH confidence)
- `/home/bashar/odoo18/CLAUDE.md` — project context, approval.request constraint, existing module inventory (HIGH confidence)
