# Requirements: BPM Automation Engine

**Defined:** 2026-02-22
**Core Value:** Any business record in Odoo can automatically trigger a multi-step workflow — without writing code.

## v1 Requirements

Requirements for initial release. Table stakes that deliver a working BPM engine.

### Foundation

- [ ] **FOUND-01**: Module installs on Odoo 18 with security groups (User, Designer, Manager, Administrator)
- [ ] **FOUND-02**: Menu structure with Workflows, Instances, Tasks, Monitoring, Configuration sections
- [ ] **FOUND-03**: Access rights and record rules enforce group-based visibility

### Workflow Definition

- [ ] **WFDEF-01**: Admin can create workflow with name, unique code, description, target model, and version
- [ ] **WFDEF-02**: Workflow has state lifecycle: draft → active → disabled (with activate/deactivate actions)
- [ ] **WFDEF-03**: Admin can define steps within a workflow: action, condition (if/else gateway), stop
- [ ] **WFDEF-04**: Each step has configurable next_step and on_error_step routing
- [ ] **WFDEF-05**: Admin can define reusable actions with field mappings (static, field, expression value types)
- [ ] **WFDEF-06**: Admin can define triggers: on_create, on_write, manual, scheduled (cron)
- [ ] **WFDEF-07**: Triggers support domain filters to match specific records
- [ ] **WFDEF-08**: Workflow form view with steps tree, triggers tree, and statistics

### Execution Engine

- [ ] **EXEC-01**: Outbox queue model (bpm.outbox) with idempotency keys and state management
- [ ] **EXEC-02**: Orchestrator cron acquires outbox items using FOR NO KEY UPDATE SKIP LOCKED
- [ ] **EXEC-03**: Orchestrator commits per item (not per batch) to prevent cascading rollbacks
- [ ] **EXEC-04**: Stale lock recovery runs at start of each cron tick (recover items locked > 10 min)
- [ ] **EXEC-05**: Workflow instance model tracks state (running/paused/done/failed/cancelled), current step, context
- [ ] **EXEC-06**: Step execution log tracks each step's input/output, timing, error info, and retry count
- [ ] **EXEC-07**: Retry logic with exponential backoff and configurable max retries
- [ ] **EXEC-08**: Failed steps route to on_error_step if configured, otherwise mark instance failed
- [ ] **EXEC-09**: Trigger mixin overrides create/write on target models to fire workflows within user's transaction
- [ ] **EXEC-10**: Trigger mixin uses bpm_skip_triggers context flag to prevent infinite loops

### Action Executors

- [ ] **ACTN-01**: update_record — resolve field mappings and write to target record
- [ ] **ACTN-02**: create_record — resolve field mappings and create new record on target model
- [ ] **ACTN-03**: send_email — send via mail.template or custom mail.mail with rendered subject/body
- [ ] **ACTN-04**: create_activity — create mail.activity with rendered summary, assignee resolution, deadline
- [ ] **ACTN-05**: server_action — execute ir.actions.server with context and active record
- [ ] **ACTN-06**: All action executors set bpm_skip_triggers=True context on record writes

### Step Executors

- [ ] **STEP-01**: Action executor dispatches to action engine based on action type
- [ ] **STEP-02**: Condition executor evaluates safe_eval expression and routes to true/false next steps
- [ ] **STEP-03**: Stop executor marks workflow as completed/failed/cancelled with optional message

### Monitoring

- [ ] **MNTR-01**: Instance list view with filters by state, workflow, date range
- [ ] **MNTR-02**: Instance detail view showing step execution timeline and context viewer
- [ ] **MNTR-03**: Control buttons on instance: pause, resume, cancel, retry failed step
- [ ] **MNTR-04**: Execution audit log (per-instance, level-categorized, filterable)
- [ ] **MNTR-05**: Workflow list/form views with statistics (instances, success rate)

### Configuration

- [ ] **CONF-01**: System configuration model for orchestrator batch size, retry delays, max retries, log retention
- [ ] **CONF-02**: Cron data XML for orchestrator (1 min interval) and scheduled triggers

## v2 Requirements

Deferred differentiators. Build after v1 core is proven stable.

### Advanced Step Types

- **STEP-10**: Delay/timer step — wait fixed duration or until field-based datetime
- **STEP-11**: Human task step — create bpm.task with assignee resolution and deadline
- **STEP-12**: Wait event step — pause instance until external event correlation
- **STEP-13**: Parallel split step — fork into multiple concurrent branches
- **STEP-14**: Parallel join step — wait for all/any branches to complete before continuing

### Advanced Triggers

- **TRIG-10**: on_delete trigger (fire on record unlink)
- **TRIG-11**: on_field_change trigger (detect specific field value changes)
- **TRIG-12**: on_condition trigger (periodic evaluation of domain)
- **TRIG-13**: deadline trigger (fire relative to date field)
- **TRIG-14**: webhook trigger (external HTTP POST fires workflow)
- **TRIG-15**: API trigger (REST endpoint starts workflow)

### Advanced Action Executors

- **ACTN-10**: send_message — post to chatter via message_post()
- **ACTN-11**: send_sms — send SMS via sms.template
- **ACTN-12**: delete_record — archive or unlink records by domain
- **ACTN-13**: link_records — link via Many2many field
- **ACTN-14**: http_request — call external HTTP endpoint with auth (basic/bearer/api_key)
- **ACTN-15**: webhook_call — call external webhook with HMAC signature
- **ACTN-16**: execute_python — run sandboxed Python with admin-approved function registry

### Human Task System

- **TASK-10**: bpm.task model with state lifecycle (pending/claimed/completed/expired)
- **TASK-11**: Task kanban view grouped by state with assignee avatars
- **TASK-12**: Task escalation with configurable deadlines and level-based reassignment
- **TASK-13**: Task delegation (reassign to another user)
- **TASK-14**: mail.activity sync (mark activity done on task completion)

### Integration

- **INTG-10**: REST API: list workflows, start workflow, get instance, complete task
- **INTG-11**: Webhook endpoint controller with token auth
- **INTG-12**: HMAC signature validation and IP allowlist on webhook endpoint

### Advanced Monitoring

- **DASH-10**: Dashboard with statistics widgets (running/failed/pending counts)
- **DASH-11**: Graph views for state distribution and time-based metrics
- **DASH-12**: Instance graph view showing workflow distribution

## Out of Scope

| Feature | Reason |
|---------|--------|
| Approval workflows | Odoo native approval.request handles this; no duplication |
| Visual drag-and-drop workflow designer | Step-based form UI sufficient; visual canvas is massive scope |
| BPMN 2.0 import/export | Enterprise standard but huge complexity for no immediate value |
| Real-time websocket monitoring | Odoo's action polling is sufficient; websockets add infrastructure |
| Custom form builder for human tasks | Odoo's native form engine handles task UIs |
| Integration with EPT modules | BPM is standalone; EPT approval chains stay as-is |
| Multi-tenancy / SaaS features | Single Odoo instance target |

## Traceability

Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| *(populated by roadmapper)* | | |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 0
- Unmapped: 30

---
*Requirements defined: 2026-02-22*
*Last updated: 2026-02-22 after initial definition*
