# Roadmap: BPM Automation Engine

## Overview

This roadmap delivers a complete BPM engine for Odoo 18 in 9 phases, ordered by strict foreign-key dependencies and architectural risk. Phases 1-3 build the definition layer (what workflows look like). Phases 4-6 build the execution layer (how workflows run). Phases 7-8 build the business logic layer (what workflows do). Phase 9 adds observability. The build order front-loads the hardest architectural risks (outbox pattern, SKIP LOCKED, trigger loops) so failures surface early.

## Phases

- [ ] **Phase 1: Module Scaffold and Security** - Installable module with security groups, menus, and access rights
- [ ] **Phase 2: Workflow Definition Schema** - Models for workflows, steps, and actions with state lifecycle
- [ ] **Phase 3: Triggers and Definition Views** - Trigger model, domain filters, and workflow form UI
- [ ] **Phase 4: Outbox Queue and Instance Tracking** - Durable execution queue with instance and step log models
- [ ] **Phase 5: Trigger Engine and ORM Mixin** - ORM event interception that fires workflows into the outbox
- [ ] **Phase 6: Orchestrator Core** - Cron-driven queue processor with retry, recovery, and configuration
- [ ] **Phase 7: Step Executors** - Condition evaluation, stop handling, and action dispatch routing
- [ ] **Phase 8: Action Executors** - Record CRUD, email, activity, server action with loop prevention
- [ ] **Phase 9: Monitoring and Audit** - Instance views, step timeline, control buttons, audit log, statistics

## Phase Details

### Phase 1: Module Scaffold and Security
**Goal**: Admin can install the module and see BPM menus with proper group-based access
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03
**Success Criteria** (what must be TRUE):
  1. Module installs without error on a clean Odoo 18 database
  2. Four security groups exist: BPM User, BPM Designer, BPM Manager, BPM Administrator (with proper hierarchy)
  3. Top-level BPM menu appears with sections for Workflows, Instances, Tasks, Monitoring, Configuration
  4. Users without BPM groups cannot see BPM menus or access BPM models
**Plans**: TBD

Plans:
- [ ] 01-01: Module manifest, directory structure, security groups, menus, and access rights

### Phase 2: Workflow Definition Schema
**Goal**: Admin can create and configure multi-step workflows with actions through form views
**Depends on**: Phase 1
**Requirements**: WFDEF-01, WFDEF-02, WFDEF-03, WFDEF-04, WFDEF-05
**Success Criteria** (what must be TRUE):
  1. Admin can create a workflow with name, unique code, description, target model selection, and version number
  2. Workflow state transitions work: draft -> active -> disabled, with activate/deactivate buttons
  3. Admin can add steps (action, condition, stop types) to a workflow with next_step and on_error_step routing
  4. Admin can define reusable actions with field mappings using static values, field references, or expressions
  5. Steps and actions are visible in tree views within the workflow form
**Plans**: TBD

Plans:
- [ ] 02-01: Workflow model with state lifecycle and basic form/tree views
- [ ] 02-02: Step model with type selection, routing fields, and action model with field mappings

### Phase 3: Triggers and Definition Views
**Goal**: Admin can configure what events start a workflow and see the complete definition in a polished form
**Depends on**: Phase 2
**Requirements**: WFDEF-06, WFDEF-07, WFDEF-08
**Success Criteria** (what must be TRUE):
  1. Admin can define triggers of type on_create, on_write, manual, or scheduled (cron) on a workflow
  2. Each trigger supports a domain filter to match only specific records
  3. Workflow form view shows steps tree, triggers tree, and summary statistics in a coherent layout
**Plans**: TBD

Plans:
- [ ] 03-01: Trigger model with type selection, domain filters, and cron scheduling fields
- [ ] 03-02: Complete workflow form view with embedded steps tree, triggers tree, and statistics

### Phase 4: Outbox Queue and Instance Tracking
**Goal**: The system has a durable queue for workflow execution and models to track running instances
**Depends on**: Phase 2
**Requirements**: EXEC-01, EXEC-05, EXEC-06
**Success Criteria** (what must be TRUE):
  1. bpm.outbox model exists with state management (pending/processing/done/failed), idempotency keys, and payload storage
  2. bpm.workflow.instance model tracks state (running/paused/done/failed/cancelled), current step, and execution context
  3. bpm.instance.step.log records each step execution with input/output, timing, error info, and retry count
  4. Outbox entries can be created programmatically and transition through states correctly
**Plans**: TBD

Plans:
- [ ] 04-01: Outbox model with state machine, idempotency keys, and retry metadata
- [ ] 04-02: Workflow instance and step log models with state tracking and context storage

### Phase 5: Trigger Engine and ORM Mixin
**Goal**: Record events in Odoo automatically create outbox entries for matching workflows
**Depends on**: Phase 3, Phase 4
**Requirements**: EXEC-09, EXEC-10
**Success Criteria** (what must be TRUE):
  1. When a user creates or writes a record on a model with active triggers, matching workflow outbox entries are created within the same transaction
  2. The bpm_skip_triggers context flag prevents trigger firing (no infinite loops when BPM writes back)
  3. Trigger mixin dynamically patches target models when workflows are activated/deactivated
**Plans**: TBD

Plans:
- [ ] 05-01: Trigger mixin (AbstractModel) with ORM create/write interception and bpm_skip_triggers guard
- [ ] 05-02: Trigger engine matching logic -- evaluate triggers against ORM events and write outbox entries

### Phase 6: Orchestrator Core
**Goal**: A cron job reliably processes the outbox queue with concurrency safety, retry logic, and configurable behavior
**Depends on**: Phase 4
**Requirements**: EXEC-02, EXEC-03, EXEC-04, EXEC-07, EXEC-08, CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. Orchestrator cron acquires outbox items using FOR NO KEY UPDATE SKIP LOCKED (no duplicate processing by concurrent workers)
  2. Each outbox item is committed independently (one failure does not roll back the batch)
  3. Stale locks (items locked > configurable timeout) are recovered at the start of each cron tick
  4. Failed steps retry with exponential backoff up to a configurable max retry count
  5. Failed steps route to on_error_step if configured; otherwise the instance is marked failed
  6. System configuration model allows admins to set batch size, retry delays, max retries, and log retention
  7. Cron data XML defines the orchestrator job (1 min interval) and scheduled trigger processor
**Plans**: TBD

Plans:
- [ ] 06-01: System configuration model (bpm.config.setting) with orchestrator tuning parameters
- [ ] 06-02: Orchestrator cron with SKIP LOCKED dequeue, per-item commit, and stale lock recovery
- [ ] 06-03: Retry engine with exponential backoff and error routing to on_error_step
- [ ] 06-04: Cron data XML for orchestrator and scheduled trigger jobs

### Phase 7: Step Executors
**Goal**: The orchestrator can dispatch workflow steps and route execution based on conditions
**Depends on**: Phase 6
**Requirements**: STEP-01, STEP-02, STEP-03
**Success Criteria** (what must be TRUE):
  1. Action step executor dispatches to the action engine based on the step's configured action type
  2. Condition step evaluates a safe_eval expression and routes to the true-branch or false-branch next step
  3. Stop step marks the workflow instance as completed, failed, or cancelled with an optional message
  4. End-to-end: a workflow with action -> condition -> stop steps executes correctly through the orchestrator
**Plans**: TBD

Plans:
- [ ] 07-01: Step executor dispatch framework and action step executor
- [ ] 07-02: Condition step executor with safe_eval and true/false routing
- [ ] 07-03: Stop step executor and end-to-end step chaining verification

### Phase 8: Action Executors
**Goal**: Workflows can perform real business actions -- update records, create records, send emails, create activities, and run server actions
**Depends on**: Phase 7
**Requirements**: ACTN-01, ACTN-02, ACTN-03, ACTN-04, ACTN-05, ACTN-06
**Success Criteria** (what must be TRUE):
  1. update_record executor resolves field mappings (static, field reference, expression) and writes to the target record
  2. create_record executor resolves field mappings and creates a new record on the configured model
  3. send_email executor sends email via mail.template or custom mail.mail with rendered subject and body
  4. create_activity executor creates a mail.activity with rendered summary, resolved assignee, and deadline
  5. server_action executor runs an ir.actions.server with proper context and active record
  6. All action executors set bpm_skip_triggers=True in context on any record writes (no trigger loops)
**Plans**: TBD

Plans:
- [ ] 08-01: Field mapping resolution engine (static, field, expression value types)
- [ ] 08-02: update_record and create_record executors with field mapping resolution
- [ ] 08-03: send_email executor with mail.template and custom mail.mail support
- [ ] 08-04: create_activity executor with assignee resolution and deadline calculation
- [ ] 08-05: server_action executor with context injection and bpm_skip_triggers enforcement

### Phase 9: Monitoring and Audit
**Goal**: Admins can observe, debug, and control running workflow instances through dedicated views
**Depends on**: Phase 8
**Requirements**: MNTR-01, MNTR-02, MNTR-03, MNTR-04, MNTR-05
**Success Criteria** (what must be TRUE):
  1. Instance list view with filters by state, workflow, and date range shows all workflow executions
  2. Instance detail view shows step execution timeline with timing, status, and input/output for each step
  3. Control buttons on instance form allow admin to pause, resume, cancel, or retry a failed step
  4. Execution audit log shows per-instance categorized entries (info/warning/error) with filtering
  5. Workflow list and form views display statistics: total instances, running count, success rate
**Plans**: TBD

Plans:
- [ ] 09-01: Instance list view with state/workflow/date filters and search
- [ ] 09-02: Instance detail view with step execution timeline and context viewer
- [ ] 09-03: Instance control buttons (pause, resume, cancel, retry) with state validation
- [ ] 09-04: Execution audit log model with categorized entries and filter views
- [ ] 09-05: Workflow statistics (instance counts, success rate) on workflow list and form views

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

Note: Phase 4 and Phase 3 can execute in parallel (both depend on Phase 2, not on each other).
Phase 5 depends on both Phase 3 and Phase 4.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Module Scaffold and Security | 0/1 | Not started | - |
| 2. Workflow Definition Schema | 0/2 | Not started | - |
| 3. Triggers and Definition Views | 0/2 | Not started | - |
| 4. Outbox Queue and Instance Tracking | 0/2 | Not started | - |
| 5. Trigger Engine and ORM Mixin | 0/2 | Not started | - |
| 6. Orchestrator Core | 0/4 | Not started | - |
| 7. Step Executors | 0/3 | Not started | - |
| 8. Action Executors | 0/5 | Not started | - |
| 9. Monitoring and Audit | 0/5 | Not started | - |
