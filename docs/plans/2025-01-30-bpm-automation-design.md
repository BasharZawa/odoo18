# BPM Automation Module - Complete Design Document

**Module Name:** `bpm_automation`
**Version:** 18.0.1.0.0
**Date:** 2025-01-30
**Target:** Odoo 18 Community/Enterprise
**Deployment:** odoo.sh via GitHub

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Model](#3-data-model)
4. [Trigger System](#4-trigger-system)
5. [Execution Engine](#5-execution-engine)
6. [Action Executors](#6-action-executors)
7. [Dashboard & UI](#7-dashboard--ui)
8. [API Endpoints](#8-api-endpoints)
9. [Security](#9-security)
10. [Configuration](#10-configuration)
11. [File Structure](#11-file-structure)
12. [Implementation Phases](#12-implementation-phases)
13. [Testing Strategy](#13-testing-strategy)
14. [Deployment Guide](#14-deployment-guide)

---

## 1. Executive Summary

### 1.1 Purpose

BPM Automation is a comprehensive workflow and process management system for Odoo 18. It enables administrators to build, edit, and manage business workflows through a step-based UI without writing code.

### 1.2 Key Features

| Feature | Description |
|---------|-------------|
| **Visual Workflow Builder** | Step-based list UI for designing workflows |
| **Multiple Trigger Types** | Record events, schedules, webhooks, manual, API |
| **Rich Action Library** | 18+ action types for records, communications, integrations |
| **Human Tasks** | Approval workflows with assignment, escalation, deadlines |
| **External Integrations** | HTTP requests, webhooks, API calls |
| **Monitoring Dashboard** | Real-time instance tracking, error recovery, metrics |
| **Parallel Execution** | Split/join workflows with branch tracking |
| **Reliable Delivery** | Outbox pattern for guaranteed execution |

### 1.3 Use Cases

1. **Approval Workflows** - Purchase orders, leave requests, expense claims
2. **Document Lifecycle** - Lead → Opportunity → Quote → Order → Invoice
3. **Integration Orchestration** - Sync with external APIs, webhooks
4. **Scheduled Operations** - Daily reports, periodic cleanup, batch processing
5. **Event-Driven Automation** - React to changes across the system

### 1.4 Design Principles

- **No Code Required** - Admins configure via UI, not Python
- **Async Execution** - Never block user operations
- **Reliable** - Outbox pattern prevents lost actions
- **Extensible** - Pluggable executor architecture
- **Observable** - Full audit trail and monitoring
- **Odoo-Native** - Leverages ir.cron, mail.activity, mail.template

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BPM AUTOMATION                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Workflow   │  │   Trigger   │  │   Action    │  │ Dashboard  │ │
│  │  Designer   │  │   Engine    │  │   Engine    │  │  & Monitor │ │
│  │  (Step UI)  │  │             │  │             │  │            │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
│         │                │                │                │       │
│  ┌──────▼────────────────▼────────────────▼────────────────▼─────┐ │
│  │                     CORE ENGINE                               │ │
│  │  - Workflow Definitions    - Instance Management              │ │
│  │  - Step Definitions        - Execution Queue (Outbox)         │ │
│  │  - Context Management      - Error Handling & Retry           │ │
│  └──────────────────────────┬────────────────────────────────────┘ │
│                             │                                      │
│  ┌──────────────────────────▼────────────────────────────────────┐ │
│  │                   ODOO INTEGRATION LAYER                      │ │
│  │  ir.cron │ mail.activity │ mail.template │ mail.message       │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Workflow Designer** | UI for creating/editing workflow definitions and steps |
| **Trigger Engine** | Detects events and starts workflow instances |
| **Action Engine** | Executes steps via pluggable executors |
| **Orchestrator** | Cron-based worker that processes the outbox queue |
| **Dashboard** | Monitoring, control, and analytics UI |

### 2.3 Execution Flow

```
Event Occurs (create/write/cron/webhook/manual)
         │
         ▼
┌─────────────────┐
│ Trigger Engine  │ ── Match triggers, check conditions
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Instance │ ── bpm.workflow.instance + context
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Enqueue to      │ ── First step added to bpm.outbox
│ Outbox          │
└────────┬────────┘
         │
         ▼ (async, via cron)
┌─────────────────┐
│ Orchestrator    │ ── Picks items from outbox
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Action Executor │ ── Executes step, determines next
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Enqueue Next    │ ── Next step(s) to outbox
│ or Complete     │
└─────────────────┘
```

---

## 3. Data Model

### 3.1 Model Overview

| # | Model | Purpose | Key Fields |
|---|-------|---------|------------|
| 1 | `bpm.workflow` | Workflow definition | name, code, model_id, state, version |
| 2 | `bpm.workflow.step` | Steps in workflow | workflow_id, sequence, step_type, action_id |
| 3 | `bpm.action` | Reusable actions | name, action_type, config fields |
| 4 | `bpm.action.field.map` | Field mappings | action_id, field_id, value_type |
| 5 | `bpm.trigger` | Workflow triggers | workflow_id, trigger_type, conditions |
| 6 | `bpm.workflow.instance` | Running instance | workflow_id, res_model, res_id, state |
| 7 | `bpm.instance.step.log` | Step execution log | instance_id, step_id, state, result |
| 8 | `bpm.parallel.branch` | Parallel tracking | instance_id, split_step_log_id, state |
| 9 | `bpm.execution.log` | Audit trail | instance_id, timestamp, message |
| 10 | `bpm.task` | Human tasks | instance_id, assignee_id, state, deadline |
| 11 | `bpm.task.response` | Task responses | task_id, user_id, decision |
| 12 | `bpm.webhook.endpoint` | Webhook config | trigger_id, token, secret_key |
| 13 | `bpm.webhook.call.log` | Webhook history | endpoint_id, payload, status |
| 14 | `bpm.schedule.job` | Cron wrapper | trigger_id, ir_cron_id, next_run |
| 15 | `bpm.outbox` | Execution queue | instance_id, step_log_id, state |
| 16 | `bpm.config.setting` | Settings | key, value, company_id |
| 17 | `bpm.action.registry` | Function whitelist | name, python_path, is_safe |

### 3.2 Detailed Model Definitions

#### 3.2.1 bpm.workflow

```python
class BpmWorkflow(models.Model):
    _name = 'bpm.workflow'
    _description = 'BPM Workflow Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ─── BASIC INFO ───
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        help='Human-readable workflow name'
    )
    code = fields.Char(
        string='Code',
        required=True,
        copy=False,
        help='Unique identifier for API/reference'
    )
    description = fields.Html(
        string='Description',
        help='Detailed description of workflow purpose'
    )

    # ─── TARGET MODEL ───
    model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        ondelete='cascade',
        help='Primary model this workflow operates on'
    )
    model_name = fields.Char(
        related='model_id.model',
        store=True,
        string='Model Name'
    )

    # ─── STATE & VERSION ───
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ], string='Status', default='draft', tracking=True)

    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True,
        help='Auto-incremented on activation'
    )
    is_latest = fields.Boolean(
        string='Is Latest Version',
        default=True,
        help='Only one version per code can be latest'
    )
    previous_version_id = fields.Many2one(
        'bpm.workflow',
        string='Previous Version',
        readonly=True
    )

    # ─── RELATIONS ───
    step_ids = fields.One2many(
        'bpm.workflow.step',
        'workflow_id',
        string='Steps',
        copy=True
    )
    trigger_ids = fields.One2many(
        'bpm.trigger',
        'workflow_id',
        string='Triggers',
        copy=True
    )
    instance_ids = fields.One2many(
        'bpm.workflow.instance',
        'workflow_id',
        string='Instances'
    )

    # ─── STATISTICS ───
    step_count = fields.Integer(
        compute='_compute_counts',
        string='Steps'
    )
    trigger_count = fields.Integer(
        compute='_compute_counts',
        string='Triggers'
    )
    instance_count = fields.Integer(
        compute='_compute_counts',
        string='Instances'
    )
    running_instance_count = fields.Integer(
        compute='_compute_counts',
        string='Running'
    )

    # ─── COMPANY ───
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # ─── AUDIT ───
    create_uid = fields.Many2one('res.users', readonly=True)
    activated_at = fields.Datetime(string='Activated At')
    activated_by = fields.Many2one('res.users', string='Activated By')

    # ─── CONSTRAINTS ───
    _sql_constraints = [
        ('code_version_unique',
         'UNIQUE(code, version)',
         'Code + Version must be unique'),
    ]
```

#### 3.2.2 bpm.workflow.step

```python
class BpmWorkflowStep(models.Model):
    _name = 'bpm.workflow.step'
    _description = 'BPM Workflow Step'
    _order = 'sequence, id'

    # ─── BASIC INFO ───
    name = fields.Char(
        string='Step Name',
        required=True,
        help='Descriptive name for this step'
    )
    workflow_id = fields.Many2one(
        'bpm.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of execution in list view'
    )

    # ─── STEP TYPE ───
    step_type = fields.Selection([
        ('action', 'Execute Action'),
        ('condition', 'Condition Gateway'),
        ('parallel_split', 'Parallel Split'),
        ('parallel_join', 'Parallel Join'),
        ('human_task', 'Human Task'),
        ('wait_event', 'Wait for Event'),
        ('delay', 'Delay/Timer'),
        ('stop', 'Stop Workflow'),
    ], string='Step Type', required=True, default='action')

    # ─── ACTION REFERENCE ───
    action_id = fields.Many2one(
        'bpm.action',
        string='Action',
        help='Action to execute (for action type steps)'
    )

    # ─── FLOW CONTROL ───
    next_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Next Step',
        domain="[('workflow_id', '=', workflow_id)]",
        help='Step to execute after this one'
    )
    is_start_step = fields.Boolean(
        string='Is Start Step',
        default=False,
        help='First step to execute when workflow starts'
    )

    # ─── CONDITION GATEWAY ───
    condition_expression = fields.Text(
        string='Condition',
        help='Python expression. Available: record, ctx, env, user'
    )
    on_true_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='If True → Step',
        domain="[('workflow_id', '=', workflow_id)]"
    )
    on_false_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='If False → Step',
        domain="[('workflow_id', '=', workflow_id)]"
    )

    # ─── PARALLEL SPLIT ───
    parallel_step_ids = fields.Many2many(
        'bpm.workflow.step',
        'bpm_step_parallel_rel',
        'step_id',
        'parallel_step_id',
        string='Parallel Branches',
        domain="[('workflow_id', '=', workflow_id)]"
    )
    join_type = fields.Selection([
        ('all', 'Wait for All'),
        ('any', 'Continue on Any'),
    ], string='Join Type', default='all')
    join_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Join at Step',
        domain="[('workflow_id', '=', workflow_id), ('step_type', '=', 'parallel_join')]"
    )

    # ─── HUMAN TASK (inline, no action_id needed) ───
    task_title = fields.Char(string='Task Title')
    task_instructions = fields.Html(string='Instructions')
    assignee_type = fields.Selection([
        ('user', 'Specific User'),
        ('field', 'Field on Record'),
        ('group', 'User Group'),
        ('expression', 'Python Expression'),
    ], string='Assign To')
    assignee_user_id = fields.Many2one('res.users', string='Assignee User')
    assignee_field_id = fields.Many2one(
        'ir.model.fields',
        string='Assignee Field',
        help='Many2one field pointing to res.users'
    )
    assignee_group_id = fields.Many2one('res.groups', string='Assignee Group')
    assignee_expression = fields.Text(string='Assignee Expression')

    task_deadline_hours = fields.Integer(
        string='Deadline (hours)',
        default=24
    )
    on_approve_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='On Approve → Step',
        domain="[('workflow_id', '=', workflow_id)]"
    )
    on_reject_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='On Reject → Step',
        domain="[('workflow_id', '=', workflow_id)]"
    )

    # ─── ESCALATION ───
    escalation_enabled = fields.Boolean(string='Enable Escalation')
    escalation_hours = fields.Integer(string='Escalate After (hours)')
    escalation_user_id = fields.Many2one('res.users', string='Escalate To User')
    escalation_group_id = fields.Many2one('res.groups', string='Escalate To Group')

    # ─── WAIT EVENT ───
    event_name = fields.Char(
        string='Event Name',
        help='Event identifier to wait for'
    )
    event_correlation_field = fields.Char(
        string='Correlation Field',
        help='Context key to match incoming event'
    )
    event_timeout_hours = fields.Integer(string='Timeout (hours)')
    on_timeout_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='On Timeout → Step',
        domain="[('workflow_id', '=', workflow_id)]"
    )

    # ─── DELAY/TIMER ───
    delay_type = fields.Selection([
        ('fixed', 'Fixed Duration'),
        ('field', 'Based on Field'),
        ('expression', 'Python Expression'),
    ], string='Delay Type')
    delay_minutes = fields.Integer(string='Minutes')
    delay_hours = fields.Integer(string='Hours')
    delay_days = fields.Integer(string='Days')
    delay_field_id = fields.Many2one(
        'ir.model.fields',
        string='Date Field',
        help='Datetime field to calculate delay from'
    )
    delay_expression = fields.Text(
        string='Delay Expression',
        help='Python expression returning minutes'
    )

    # ─── STOP ───
    stop_type = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('cancel', 'Cancel'),
    ], string='Stop Type', default='success')
    stop_message = fields.Text(string='Stop Message')

    # ─── ERROR HANDLING ───
    retry_count = fields.Integer(
        string='Max Retries',
        default=3,
        help='Number of retry attempts on failure'
    )
    retry_delay_minutes = fields.Integer(
        string='Retry Delay (min)',
        default=5
    )
    on_error_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='On Error → Step',
        domain="[('workflow_id', '=', workflow_id)]",
        help='Step to execute on unrecoverable error'
    )

    # ─── DESCRIPTION ───
    description = fields.Text(
        string='Description',
        help='Internal notes about this step'
    )
    active = fields.Boolean(default=True)
```

#### 3.2.3 bpm.action

```python
class BpmAction(models.Model):
    _name = 'bpm.action'
    _description = 'BPM Reusable Action'
    _order = 'name'

    # ─── BASIC INFO ───
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
        help='Template actions can be reused across workflows'
    )

    # ─── ACTION TYPE ───
    action_type = fields.Selection([
        # Record Actions
        ('update_record', 'Update Record'),
        ('create_record', 'Create Record'),
        ('delete_record', 'Delete Record'),
        ('link_records', 'Link Records'),
        ('server_action', 'Execute Server Action'),
        # Communication
        ('send_email', 'Send Email'),
        ('send_message', 'Post Message'),
        ('send_sms', 'Send SMS'),
        ('create_activity', 'Create Activity'),
        # Integration
        ('http_request', 'HTTP Request'),
        ('webhook_call', 'Webhook Call'),
        ('execute_python', 'Execute Python'),
    ], string='Action Type', required=True)

    # ─── TARGET MODEL (for record actions) ───
    model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        help='Model to operate on (defaults to workflow model)'
    )
    use_workflow_model = fields.Boolean(
        string='Use Workflow Model',
        default=True,
        help='Operate on the workflow\'s target model'
    )

    # ─── FIELD MAPPINGS (for update/create) ───
    field_mapping_ids = fields.One2many(
        'bpm.action.field.map',
        'action_id',
        string='Field Mappings'
    )

    # ─── DELETE OPTIONS ───
    delete_type = fields.Selection([
        ('archive', 'Archive (set active=False)'),
        ('unlink', 'Delete Permanently'),
    ], string='Delete Type', default='archive')
    delete_domain = fields.Text(
        string='Delete Domain',
        help='Domain to filter records to delete'
    )

    # ─── SERVER ACTION ───
    server_action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action'
    )

    # ─── EMAIL ───
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template'
    )
    email_to = fields.Text(
        string='To (Expression)',
        help='Python expression for recipient email'
    )
    email_cc = fields.Text(string='CC (Expression)')
    email_subject = fields.Char(string='Subject (Jinja)')
    email_body = fields.Html(string='Body (Jinja)')

    # ─── MESSAGE ───
    message_body = fields.Html(string='Message Body (Jinja)')
    message_subtype_id = fields.Many2one(
        'mail.message.subtype',
        string='Subtype'
    )
    message_partner_ids_expr = fields.Text(
        string='Notify Partners (Expression)',
        help='Expression returning partner IDs list'
    )

    # ─── SMS ───
    sms_template_id = fields.Many2one('sms.template', string='SMS Template')
    sms_to_field_id = fields.Many2one(
        'ir.model.fields',
        string='Phone Field'
    )
    sms_to_expression = fields.Text(string='Phone Expression')
    sms_body = fields.Text(string='SMS Body (Jinja)')

    # ─── ACTIVITY ───
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type'
    )
    activity_summary = fields.Char(string='Summary (Jinja)')
    activity_note = fields.Html(string='Note (Jinja)')
    activity_user_expr = fields.Text(string='Assigned To (Expression)')
    activity_deadline_days = fields.Integer(
        string='Deadline (days)',
        default=2
    )

    # ─── HTTP REQUEST ───
    http_url = fields.Text(
        string='URL (Jinja)',
        help='URL with Jinja templating: https://api.example.com/{{record.id}}'
    )
    http_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ], string='HTTP Method', default='POST')
    http_headers = fields.Text(
        string='Headers (JSON Jinja)',
        help='{"Authorization": "Bearer {{ctx.token}}"}'
    )
    http_body = fields.Text(
        string='Body (JSON Jinja)',
        help='Request body with Jinja templating'
    )
    http_auth_type = fields.Selection([
        ('none', 'None'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('api_key', 'API Key'),
    ], string='Auth Type', default='none')
    http_auth_user = fields.Char(string='Username / API Key Name')
    http_auth_password = fields.Char(string='Password / Token / API Key')
    http_timeout = fields.Integer(string='Timeout (sec)', default=30)
    http_success_codes = fields.Char(
        string='Success Codes',
        default='200,201,202,204',
        help='Comma-separated HTTP codes considered success'
    )

    # ─── WEBHOOK CALL ───
    webhook_url = fields.Text(string='Webhook URL')
    webhook_secret = fields.Char(string='Webhook Secret (for HMAC)')
    webhook_payload_template = fields.Text(
        string='Payload (JSON Jinja)',
        help='Custom payload, or leave empty for default'
    )

    # ─── PYTHON CODE ───
    python_code = fields.Text(
        string='Python Code',
        help='Sandboxed Python. Available: record, ctx, env, user, datetime, json'
    )
    registry_id = fields.Many2one(
        'bpm.action.registry',
        string='Registered Function',
        help='Call a whitelisted Python function'
    )

    # ─── COMPANY ───
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)
```

#### 3.2.4 bpm.action.field.map

```python
class BpmActionFieldMap(models.Model):
    _name = 'bpm.action.field.map'
    _description = 'BPM Action Field Mapping'
    _order = 'sequence'

    action_id = fields.Many2one(
        'bpm.action',
        string='Action',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        help='Field to set value for'
    )
    field_name = fields.Char(related='field_id.name', store=True)
    field_type = fields.Selection(related='field_id.ttype')

    value_type = fields.Selection([
        ('static', 'Static Value'),
        ('field', 'Copy from Field'),
        ('expression', 'Python Expression'),
        ('context', 'From Context'),
        ('jinja', 'Jinja Template'),
    ], string='Value Type', required=True, default='static')

    # Value sources (based on value_type)
    static_value = fields.Text(string='Static Value')
    source_field_id = fields.Many2one(
        'ir.model.fields',
        string='Source Field'
    )
    expression = fields.Text(
        string='Expression',
        help='Python expression: record.partner_id.id'
    )
    context_key = fields.Char(
        string='Context Key',
        help='Key in context dict: ctx["my_key"]'
    )
    jinja_template = fields.Text(
        string='Jinja Template',
        help='Template: "Order: {{record.name}}"'
    )
```

#### 3.2.5 bpm.trigger

```python
class BpmTrigger(models.Model):
    _name = 'bpm.trigger'
    _description = 'BPM Workflow Trigger'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    workflow_id = fields.Many2one(
        'bpm.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(string='Active', default=True)

    # ─── TRIGGER TYPE ───
    trigger_type = fields.Selection([
        # Record-based
        ('on_create', 'On Create'),
        ('on_write', 'On Update'),
        ('on_delete', 'On Delete'),
        ('on_field_change', 'On Field Change'),
        ('on_condition', 'When Condition Met'),
        # Time-based
        ('scheduled', 'Scheduled (Cron)'),
        ('deadline', 'Deadline-Based'),
        # External
        ('webhook', 'Incoming Webhook'),
        ('manual', 'Manual Button'),
        ('api', 'API Call'),
    ], string='Trigger Type', required=True)

    # ─── RECORD TRIGGERS ───
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        help='Defaults to workflow model if not set'
    )
    domain_filter = fields.Text(
        string='Filter Domain',
        default='[]',
        help='Only trigger for records matching this domain'
    )

    # ─── FIELD CHANGE ───
    watched_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Watch Fields',
        help='Trigger when any of these fields change'
    )
    field_from_value = fields.Char(
        string='From Value',
        help='Optional: only if field changes FROM this value'
    )
    field_to_value = fields.Char(
        string='To Value',
        help='Optional: only if field changes TO this value'
    )

    # ─── CONDITION ───
    condition_expression = fields.Text(
        string='Condition Expression',
        help='Python expression that must be True'
    )
    condition_check_interval = fields.Integer(
        string='Check Interval (min)',
        default=60,
        help='How often to check condition for existing records'
    )

    # ─── SCHEDULED ───
    cron_expression = fields.Char(
        string='Cron Expression',
        help='Standard cron: "0 9 * * MON" = Monday 9am'
    )
    cron_timezone = fields.Char(
        string='Timezone',
        default='UTC'
    )
    schedule_job_id = fields.Many2one(
        'bpm.schedule.job',
        string='Schedule Job',
        readonly=True
    )

    # ─── DEADLINE ───
    deadline_field_id = fields.Many2one(
        'ir.model.fields',
        string='Deadline Field',
        help='Date/Datetime field to base deadline on'
    )
    deadline_offset_days = fields.Integer(
        string='Days Before (-) / After (+)',
        help='Negative = before deadline, Positive = after'
    )
    deadline_offset_hours = fields.Integer(string='Hours Offset')

    # ─── WEBHOOK ───
    webhook_endpoint_id = fields.Many2one(
        'bpm.webhook.endpoint',
        string='Webhook Endpoint',
        readonly=True
    )
    webhook_token = fields.Char(
        string='Webhook Token',
        readonly=True,
        copy=False
    )

    # ─── MANUAL ───
    button_label = fields.Char(
        string='Button Label',
        default='Start Workflow'
    )
    button_icon = fields.Char(
        string='Button Icon',
        default='fa-play'
    )
    allowed_group_ids = fields.Many2many(
        'res.groups',
        string='Allowed Groups',
        help='Groups that can trigger manually'
    )

    # ─── API ───
    api_key_required = fields.Boolean(string='Require API Key')

    # ─── DEDUPLICATION ───
    prevent_duplicate = fields.Boolean(
        string='Prevent Duplicate',
        help='Don\'t start if instance already running for this record'
    )
    duplicate_check_field = fields.Char(
        string='Duplicate Key Field',
        help='Context field to use for deduplication'
    )
```

#### 3.2.6 bpm.workflow.instance

```python
class BpmWorkflowInstance(models.Model):
    _name = 'bpm.workflow.instance'
    _description = 'BPM Workflow Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
    )

    # ─── WORKFLOW REFERENCE ───
    workflow_id = fields.Many2one(
        'bpm.workflow',
        string='Workflow',
        required=True,
        ondelete='restrict'
    )
    workflow_code = fields.Char(related='workflow_id.code', store=True)
    workflow_version = fields.Integer(
        string='Workflow Version',
        help='Version at time of creation'
    )
    trigger_id = fields.Many2one(
        'bpm.trigger',
        string='Triggered By'
    )

    # ─── SOURCE RECORD ───
    res_model = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source Record ID')
    res_name = fields.Char(
        string='Source Record',
        compute='_compute_res_name'
    )

    # ─── STATE ───
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('waiting', 'Waiting'),
        ('paused', 'Paused'),
        ('done', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    # ─── CONTEXT ───
    context_json = fields.Text(
        string='Context',
        default='{}',
        help='Runtime context data (JSON)'
    )

    # ─── CURRENT POSITION ───
    current_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Current Step'
    )
    current_step_log_id = fields.Many2one(
        'bpm.instance.step.log',
        string='Current Step Log'
    )

    # ─── TIMING ───
    started_at = fields.Datetime(string='Started At')
    ended_at = fields.Datetime(string='Ended At')
    duration_seconds = fields.Integer(
        string='Duration (sec)',
        compute='_compute_duration',
        store=True
    )

    # ─── ERROR INFO ───
    error_message = fields.Text(string='Error Message')
    last_error_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Failed at Step'
    )
    retry_count = fields.Integer(string='Retry Count', default=0)

    # ─── CONTROL ───
    paused_at = fields.Datetime(string='Paused At')
    paused_by_id = fields.Many2one('res.users', string='Paused By')
    pause_reason = fields.Text(string='Pause Reason')

    cancelled_at = fields.Datetime(string='Cancelled At')
    cancelled_by_id = fields.Many2one('res.users', string='Cancelled By')
    cancel_reason = fields.Text(string='Cancel Reason')

    # ─── RELATIONS ───
    step_log_ids = fields.One2many(
        'bpm.instance.step.log',
        'instance_id',
        string='Step Logs'
    )
    execution_log_ids = fields.One2many(
        'bpm.execution.log',
        'instance_id',
        string='Execution Logs'
    )
    task_ids = fields.One2many(
        'bpm.task',
        'instance_id',
        string='Tasks'
    )
    branch_ids = fields.One2many(
        'bpm.parallel.branch',
        'instance_id',
        string='Parallel Branches'
    )

    # ─── STATISTICS ───
    step_count = fields.Integer(compute='_compute_step_stats')
    completed_step_count = fields.Integer(compute='_compute_step_stats')
    progress_percent = fields.Float(compute='_compute_step_stats')

    # ─── COMPANY ───
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )
```

#### 3.2.7 bpm.instance.step.log

```python
class BpmInstanceStepLog(models.Model):
    _name = 'bpm.instance.step.log'
    _description = 'BPM Instance Step Execution Log'
    _order = 'sequence, started_at'

    instance_id = fields.Many2one(
        'bpm.workflow.instance',
        string='Instance',
        required=True,
        ondelete='cascade',
        index=True
    )
    step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Step',
        required=True
    )
    action_id = fields.Many2one(
        'bpm.action',
        string='Action'
    )
    sequence = fields.Integer(
        string='Execution Order',
        help='Order this step was executed'
    )

    # ─── STATE ───
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('waiting', 'Waiting'),
        ('done', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', index=True)

    # ─── TIMING ───
    started_at = fields.Datetime(string='Started At')
    ended_at = fields.Datetime(string='Ended At')
    duration_ms = fields.Integer(string='Duration (ms)')

    # ─── INPUT/OUTPUT ───
    input_context = fields.Text(
        string='Input Context',
        help='Context at step start (JSON)'
    )
    output_result = fields.Text(
        string='Output Result',
        help='Step execution result (JSON)'
    )
    context_updates = fields.Text(
        string='Context Updates',
        help='Changes made to context (JSON)'
    )

    # ─── ERROR ───
    error_message = fields.Text(string='Error Message')
    error_traceback = fields.Text(string='Error Traceback')

    # ─── RETRY ───
    attempt_number = fields.Integer(string='Attempt #', default=1)
    max_attempts = fields.Integer(string='Max Attempts')
    next_retry_at = fields.Datetime(string='Next Retry At')

    # ─── HUMAN TASK ───
    assignee_id = fields.Many2one('res.users', string='Assignee')
    assigned_at = fields.Datetime(string='Assigned At')
    completed_by_id = fields.Many2one('res.users', string='Completed By')
    decision = fields.Selection([
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('custom', 'Custom'),
    ], string='Decision')
    decision_comment = fields.Text(string='Decision Comment')
    task_id = fields.Many2one('bpm.task', string='Task')

    # ─── HTTP RESPONSE ───
    http_status_code = fields.Integer(string='HTTP Status')
    http_response_body = fields.Text(string='HTTP Response')

    # ─── PARALLEL BRANCH ───
    branch_id = fields.Many2one(
        'bpm.parallel.branch',
        string='Parallel Branch'
    )
```

#### 3.2.8 bpm.parallel.branch

```python
class BpmParallelBranch(models.Model):
    _name = 'bpm.parallel.branch'
    _description = 'BPM Parallel Branch Tracker'

    instance_id = fields.Many2one(
        'bpm.workflow.instance',
        string='Instance',
        required=True,
        ondelete='cascade'
    )
    split_step_log_id = fields.Many2one(
        'bpm.instance.step.log',
        string='Split Step',
        help='The parallel_split step that created this branch'
    )
    join_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Join Step',
        help='The parallel_join step waiting for this branch'
    )

    branch_index = fields.Integer(
        string='Branch Index',
        help='0-based index of this branch'
    )
    first_step_id = fields.Many2one(
        'bpm.workflow.step',
        string='First Step'
    )

    state = fields.Selection([
        ('running', 'Running'),
        ('done', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='running')

    started_at = fields.Datetime(string='Started At')
    ended_at = fields.Datetime(string='Ended At')
    error_message = fields.Text(string='Error Message')
```

#### 3.2.9 bpm.execution.log

```python
class BpmExecutionLog(models.Model):
    _name = 'bpm.execution.log'
    _description = 'BPM Execution Audit Log'
    _order = 'timestamp desc'

    instance_id = fields.Many2one(
        'bpm.workflow.instance',
        string='Instance',
        required=True,
        ondelete='cascade',
        index=True
    )
    step_log_id = fields.Many2one(
        'bpm.instance.step.log',
        string='Step Log'
    )

    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        index=True
    )

    log_level = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string='Level', default='info')

    category = fields.Selection([
        ('trigger', 'Trigger'),
        ('step', 'Step Execution'),
        ('action', 'Action'),
        ('condition', 'Condition'),
        ('assignment', 'Assignment'),
        ('error', 'Error'),
        ('retry', 'Retry'),
        ('control', 'Control'),
    ], string='Category')

    message = fields.Text(string='Message', required=True)
    data_json = fields.Text(string='Additional Data')

    user_id = fields.Many2one('res.users', string='User')
```

#### 3.2.10 bpm.task

```python
class BpmTask(models.Model):
    _name = 'bpm.task'
    _description = 'BPM Human Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline, create_date'

    name = fields.Char(string='Title', required=True)

    # ─── WORKFLOW REFERENCE ───
    instance_id = fields.Many2one(
        'bpm.workflow.instance',
        string='Instance',
        required=True,
        ondelete='cascade'
    )
    step_log_id = fields.Many2one(
        'bpm.instance.step.log',
        string='Step Log',
        required=True
    )
    step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Step'
    )

    # ─── SOURCE RECORD ───
    res_model = fields.Char(related='instance_id.res_model')
    res_id = fields.Integer(related='instance_id.res_id')

    # ─── CONTENT ───
    instructions = fields.Html(string='Instructions')
    form_view_id = fields.Many2one(
        'ir.ui.view',
        string='Custom Form View'
    )

    # ─── ASSIGNMENT ───
    assignee_id = fields.Many2one(
        'res.users',
        string='Assignee',
        tracking=True
    )
    assignee_group_id = fields.Many2one(
        'res.groups',
        string='Assignee Group'
    )
    delegated_from_id = fields.Many2one(
        'res.users',
        string='Delegated From'
    )

    # ─── STATE ───
    state = fields.Selection([
        ('pending', 'Pending'),
        ('claimed', 'Claimed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', default='pending', tracking=True)

    # ─── TIMING ───
    deadline = fields.Datetime(string='Deadline')
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now
    )
    claimed_at = fields.Datetime(string='Claimed At')
    completed_at = fields.Datetime(string='Completed At')

    # ─── COMPLETION ───
    completed_by_id = fields.Many2one(
        'res.users',
        string='Completed By'
    )
    decision = fields.Selection([
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('custom', 'Custom'),
    ], string='Decision')
    decision_comment = fields.Text(string='Comment')

    # ─── ESCALATION ───
    escalation_level = fields.Integer(string='Escalation Level', default=0)
    escalated_at = fields.Datetime(string='Escalated At')
    original_assignee_id = fields.Many2one(
        'res.users',
        string='Original Assignee'
    )

    # ─── MAIL ACTIVITY ───
    mail_activity_id = fields.Many2one(
        'mail.activity',
        string='Mail Activity'
    )

    # ─── COMPANY ───
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )
```

#### 3.2.11 bpm.task.response

```python
class BpmTaskResponse(models.Model):
    _name = 'bpm.task.response'
    _description = 'BPM Task Response'
    _order = 'responded_at desc'

    task_id = fields.Many2one(
        'bpm.task',
        string='Task',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user
    )

    response_type = fields.Selection([
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('delegate', 'Delegated'),
        ('comment', 'Comment'),
        ('custom', 'Custom'),
    ], string='Response Type', required=True)

    response_data = fields.Text(
        string='Response Data',
        help='JSON data for custom responses'
    )
    comment = fields.Text(string='Comment')
    responded_at = fields.Datetime(
        string='Responded At',
        default=fields.Datetime.now
    )

    # For delegation
    delegated_to_id = fields.Many2one(
        'res.users',
        string='Delegated To'
    )
```

#### 3.2.12 bpm.webhook.endpoint

```python
class BpmWebhookEndpoint(models.Model):
    _name = 'bpm.webhook.endpoint'
    _description = 'BPM Webhook Endpoint'

    name = fields.Char(string='Name', required=True)
    trigger_id = fields.Many2one(
        'bpm.trigger',
        string='Trigger',
        required=True,
        ondelete='cascade'
    )

    # ─── ENDPOINT CONFIG ───
    token = fields.Char(
        string='Token',
        required=True,
        copy=False,
        default=lambda self: self._generate_token()
    )
    endpoint_url = fields.Char(
        string='Endpoint URL',
        compute='_compute_endpoint_url'
    )

    # ─── SECURITY ───
    secret_key = fields.Char(
        string='Secret Key',
        help='For HMAC signature verification'
    )
    allowed_ips = fields.Text(
        string='Allowed IPs',
        help='Comma-separated IP addresses (empty = all)'
    )
    require_signature = fields.Boolean(
        string='Require Signature',
        default=False
    )

    # ─── STATUS ───
    is_active = fields.Boolean(string='Active', default=True)
    last_called_at = fields.Datetime(string='Last Called')
    call_count = fields.Integer(string='Total Calls', default=0)

    # ─── RATE LIMITING ───
    rate_limit_enabled = fields.Boolean(string='Enable Rate Limit')
    rate_limit_count = fields.Integer(
        string='Max Calls',
        default=100
    )
    rate_limit_period = fields.Integer(
        string='Per Minutes',
        default=60
    )
```

#### 3.2.13 bpm.webhook.call.log

```python
class BpmWebhookCallLog(models.Model):
    _name = 'bpm.webhook.call.log'
    _description = 'BPM Webhook Call Log'
    _order = 'received_at desc'

    endpoint_id = fields.Many2one(
        'bpm.webhook.endpoint',
        string='Endpoint',
        required=True,
        ondelete='cascade'
    )
    instance_id = fields.Many2one(
        'bpm.workflow.instance',
        string='Instance Created'
    )

    received_at = fields.Datetime(
        string='Received At',
        default=fields.Datetime.now
    )
    source_ip = fields.Char(string='Source IP')

    # ─── REQUEST DATA ───
    headers_json = fields.Text(string='Headers')
    payload_json = fields.Text(string='Payload')

    # ─── RESPONSE ───
    response_code = fields.Integer(string='Response Code')
    response_body = fields.Text(string='Response Body')

    # ─── PROCESSING ───
    processing_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('rejected', 'Rejected'),
    ], string='Status')
    error_message = fields.Text(string='Error Message')
    processing_time_ms = fields.Integer(string='Processing Time (ms)')
```

#### 3.2.14 bpm.schedule.job

```python
class BpmScheduleJob(models.Model):
    _name = 'bpm.schedule.job'
    _description = 'BPM Schedule Job'

    name = fields.Char(string='Name', required=True)
    trigger_id = fields.Many2one(
        'bpm.trigger',
        string='Trigger',
        required=True,
        ondelete='cascade'
    )

    # ─── CRON REFERENCE ───
    ir_cron_id = fields.Many2one(
        'ir.cron',
        string='Odoo Cron Job',
        ondelete='set null'
    )

    # ─── SCHEDULE ───
    cron_expression = fields.Char(
        string='Cron Expression',
        help='Standard cron format: MIN HOUR DOM MON DOW'
    )
    timezone = fields.Char(string='Timezone', default='UTC')

    # ─── STATUS ───
    is_active = fields.Boolean(string='Active', default=True)
    next_run = fields.Datetime(string='Next Run')
    last_run = fields.Datetime(string='Last Run')
    last_run_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='Last Run Status')
    last_error = fields.Text(string='Last Error')

    # ─── STATISTICS ───
    run_count = fields.Integer(string='Total Runs', default=0)
    success_count = fields.Integer(string='Successful Runs', default=0)
    error_count = fields.Integer(string='Failed Runs', default=0)
```

#### 3.2.15 bpm.outbox

```python
class BpmOutbox(models.Model):
    _name = 'bpm.outbox'
    _description = 'BPM Execution Outbox'
    _order = 'scheduled_at, create_date'

    # ─── REFERENCES ───
    instance_id = fields.Many2one(
        'bpm.workflow.instance',
        string='Instance',
        required=True,
        ondelete='cascade',
        index=True
    )
    step_log_id = fields.Many2one(
        'bpm.instance.step.log',
        string='Step Log',
        required=True
    )
    step_id = fields.Many2one(
        'bpm.workflow.step',
        string='Step',
        required=True
    )

    # ─── IDEMPOTENCY ───
    idempotency_key = fields.Char(
        string='Idempotency Key',
        required=True,
        index=True,
        help='Unique key to prevent duplicate execution'
    )

    # ─── STATE ───
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', index=True)

    # ─── SCHEDULING ───
    scheduled_at = fields.Datetime(
        string='Scheduled At',
        default=fields.Datetime.now,
        index=True,
        help='When this item should be processed'
    )

    # ─── PROCESSING ───
    started_at = fields.Datetime(string='Started At')
    completed_at = fields.Datetime(string='Completed At')
    processing_time_ms = fields.Integer(string='Processing Time (ms)')

    # ─── RETRY ───
    attempt_count = fields.Integer(string='Attempts', default=0)
    max_attempts = fields.Integer(string='Max Attempts', default=3)
    next_retry_at = fields.Datetime(string='Next Retry At')

    # ─── ERROR ───
    last_error = fields.Text(string='Last Error')
    error_count = fields.Integer(string='Error Count', default=0)

    # ─── LOCKING ───
    locked_at = fields.Datetime(string='Locked At')
    locked_by = fields.Char(string='Locked By', help='Worker ID')

    _sql_constraints = [
        ('idempotency_unique',
         'UNIQUE(idempotency_key)',
         'Idempotency key must be unique'),
    ]
```

#### 3.2.16 bpm.config.setting

```python
class BpmConfigSetting(models.Model):
    _name = 'bpm.config.setting'
    _description = 'BPM Configuration Setting'

    key = fields.Char(string='Key', required=True)
    value = fields.Text(string='Value')
    value_type = fields.Selection([
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ], string='Type', default='string')

    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company')

    _sql_constraints = [
        ('key_company_unique',
         'UNIQUE(key, company_id)',
         'Setting key must be unique per company'),
    ]
```

**Default settings:**

| Key | Default | Description |
|-----|---------|-------------|
| `orchestrator_batch_size` | 50 | Items per cron tick |
| `orchestrator_interval` | 1 | Cron interval (minutes) |
| `outbox_retry_delay` | 5 | Minutes between retries |
| `outbox_max_retries` | 3 | Maximum retry attempts |
| `task_default_deadline` | 24 | Hours for task deadline |
| `task_escalation_check` | 15 | Minutes between escalation checks |
| `log_retention_days` | 90 | Days to keep execution logs |
| `webhook_timeout` | 30 | Seconds for webhook timeout |
| `http_default_timeout` | 30 | Seconds for HTTP requests |

#### 3.2.17 bpm.action.registry

```python
class BpmActionRegistry(models.Model):
    _name = 'bpm.action.registry'
    _description = 'BPM Action Registry (Whitelist)'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique identifier for this function'
    )
    python_path = fields.Char(
        string='Python Path',
        required=True,
        help='Full path: module.submodule.function_name'
    )

    description = fields.Text(string='Description')

    # ─── SECURITY ───
    is_safe = fields.Boolean(
        string='Is Safe',
        default=False,
        help='Can be used without admin review'
    )
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=True
    )
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By'
    )
    approved_at = fields.Datetime(string='Approved At')

    # ─── PARAMETERS ───
    param_schema = fields.Text(
        string='Parameter Schema',
        help='JSON Schema for expected parameters'
    )
    return_schema = fields.Text(
        string='Return Schema',
        help='JSON Schema for return value'
    )

    # ─── USAGE ───
    usage_count = fields.Integer(string='Usage Count', default=0)
    last_used_at = fields.Datetime(string='Last Used')

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Code must be unique'),
        ('path_unique', 'UNIQUE(python_path)', 'Python path must be unique'),
    ]
```

---

## 4. Trigger System

### 4.1 Trigger Engine Architecture

```python
# engine/trigger_engine.py

class TriggerEngine:
    """
    Central trigger detection and workflow initiation engine.

    Responsibilities:
    - Cache active triggers for fast lookup
    - Match incoming events to triggers
    - Validate conditions and domains
    - Create workflow instances
    - Enqueue first step to outbox
    """

    def __init__(self, env):
        self.env = env
        self._trigger_cache = {}
        self._cache_timestamp = None

    # ─── CACHE MANAGEMENT ───

    def _get_triggers_for_model(self, model_name, trigger_type):
        """Get cached triggers for a model and type."""
        self._refresh_cache_if_needed()
        key = f"{model_name}:{trigger_type}"
        return self._trigger_cache.get(key, [])

    def _refresh_cache_if_needed(self):
        """Refresh cache if stale (older than 60 seconds)."""
        pass  # Implementation

    def invalidate_cache(self):
        """Called when triggers are modified."""
        self._trigger_cache = {}
        self._cache_timestamp = None

    # ─── RECORD EVENT HANDLERS ───

    def on_record_create(self, model_name, records):
        """Called by mixin after create."""
        triggers = self._get_triggers_for_model(model_name, 'on_create')
        for trigger in triggers:
            matching = self._filter_by_domain(records, trigger.domain_filter)
            for record in matching:
                self._start_workflow(trigger, record)

    def on_record_write(self, model_name, records, vals, old_values):
        """Called by mixin after write."""
        # Handle on_write triggers
        triggers = self._get_triggers_for_model(model_name, 'on_write')
        for trigger in triggers:
            matching = self._filter_by_domain(records, trigger.domain_filter)
            for record in matching:
                self._start_workflow(trigger, record)

        # Handle on_field_change triggers
        field_triggers = self._get_triggers_for_model(model_name, 'on_field_change')
        for trigger in field_triggers:
            for record in records:
                if self._field_changed(trigger, record, old_values, vals):
                    self._start_workflow(trigger, record)

    def on_record_delete(self, model_name, records):
        """Called by mixin before unlink."""
        triggers = self._get_triggers_for_model(model_name, 'on_delete')
        for trigger in triggers:
            matching = self._filter_by_domain(records, trigger.domain_filter)
            for record in matching:
                # Store record data in context since record will be deleted
                context = self._record_to_context(record)
                self._start_workflow(trigger, None, context)

    # ─── FIELD CHANGE DETECTION ───

    def _field_changed(self, trigger, record, old_values, new_vals):
        """Check if watched fields changed as expected."""
        watched_fields = trigger.watched_field_ids.mapped('name')
        changed_fields = set(new_vals.keys()) & set(watched_fields)

        if not changed_fields:
            return False

        for field_name in changed_fields:
            old_val = old_values.get(record.id, {}).get(field_name)
            new_val = new_vals.get(field_name)

            # Check from/to value constraints
            if trigger.field_from_value:
                if str(old_val) != trigger.field_from_value:
                    continue
            if trigger.field_to_value:
                if str(new_val) != trigger.field_to_value:
                    continue

            return True

        return False

    # ─── SCHEDULED TRIGGERS ───

    def fire_scheduled(self, trigger_id):
        """Called by ir.cron for scheduled triggers."""
        trigger = self.env['bpm.trigger'].browse(trigger_id)
        if not trigger.exists() or not trigger.is_active:
            return

        # If workflow has target model, optionally process matching records
        if trigger.workflow_id.model_id and trigger.domain_filter:
            Model = self.env[trigger.workflow_id.model_name]
            domain = safe_eval(trigger.domain_filter or '[]')
            records = Model.search(domain)
            for record in records:
                self._start_workflow(trigger, record)
        else:
            # No record context - batch workflow
            self._start_workflow(trigger, None)

    def check_deadline_triggers(self):
        """Cron job to check all deadline-based triggers."""
        triggers = self.env['bpm.trigger'].search([
            ('trigger_type', '=', 'deadline'),
            ('is_active', '=', True),
        ])

        now = fields.Datetime.now()

        for trigger in triggers:
            Model = self.env[trigger.workflow_id.model_name]
            field_name = trigger.deadline_field_id.name

            # Calculate target datetime
            offset = timedelta(
                days=trigger.deadline_offset_days or 0,
                hours=trigger.deadline_offset_hours or 0
            )
            target_time = now - offset  # If offset is -3, we want deadline in 3 days

            # Find records where deadline matches
            domain = safe_eval(trigger.domain_filter or '[]')
            domain.append((field_name, '!=', False))
            domain.append((field_name, '<=', target_time))

            records = Model.search(domain)

            for record in records:
                # Prevent duplicate - check if already triggered
                if not self._already_triggered(trigger, record):
                    self._start_workflow(trigger, record)

    # ─── WEBHOOK TRIGGER ───

    def fire_webhook(self, endpoint_id, payload, headers, source_ip):
        """Called by webhook controller."""
        endpoint = self.env['bpm.webhook.endpoint'].browse(endpoint_id)
        if not endpoint.exists() or not endpoint.is_active:
            return {'success': False, 'error': 'Endpoint not active'}

        trigger = endpoint.trigger_id
        if not trigger.is_active:
            return {'success': False, 'error': 'Trigger not active'}

        # Validate signature if required
        if endpoint.require_signature:
            if not self._validate_webhook_signature(endpoint, payload, headers):
                return {'success': False, 'error': 'Invalid signature'}

        # Validate IP if restricted
        if endpoint.allowed_ips:
            allowed = [ip.strip() for ip in endpoint.allowed_ips.split(',')]
            if source_ip not in allowed:
                return {'success': False, 'error': 'IP not allowed'}

        # Build context from payload
        context = {'webhook_payload': payload, 'webhook_headers': headers}

        # Try to find source record if correlation provided
        record = None
        if trigger.workflow_id.model_id and payload.get('record_id'):
            Model = self.env[trigger.workflow_id.model_name]
            record = Model.browse(payload['record_id'])
            if not record.exists():
                record = None

        instance = self._start_workflow(trigger, record, context)

        return {
            'success': True,
            'instance_id': instance.id,
            'message': 'Workflow started'
        }

    # ─── MANUAL & API TRIGGERS ───

    def fire_manual(self, trigger_id, record=None, context=None):
        """Called when user clicks manual trigger button."""
        trigger = self.env['bpm.trigger'].browse(trigger_id)

        # Check permissions
        if trigger.allowed_group_ids:
            user_groups = self.env.user.groups_id
            if not (user_groups & trigger.allowed_group_ids):
                raise AccessError("You don't have permission to trigger this workflow")

        return self._start_workflow(trigger, record, context)

    def fire_api(self, workflow_code, res_model=None, res_id=None, context=None):
        """Called by external API."""
        trigger = self.env['bpm.trigger'].search([
            ('workflow_id.code', '=', workflow_code),
            ('trigger_type', '=', 'api'),
            ('is_active', '=', True),
        ], limit=1)

        if not trigger:
            raise ValueError(f"No active API trigger for workflow: {workflow_code}")

        record = None
        if res_model and res_id:
            record = self.env[res_model].browse(res_id)

        return self._start_workflow(trigger, record, context)

    # ─── WORKFLOW INITIATION ───

    def _start_workflow(self, trigger, record=None, extra_context=None):
        """Create workflow instance and enqueue first step."""
        workflow = trigger.workflow_id

        # Check for duplicate if configured
        if trigger.prevent_duplicate:
            existing = self.env['bpm.workflow.instance'].search([
                ('workflow_id', '=', workflow.id),
                ('res_model', '=', record._name if record else False),
                ('res_id', '=', record.id if record else False),
                ('state', 'in', ['draft', 'running', 'waiting', 'paused']),
            ], limit=1)
            if existing:
                return existing  # Return existing instead of creating new

        # Build context
        context = extra_context or {}
        if record:
            context['record_id'] = record.id
            context['record_model'] = record._name
            context['record_name'] = record.display_name

        # Create instance
        instance = self.env['bpm.workflow.instance'].create({
            'workflow_id': workflow.id,
            'workflow_version': workflow.version,
            'trigger_id': trigger.id,
            'res_model': record._name if record else False,
            'res_id': record.id if record else False,
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'context_json': json.dumps(context),
        })

        # Log
        self.env['bpm.execution.log'].create({
            'instance_id': instance.id,
            'log_level': 'info',
            'category': 'trigger',
            'message': f"Workflow started by trigger: {trigger.name}",
            'data_json': json.dumps({
                'trigger_type': trigger.trigger_type,
                'record': f"{record._name}({record.id})" if record else None,
            }),
        })

        # Find and enqueue start step
        start_step = workflow.step_ids.filtered('is_start_step')[:1]
        if not start_step:
            start_step = workflow.step_ids.sorted('sequence')[:1]

        if start_step:
            self._enqueue_step(instance, start_step)

        return instance

    def _enqueue_step(self, instance, step, scheduled_at=None):
        """Add step to outbox for execution."""
        # Create step log
        step_log = self.env['bpm.instance.step.log'].create({
            'instance_id': instance.id,
            'step_id': step.id,
            'action_id': step.action_id.id if step.action_id else False,
            'state': 'pending',
            'input_context': instance.context_json,
        })

        # Create outbox entry
        self.env['bpm.outbox'].create({
            'instance_id': instance.id,
            'step_log_id': step_log.id,
            'step_id': step.id,
            'idempotency_key': f"{instance.id}-{step.id}-{step_log.id}",
            'state': 'pending',
            'scheduled_at': scheduled_at or fields.Datetime.now(),
            'max_attempts': step.retry_count or 3,
        })

        # Update instance
        instance.write({
            'current_step_id': step.id,
            'current_step_log_id': step_log.id,
        })

        return step_log
```

### 4.2 ORM Trigger Mixin

```python
# models/bpm_trigger_mixin.py

class BpmTriggerMixin(models.AbstractModel):
    """
    Mixin to add BPM trigger hooks to any model.

    Models that need workflow triggers should inherit this mixin.
    The mixin intercepts create/write/unlink operations and
    notifies the trigger engine.

    Usage:
        class SaleOrder(models.Model):
            _inherit = ['sale.order', 'bpm.trigger.mixin']
    """
    _name = 'bpm.trigger.mixin'
    _description = 'BPM Trigger Mixin'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger on_create workflows."""
        records = super().create(vals_list)

        # Notify trigger engine (async-safe)
        if not self.env.context.get('bpm_skip_triggers'):
            self.env['bpm.trigger.engine']._on_create(
                self._name,
                records
            )

        return records

    def write(self, vals):
        """Override write to trigger on_write and on_field_change workflows."""
        # Capture old values for field change detection
        old_values = {}
        if not self.env.context.get('bpm_skip_triggers'):
            # Get fields that might be watched
            watched_fields = self._bpm_get_watched_fields()
            if watched_fields:
                for record in self:
                    old_values[record.id] = {
                        f: record[f] for f in watched_fields
                        if f in vals  # Only track changing fields
                    }

        result = super().write(vals)

        # Notify trigger engine
        if not self.env.context.get('bpm_skip_triggers'):
            self.env['bpm.trigger.engine']._on_write(
                self._name,
                self,
                vals,
                old_values
            )

        return result

    def unlink(self):
        """Override unlink to trigger on_delete workflows."""
        # Notify trigger engine BEFORE delete
        if not self.env.context.get('bpm_skip_triggers'):
            self.env['bpm.trigger.engine']._on_delete(
                self._name,
                self
            )

        return super().unlink()

    def _bpm_get_watched_fields(self):
        """Get list of fields watched by active triggers."""
        triggers = self.env['bpm.trigger'].search([
            ('trigger_type', '=', 'on_field_change'),
            ('is_active', '=', True),
            '|',
            ('model_id.model', '=', self._name),
            ('workflow_id.model_id.model', '=', self._name),
        ])
        fields = set()
        for trigger in triggers:
            fields.update(trigger.watched_field_ids.mapped('name'))
        return list(fields)

    def bpm_start_workflow(self, workflow_code, context=None):
        """
        Manually start a workflow for this record.

        Args:
            workflow_code: Code of the workflow to start
            context: Optional additional context dict

        Returns:
            bpm.workflow.instance record
        """
        self.ensure_one()
        return self.env['bpm.trigger.engine'].fire_api(
            workflow_code,
            res_model=self._name,
            res_id=self.id,
            context=context
        )
```

---

## 5. Execution Engine

### 5.1 Orchestrator Overview

The Orchestrator is the cron-based worker that processes the outbox queue.

```python
# engine/orchestrator.py

class BpmOrchestrator(models.TransientModel):
    """
    Cron-based workflow execution orchestrator.

    Responsibilities:
    - Poll bpm.outbox for pending items
    - Lock items to prevent duplicate processing
    - Dispatch to appropriate step executor
    - Handle success/failure and determine next step
    - Manage retries with exponential backoff
    """
    _name = 'bpm.orchestrator'
    _description = 'BPM Workflow Orchestrator'

    @api.model
    def process_outbox(self):
        """Main entry point - called by ir.cron every minute."""
        batch_size = int(self.env['ir.config_parameter'].sudo().get_param(
            'bpm.orchestrator_batch_size', '50'
        ))

        items = self._acquire_items(batch_size)

        for item in items:
            try:
                self._process_item(item)
            except Exception as e:
                self._handle_item_error(item, e)
            finally:
                self.env.cr.commit()

    def _acquire_items(self, batch_size):
        """Acquire outbox items with pessimistic locking."""
        worker_id = f"{socket.gethostname()}-{os.getpid()}"
        now = fields.Datetime.now()

        self.env.cr.execute("""
            UPDATE bpm_outbox
            SET state = 'processing',
                locked_at = %s,
                locked_by = %s,
                started_at = COALESCE(started_at, %s)
            WHERE id IN (
                SELECT id FROM bpm_outbox
                WHERE state = 'pending'
                  AND scheduled_at <= %s
                  AND (locked_at IS NULL
                       OR locked_at < %s)
                ORDER BY scheduled_at, id
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
        """, (now, worker_id, now, now,
              now - timedelta(minutes=10),
              batch_size))

        item_ids = [row[0] for row in self.env.cr.fetchall()]
        return self.env['bpm.outbox'].browse(item_ids)

    def _process_item(self, item):
        """Process a single outbox item."""
        instance = item.instance_id
        step = item.step_id
        step_log = item.step_log_id

        if instance.state not in ('running', 'waiting'):
            item.write({'state': 'cancelled'})
            return

        step_log.write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'attempt_number': item.attempt_count + 1,
        })

        executor = self._get_executor(step.step_type)
        ctx = self._build_context(instance, step_log)

        start_time = time.time()
        result = executor.execute(step, ctx)
        duration_ms = int((time.time() - start_time) * 1000)

        self._handle_result(item, step_log, result, duration_ms)

    def _get_executor(self, step_type):
        """Get the appropriate executor for a step type."""
        executor_map = {
            'action': 'bpm.executor.action',
            'condition': 'bpm.executor.condition',
            'parallel_split': 'bpm.executor.parallel.split',
            'parallel_join': 'bpm.executor.parallel.join',
            'human_task': 'bpm.executor.human.task',
            'wait_event': 'bpm.executor.wait.event',
            'delay': 'bpm.executor.delay',
            'stop': 'bpm.executor.stop',
        }

        model_name = executor_map.get(step_type)
        if not model_name:
            raise ValueError(f"Unknown step type: {step_type}")

        return self.env[model_name]

    def _build_context(self, instance, step_log):
        """Build execution context dict available to all executors."""
        ctx = json.loads(instance.context_json or '{}')

        ctx['_instance_id'] = instance.id
        ctx['_step_log_id'] = step_log.id
        ctx['_workflow_code'] = instance.workflow_code

        if instance.res_model and instance.res_id:
            record = self.env[instance.res_model].browse(instance.res_id)
            if record.exists():
                ctx['_record'] = record

        ctx['_user'] = self.env.user
        ctx['_company'] = self.env.company
        ctx['_now'] = fields.Datetime.now()

        return ctx
```

### 5.2 Result Handling & Retry Logic

```python
    def _handle_result(self, item, step_log, result, duration_ms):
        """Process executor result and determine next action."""
        if result.get('success'):
            self._handle_success(item, step_log, result, duration_ms)
        else:
            self._handle_failure(item, step_log, result, duration_ms)

    def _handle_success(self, item, step_log, result, duration_ms):
        """Handle successful step execution."""
        instance = item.instance_id

        step_log.write({
            'state': 'done',
            'ended_at': fields.Datetime.now(),
            'duration_ms': duration_ms,
            'output_result': json.dumps(result.get('output', {})),
            'context_updates': json.dumps(result.get('context_updates', {})),
        })

        if result.get('context_updates'):
            ctx = json.loads(instance.context_json or '{}')
            ctx.update(result['context_updates'])
            instance.write({'context_json': json.dumps(ctx)})

        item.write({
            'state': 'done',
            'completed_at': fields.Datetime.now(),
            'processing_time_ms': duration_ms,
        })

        self._enqueue_next_steps(instance, step_log, result)

    def _handle_failure(self, item, step_log, result, duration_ms):
        """Handle failed step execution with retry logic."""
        instance = item.instance_id
        step = item.step_id
        error_msg = result.get('error', 'Unknown error')

        step_log.write({
            'state': 'failed',
            'ended_at': fields.Datetime.now(),
            'duration_ms': duration_ms,
            'error_message': error_msg,
            'error_traceback': result.get('traceback', ''),
        })

        attempt = item.attempt_count + 1
        max_attempts = step.retry_count or 3

        if attempt < max_attempts:
            self._schedule_retry(item, step_log, attempt, max_attempts)
        else:
            self._handle_final_failure(item, step_log, error_msg)

    def _schedule_retry(self, item, step_log, attempt, max_attempts):
        """Schedule a retry with exponential backoff + jitter."""
        base_delay = int(self.env['ir.config_parameter'].sudo().get_param(
            'bpm.outbox_retry_delay', '5'
        ))

        backoff = base_delay * (5 ** (attempt - 1))
        jitter = backoff * 0.2 * (random.random() * 2 - 1)
        delay_minutes = max(1, backoff + jitter)

        next_retry = fields.Datetime.now() + timedelta(minutes=delay_minutes)

        item.write({
            'state': 'pending',
            'attempt_count': attempt,
            'scheduled_at': next_retry,
            'next_retry_at': next_retry,
            'last_error': step_log.error_message,
            'error_count': item.error_count + 1,
            'locked_at': False,
            'locked_by': False,
        })

    def _handle_final_failure(self, item, step_log, error_msg):
        """Handle unrecoverable failure after all retries exhausted."""
        instance = item.instance_id
        step = item.step_id

        item.write({
            'state': 'failed',
            'completed_at': fields.Datetime.now(),
            'last_error': error_msg,
        })

        if step.on_error_step_id:
            self._enqueue_step(instance, step.on_error_step_id)
        else:
            instance.write({
                'state': 'failed',
                'ended_at': fields.Datetime.now(),
                'error_message': f"Step '{step.name}' failed: {error_msg}",
                'last_error_step_id': step.id,
            })
            self._cancel_pending_items(instance)
```

### 5.3 Parallel Branch Management

```python
    def _enqueue_next_steps(self, instance, step_log, result):
        """Determine and enqueue the next step(s) to execute."""
        step = step_log.step_id

        if result.get('next_step_ids'):
            self._create_parallel_branches(instance, step_log, result['next_step_ids'])
            return

        if result.get('next_step_id'):
            next_step = self.env['bpm.workflow.step'].browse(result['next_step_id'])
            self._enqueue_step(instance, next_step)
            return

        if result.get('wait_until'):
            instance.write({'state': 'waiting'})
            self._enqueue_step(instance, step, scheduled_at=result['wait_until'])
            return

        if step.next_step_id:
            self._enqueue_step(instance, step.next_step_id)
            return

        if step_log.branch_id:
            self._complete_branch(step_log.branch_id)
            return

        self._complete_workflow(instance)

    def _create_parallel_branches(self, instance, split_step_log, next_step_ids):
        """Create parallel branches for concurrent execution."""
        step = split_step_log.step_id
        join_step = step.join_step_id

        for idx, step_id in enumerate(next_step_ids):
            branch = self.env['bpm.parallel.branch'].create({
                'instance_id': instance.id,
                'split_step_log_id': split_step_log.id,
                'join_step_id': join_step.id if join_step else False,
                'branch_index': idx,
                'first_step_id': step_id,
                'state': 'running',
                'started_at': fields.Datetime.now(),
            })

            next_step = self.env['bpm.workflow.step'].browse(step_id)
            self._enqueue_step(instance, next_step, branch_id=branch.id)

    def _complete_branch(self, branch):
        """Mark a parallel branch as complete and check join condition."""
        branch.write({
            'state': 'done',
            'ended_at': fields.Datetime.now(),
        })

        instance = branch.instance_id
        join_step = branch.join_step_id

        if not join_step:
            self._check_all_branches_complete(instance)
            return

        split_log = branch.split_step_log_id
        all_branches = self.env['bpm.parallel.branch'].search([
            ('split_step_log_id', '=', split_log.id)
        ])

        split_step = split_log.step_id
        join_type = split_step.join_type or 'all'

        if join_type == 'all':
            if all(b.state == 'done' for b in all_branches):
                self._execute_join(instance, join_step, all_branches)
        elif join_type == 'any':
            self._execute_join(instance, join_step, all_branches)
            for b in all_branches:
                if b.state == 'running':
                    self._cancel_branch(b)

    def _complete_workflow(self, instance):
        """Mark workflow instance as successfully completed."""
        instance.write({
            'state': 'done',
            'ended_at': fields.Datetime.now(),
        })
```

### 5.4 Step Executors

```python
# engine/executors/base.py

class BpmExecutorBase(models.TransientModel):
    """Base class for all step executors."""
    _name = 'bpm.executor.base'
    _description = 'BPM Executor Base'

    def execute(self, step, ctx):
        """Execute the step logic. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")

    def _safe_eval(self, expression, ctx):
        """Safely evaluate a Python expression."""
        if not expression:
            return None

        record = ctx.get('_record')

        eval_context = {
            'record': record,
            'ctx': ctx,
            'env': self.env,
            'user': self.env.user,
            'company': self.env.company,
            'datetime': datetime,
            'date': date,
            'timedelta': timedelta,
            'json': json,
            'True': True,
            'False': False,
            'None': None,
        }

        return safe_eval(expression, eval_context, mode='eval', nocopy=True)

    def _render_jinja(self, template, ctx):
        """Render a Jinja2 template with context."""
        if not template:
            return ''

        record = ctx.get('_record')

        jinja_ctx = {
            'record': record,
            'ctx': ctx,
            'user': self.env.user,
            'company': self.env.company,
            'now': fields.Datetime.now(),
        }

        env = jinja2.Environment(autoescape=True)
        tmpl = env.from_string(template)
        return tmpl.render(**jinja_ctx)


# engine/executors/condition.py

class BpmExecutorCondition(models.TransientModel):
    """Executor for condition gateway steps."""
    _name = 'bpm.executor.condition'
    _inherit = 'bpm.executor.base'

    def execute(self, step, ctx):
        try:
            expression = step.condition_expression
            if not expression:
                return {'success': False, 'error': 'No condition expression defined'}

            result = self._safe_eval(expression, ctx)

            if result:
                next_step_id = step.on_true_step_id.id if step.on_true_step_id else None
                branch = 'true'
            else:
                next_step_id = step.on_false_step_id.id if step.on_false_step_id else None
                branch = 'false'

            return {
                'success': True,
                'next_step_id': next_step_id,
                'output': {'condition_result': bool(result), 'branch_taken': branch},
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


# engine/executors/human_task.py

class BpmExecutorHumanTask(models.TransientModel):
    """Executor for human task steps."""
    _name = 'bpm.executor.human.task'
    _inherit = 'bpm.executor.base'

    def execute(self, step, ctx):
        try:
            instance_id = ctx['_instance_id']
            step_log_id = ctx['_step_log_id']

            assignee_id = self._resolve_assignee(step, ctx)

            deadline = None
            if step.task_deadline_hours:
                deadline = fields.Datetime.now() + timedelta(hours=step.task_deadline_hours)

            task = self.env['bpm.task'].create({
                'name': self._render_jinja(step.task_title, ctx) or step.name,
                'instance_id': instance_id,
                'step_log_id': step_log_id,
                'step_id': step.id,
                'instructions': self._render_jinja(step.task_instructions, ctx),
                'assignee_id': assignee_id,
                'assignee_group_id': step.assignee_group_id.id if not assignee_id else False,
                'deadline': deadline,
                'state': 'pending',
            })

            step_log = self.env['bpm.instance.step.log'].browse(step_log_id)
            step_log.write({
                'state': 'waiting',
                'task_id': task.id,
                'assignee_id': assignee_id,
            })

            return {
                'success': True,
                'output': {
                    'task_id': task.id,
                    'assignee': task.assignee_id.name if task.assignee_id else 'Unassigned',
                },
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

    def _resolve_assignee(self, step, ctx):
        """Determine the user to assign the task to."""
        if step.assignee_type == 'user':
            return step.assignee_user_id.id
        elif step.assignee_type == 'field':
            record = ctx.get('_record')
            if record and step.assignee_field_id:
                user = record[step.assignee_field_id.name]
                if user and user._name == 'res.users':
                    return user.id
        elif step.assignee_type == 'expression':
            result = self._safe_eval(step.assignee_expression, ctx)
            if isinstance(result, int):
                return result
            elif hasattr(result, 'id'):
                return result.id
        return None


# engine/executors/delay.py

class BpmExecutorDelay(models.TransientModel):
    """Executor for delay/timer steps."""
    _name = 'bpm.executor.delay'
    _inherit = 'bpm.executor.base'

    def execute(self, step, ctx):
        try:
            delay_minutes = self._calculate_delay(step, ctx)

            if delay_minutes <= 0:
                return {
                    'success': True,
                    'next_step_id': step.next_step_id.id if step.next_step_id else None,
                    'output': {'delay_minutes': 0},
                }

            wait_until = fields.Datetime.now() + timedelta(minutes=delay_minutes)

            return {
                'success': True,
                'wait_until': wait_until,
                'next_step_id': step.next_step_id.id if step.next_step_id else None,
                'output': {'delay_minutes': delay_minutes, 'resume_at': wait_until.isoformat()},
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

    def _calculate_delay(self, step, ctx):
        """Calculate delay in minutes based on configuration."""
        if step.delay_type == 'fixed':
            return (
                (step.delay_days or 0) * 24 * 60 +
                (step.delay_hours or 0) * 60 +
                (step.delay_minutes or 0)
            )
        elif step.delay_type == 'expression':
            result = self._safe_eval(step.delay_expression, ctx)
            return int(result) if result else 0
        return 0
```

### 5.5 Cron Configuration

```xml
<!-- data/cron_data.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="ir_cron_bpm_orchestrator" model="ir.cron">
        <field name="name">BPM: Process Workflow Queue</field>
        <field name="model_id" ref="model_bpm_orchestrator"/>
        <field name="state">code</field>
        <field name="code">model.process_outbox()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
        <field name="priority">5</field>
    </record>

    <record id="ir_cron_bpm_deadline_check" model="ir.cron">
        <field name="name">BPM: Check Deadline Triggers</field>
        <field name="model_id" ref="model_bpm_trigger_engine"/>
        <field name="state">code</field>
        <field name="code">model.check_deadline_triggers()</field>
        <field name="interval_number">15</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>

    <record id="ir_cron_bpm_escalation_check" model="ir.cron">
        <field name="name">BPM: Check Task Escalations</field>
        <field name="model_id" ref="model_bpm_task"/>
        <field name="state">code</field>
        <field name="code">model.check_escalations()</field>
        <field name="interval_number">15</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active">True</field>
    </record>
</odoo>
```

---

## 6. Action Executors

### 6.1 Action Engine

```python
# engine/action_engine.py

class BpmActionEngine(models.TransientModel):
    """Central action execution engine."""
    _name = 'bpm.action.engine'
    _description = 'BPM Action Engine'

    ACTION_EXECUTORS = {
        'update_record': 'bpm.action.executor.update.record',
        'create_record': 'bpm.action.executor.create.record',
        'delete_record': 'bpm.action.executor.delete.record',
        'link_records': 'bpm.action.executor.link.records',
        'server_action': 'bpm.action.executor.server.action',
        'send_email': 'bpm.action.executor.send.email',
        'send_message': 'bpm.action.executor.send.message',
        'send_sms': 'bpm.action.executor.send.sms',
        'create_activity': 'bpm.action.executor.create.activity',
        'http_request': 'bpm.action.executor.http.request',
        'webhook_call': 'bpm.action.executor.webhook.call',
        'execute_python': 'bpm.action.executor.execute.python',
    }

    def execute_action(self, action, ctx):
        """Execute an action and return result."""
        executor_model = self.ACTION_EXECUTORS.get(action.action_type)

        if not executor_model:
            return {'success': False, 'error': f"Unknown action type: {action.action_type}"}

        executor = self.env[executor_model]
        return executor.execute(action, ctx)
```

### 6.2 Record Action Executors

```python
# engine/action_executors/update_record.py

class BpmActionExecutorUpdateRecord(models.TransientModel):
    """Executor for update_record actions."""
    _name = 'bpm.action.executor.update.record'
    _inherit = 'bpm.action.executor.base'

    def execute(self, action, ctx):
        try:
            record = self._get_target_record(action, ctx)
            if not record:
                return {'success': False, 'error': 'No target record found'}

            values = self._resolve_field_mappings(action, ctx)

            if not values:
                return {'success': False, 'error': 'No field mappings defined'}

            record.with_context(bpm_skip_triggers=True).write(values)

            return {
                'success': True,
                'output': {
                    'record_id': record.id,
                    'model': record._name,
                    'updated_fields': list(values.keys()),
                },
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


# engine/action_executors/create_record.py

class BpmActionExecutorCreateRecord(models.TransientModel):
    """Executor for create_record actions."""
    _name = 'bpm.action.executor.create.record'
    _inherit = 'bpm.action.executor.base'

    def execute(self, action, ctx):
        try:
            model_name = self._get_target_model(action, ctx)
            if not model_name:
                return {'success': False, 'error': 'No target model specified'}

            values = self._resolve_field_mappings(action, ctx)

            Model = self.env[model_name]
            new_record = Model.with_context(bpm_skip_triggers=True).create(values)

            return {
                'success': True,
                'output': {
                    'record_id': new_record.id,
                    'model': model_name,
                },
                'context_updates': {
                    'created_record_id': new_record.id,
                    'created_record_model': model_name,
                },
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}
```

### 6.3 Communication Executors

```python
# engine/action_executors/send_email.py

class BpmActionExecutorSendEmail(models.TransientModel):
    """Executor for send_email actions."""
    _name = 'bpm.action.executor.send.email'
    _inherit = 'bpm.action.executor.base'

    def execute(self, action, ctx):
        try:
            record = ctx.get('_record')

            if action.mail_template_id:
                mail_id = action.mail_template_id.send_mail(record.id, force_send=True)
                return {
                    'success': True,
                    'output': {'mail_id': mail_id, 'template_used': action.mail_template_id.name},
                }

            email_to = self._safe_eval(action.email_to, ctx) if action.email_to else None
            if not email_to:
                return {'success': False, 'error': 'No recipient email address'}

            subject = self._render_jinja(action.email_subject, ctx)
            body = self._render_jinja(action.email_body, ctx)

            mail = self.env['mail.mail'].create({
                'subject': subject,
                'body_html': body,
                'email_to': email_to if isinstance(email_to, str) else ','.join(email_to),
                'auto_delete': True,
            })

            mail.send()

            return {
                'success': True,
                'output': {'mail_id': mail.id, 'email_to': email_to, 'subject': subject},
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}


# engine/action_executors/send_message.py

class BpmActionExecutorSendMessage(models.TransientModel):
    """Executor for send_message (post to chatter)."""
    _name = 'bpm.action.executor.send.message'
    _inherit = 'bpm.action.executor.base'

    def execute(self, action, ctx):
        try:
            record = ctx.get('_record')
            if not record:
                return {'success': False, 'error': 'No record to post message to'}

            if not hasattr(record, 'message_post'):
                return {'success': False, 'error': f'Model {record._name} does not support messages'}

            body = self._render_jinja(action.message_body, ctx)

            partner_ids = []
            if action.message_partner_ids_expr:
                result = self._safe_eval(action.message_partner_ids_expr, ctx)
                if isinstance(result, list):
                    partner_ids = result
                elif hasattr(result, 'ids'):
                    partner_ids = result.ids

            message = record.message_post(
                body=body,
                subtype_id=action.message_subtype_id.id if action.message_subtype_id else None,
                partner_ids=partner_ids,
            )

            return {
                'success': True,
                'output': {'message_id': message.id, 'record': f"{record._name}({record.id})"},
            }

        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}
```

### 6.4 HTTP Request Executor

```python
# engine/action_executors/http_request.py

class BpmActionExecutorHttpRequest(models.TransientModel):
    """Executor for http_request actions."""
    _name = 'bpm.action.executor.http.request'
    _inherit = 'bpm.action.executor.base'

    def execute(self, action, ctx):
        try:
            url = self._render_jinja(action.http_url, ctx)
            if not url:
                return {'success': False, 'error': 'No URL specified'}

            headers = {'Content-Type': 'application/json'}
            if action.http_headers:
                custom_headers = json.loads(self._render_jinja(action.http_headers, ctx))
                headers.update(custom_headers)

            auth = None
            if action.http_auth_type == 'basic':
                auth = (action.http_auth_user, action.http_auth_password)
            elif action.http_auth_type == 'bearer':
                headers['Authorization'] = f'Bearer {action.http_auth_password}'
            elif action.http_auth_type == 'api_key':
                headers[action.http_auth_user] = action.http_auth_password

            body = None
            if action.http_body and action.http_method in ('POST', 'PUT', 'PATCH'):
                body = self._render_jinja(action.http_body, ctx)

            timeout = action.http_timeout or 30

            response = requests.request(
                method=action.http_method,
                url=url,
                headers=headers,
                data=body,
                auth=auth,
                timeout=timeout,
            )

            success_codes = [int(c.strip()) for c in (action.http_success_codes or '200,201,202,204').split(',')]
            is_success = response.status_code in success_codes

            try:
                response_json = response.json()
            except:
                response_json = None

            if not is_success:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text[:500]}',
                }

            return {
                'success': True,
                'output': {
                    'status_code': response.status_code,
                    'response': response_json or response.text[:1000],
                },
                'context_updates': {
                    'http_response': response_json or response.text,
                    'http_status': response.status_code,
                },
            }

        except requests.Timeout:
            return {'success': False, 'error': f'HTTP request timeout after {action.http_timeout}s'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}
```

---

## 7. Dashboard & UI

### 7.1 Menu Structure

```xml
<!-- views/menu.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_bpm_root"
              name="BPM Automation"
              web_icon="bpm_automation,static/description/icon.png"
              sequence="100"/>

    <menuitem id="menu_bpm_workflows"
              name="Workflows"
              parent="menu_bpm_root"
              sequence="10"/>

    <menuitem id="menu_bpm_workflow_list"
              name="Workflow Definitions"
              parent="menu_bpm_workflows"
              action="action_bpm_workflow"
              sequence="10"/>

    <menuitem id="menu_bpm_instances"
              name="Instances"
              parent="menu_bpm_root"
              sequence="20"/>

    <menuitem id="menu_bpm_tasks"
              name="Tasks"
              parent="menu_bpm_root"
              sequence="30"/>

    <menuitem id="menu_bpm_task_my"
              name="My Tasks"
              parent="menu_bpm_tasks"
              action="action_bpm_task_my"
              sequence="10"/>

    <menuitem id="menu_bpm_monitoring"
              name="Monitoring"
              parent="menu_bpm_root"
              sequence="40"/>

    <menuitem id="menu_bpm_dashboard"
              name="Dashboard"
              parent="menu_bpm_monitoring"
              action="action_bpm_dashboard"
              sequence="10"/>

    <menuitem id="menu_bpm_config"
              name="Configuration"
              parent="menu_bpm_root"
              sequence="90"
              groups="bpm_automation.group_bpm_admin"/>
</odoo>
```

### 7.2 Workflow Form View

```xml
<!-- views/bpm_workflow_views.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_bpm_workflow_form" model="ir.ui.view">
        <field name="name">bpm.workflow.form</field>
        <field name="model">bpm.workflow</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="action_activate" type="object"
                            string="Activate" class="btn-primary"
                            invisible="state != 'draft'"/>
                    <button name="action_deactivate" type="object"
                            string="Deactivate"
                            invisible="state != 'active'"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_instances" type="object"
                                class="oe_stat_button" icon="fa-play-circle">
                            <field name="instance_count" widget="statinfo" string="Instances"/>
                        </button>
                    </div>
                    <div class="oe_title">
                        <h1><field name="name" placeholder="Workflow Name"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="code"/>
                            <field name="model_id" options="{'no_create': True}"/>
                        </group>
                        <group>
                            <field name="version"/>
                            <field name="is_latest"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Steps" name="steps">
                            <field name="step_ids">
                                <tree editable="bottom">
                                    <field name="sequence" widget="handle"/>
                                    <field name="is_start_step" widget="boolean_toggle"/>
                                    <field name="name"/>
                                    <field name="step_type"/>
                                    <field name="action_id" invisible="step_type != 'action'"/>
                                    <field name="next_step_id"/>
                                </tree>
                            </field>
                        </page>
                        <page string="Triggers" name="triggers">
                            <field name="trigger_ids">
                                <tree editable="bottom">
                                    <field name="sequence" widget="handle"/>
                                    <field name="is_active" widget="boolean_toggle"/>
                                    <field name="name"/>
                                    <field name="trigger_type"/>
                                    <field name="domain_filter"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>
</odoo>
```

### 7.3 Task Kanban View

```xml
<!-- views/bpm_task_views.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_bpm_task_kanban" model="ir.ui.view">
        <field name="name">bpm.task.kanban</field>
        <field name="model">bpm.task</field>
        <field name="arch" type="xml">
            <kanban default_group_by="state">
                <field name="name"/>
                <field name="state"/>
                <field name="assignee_id"/>
                <field name="deadline"/>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_card oe_kanban_global_click">
                            <div class="oe_kanban_content">
                                <div class="o_kanban_record_title">
                                    <strong><field name="name"/></strong>
                                </div>
                                <div class="o_kanban_record_body">
                                    <field name="assignee_id" widget="many2one_avatar_user"/>
                                    <span t-if="record.deadline.raw_value" class="float-end badge">
                                        <field name="deadline"/>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>
        </field>
    </record>

    <record id="view_bpm_task_form" model="ir.ui.view">
        <field name="name">bpm.task.form</field>
        <field name="model">bpm.task</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="action_approve" type="object"
                            string="Approve" class="btn-success"
                            invisible="state not in ('pending', 'claimed')"/>
                    <button name="action_reject" type="object"
                            string="Reject" class="btn-danger"
                            invisible="state not in ('pending', 'claimed')"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="instance_id"/>
                            <field name="assignee_id"/>
                        </group>
                        <group>
                            <field name="deadline"/>
                            <field name="escalation_level"/>
                        </group>
                    </group>
                    <group string="Instructions">
                        <field name="instructions" nolabel="1"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="action_bpm_task_my" model="ir.actions.act_window">
        <field name="name">My Tasks</field>
        <field name="res_model">bpm.task</field>
        <field name="view_mode">kanban,tree,form</field>
        <field name="domain">[
            '|',
            ('assignee_id', '=', uid),
            '&amp;',
            ('assignee_id', '=', False),
            ('assignee_group_id', 'in', user.groups_id.ids)
        ]</field>
        <field name="context">{'search_default_pending': 1}</field>
    </record>
</odoo>
```

---

## 8. API Endpoints

### 8.1 Webhook Controller

```python
# controllers/webhook.py

from odoo import http
from odoo.http import request
import json
import hmac
import hashlib

class BpmWebhookController(http.Controller):

    @http.route('/bpm/webhook/<string:token>', type='json', auth='public', csrf=False)
    def webhook_handler(self, token, **kwargs):
        """Incoming webhook endpoint."""
        endpoint = request.env['bpm.webhook.endpoint'].sudo().search([
            ('token', '=', token),
            ('is_active', '=', True),
        ], limit=1)

        if not endpoint:
            return {'success': False, 'error': 'Invalid webhook endpoint'}

        payload = request.jsonrequest
        headers = dict(request.httprequest.headers)
        source_ip = request.httprequest.remote_addr

        if endpoint.require_signature:
            if not self._validate_signature(endpoint, payload, headers.get('X-Bpm-Signature', '')):
                return {'success': False, 'error': 'Invalid signature'}

        try:
            trigger_engine = request.env['bpm.trigger.engine'].sudo()
            result = trigger_engine.fire_webhook(endpoint.id, payload, headers, source_ip)

            endpoint.sudo().write({
                'last_called_at': fields.Datetime.now(),
                'call_count': endpoint.call_count + 1,
            })

            return result

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _validate_signature(self, endpoint, payload, provided_sig):
        """Validate HMAC signature."""
        if not endpoint.secret_key:
            return True

        if not provided_sig.startswith('sha256='):
            return False

        provided_hash = provided_sig[7:]
        payload_bytes = json.dumps(payload).encode()
        expected_hash = hmac.new(
            endpoint.secret_key.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(provided_hash, expected_hash)
```

### 8.2 REST API Controller

```python
# controllers/api.py

from odoo import http
from odoo.http import request

class BpmApiController(http.Controller):

    @http.route('/api/bpm/workflows', type='json', auth='user', methods=['GET'])
    def list_workflows(self):
        """List all active workflows."""
        workflows = request.env['bpm.workflow'].search([
            ('state', '=', 'active'),
            ('is_latest', '=', True),
        ])

        return {
            'success': True,
            'workflows': [{
                'id': w.id,
                'name': w.name,
                'code': w.code,
                'model': w.model_name,
            } for w in workflows]
        }

    @http.route('/api/bpm/workflows/<string:code>/start', type='json', auth='user', methods=['POST'])
    def start_workflow(self, code, **kwargs):
        """Start a workflow via API."""
        payload = request.jsonrequest

        try:
            trigger_engine = request.env['bpm.trigger.engine']
            instance = trigger_engine.fire_api(
                workflow_code=code,
                res_model=payload.get('res_model'),
                res_id=payload.get('res_id'),
                context=payload.get('context', {}),
            )

            return {'success': True, 'instance_id': instance.id}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/api/bpm/instances/<int:instance_id>', type='json', auth='user', methods=['GET'])
    def get_instance(self, instance_id):
        """Get workflow instance details."""
        instance = request.env['bpm.workflow.instance'].browse(instance_id)

        if not instance.exists():
            return {'success': False, 'error': 'Instance not found'}

        return {
            'success': True,
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'workflow': instance.workflow_id.name,
                'state': instance.state,
                'progress': instance.progress_percent,
            }
        }

    @http.route('/api/bpm/tasks/<int:task_id>/complete', type='json', auth='user', methods=['POST'])
    def complete_task(self, task_id, **kwargs):
        """Complete a task with decision."""
        task = request.env['bpm.task'].browse(task_id)

        if not task.exists():
            return {'success': False, 'error': 'Task not found'}

        payload = request.jsonrequest
        decision = payload.get('decision', 'approve')

        if decision == 'approve':
            task.action_approve(comment=payload.get('comment'))
        elif decision == 'reject':
            task.action_reject(comment=payload.get('comment'))

        return {'success': True, 'state': task.state}
```

---

## 9. Security

### 9.1 Security Groups

```xml
<!-- security/security.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="module_category_bpm" model="ir.module.category">
        <field name="name">BPM Automation</field>
        <field name="sequence">50</field>
    </record>

    <record id="group_bpm_user" model="res.groups">
        <field name="name">BPM User</field>
        <field name="category_id" ref="module_category_bpm"/>
    </record>

    <record id="group_bpm_designer" model="res.groups">
        <field name="name">BPM Designer</field>
        <field name="category_id" ref="module_category_bpm"/>
        <field name="implied_ids" eval="[(4, ref('group_bpm_user'))]"/>
    </record>

    <record id="group_bpm_manager" model="res.groups">
        <field name="name">BPM Manager</field>
        <field name="category_id" ref="module_category_bpm"/>
        <field name="implied_ids" eval="[(4, ref('group_bpm_designer'))]"/>
    </record>

    <record id="group_bpm_admin" model="res.groups">
        <field name="name">BPM Administrator</field>
        <field name="category_id" ref="module_category_bpm"/>
        <field name="implied_ids" eval="[(4, ref('group_bpm_manager'))]"/>
    </record>
</odoo>
```

### 9.2 Access Rules

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_bpm_workflow_user,bpm.workflow.user,model_bpm_workflow,group_bpm_user,1,0,0,0
access_bpm_workflow_designer,bpm.workflow.designer,model_bpm_workflow,group_bpm_designer,1,1,1,0
access_bpm_workflow_admin,bpm.workflow.admin,model_bpm_workflow,group_bpm_admin,1,1,1,1
access_bpm_instance_user,bpm.workflow.instance.user,model_bpm_workflow_instance,group_bpm_user,1,0,0,0
access_bpm_instance_manager,bpm.workflow.instance.manager,model_bpm_workflow_instance,group_bpm_manager,1,1,1,1
access_bpm_task_user,bpm.task.user,model_bpm_task,group_bpm_user,1,1,0,0
access_bpm_task_manager,bpm.task.manager,model_bpm_task,group_bpm_manager,1,1,1,1
```

### 9.3 Record Rules

```xml
<!-- security/record_rules.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="rule_bpm_task_user" model="ir.rule">
        <field name="name">BPM Task: User sees own tasks</field>
        <field name="model_id" ref="model_bpm_task"/>
        <field name="groups" eval="[(4, ref('group_bpm_user'))]"/>
        <field name="domain_force">[
            '|',
            ('assignee_id', '=', user.id),
            '&amp;',
            ('assignee_id', '=', False),
            ('assignee_group_id', 'in', user.groups_id.ids)
        ]</field>
    </record>

    <record id="rule_bpm_task_manager" model="ir.rule">
        <field name="name">BPM Task: Manager sees all</field>
        <field name="model_id" ref="model_bpm_task"/>
        <field name="groups" eval="[(4, ref('group_bpm_manager'))]"/>
        <field name="domain_force">[(1, '=', 1)]</field>
    </record>
</odoo>
```

---

## 10. Configuration

### 10.1 Default Settings

```xml
<!-- data/config_data.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo noupdate="1">
    <record id="config_orchestrator_batch_size" model="bpm.config.setting">
        <field name="key">orchestrator_batch_size</field>
        <field name="value">50</field>
        <field name="value_type">integer</field>
        <field name="description">Items per cron tick</field>
    </record>

    <record id="config_outbox_retry_delay" model="bpm.config.setting">
        <field name="key">outbox_retry_delay</field>
        <field name="value">5</field>
        <field name="value_type">integer</field>
        <field name="description">Base retry delay (minutes)</field>
    </record>

    <record id="config_outbox_max_retries" model="bpm.config.setting">
        <field name="key">outbox_max_retries</field>
        <field name="value">3</field>
        <field name="value_type">integer</field>
        <field name="description">Max retry attempts</field>
    </record>

    <record id="config_log_retention_days" model="bpm.config.setting">
        <field name="key">log_retention_days</field>
        <field name="value">90</field>
        <field name="value_type">integer</field>
        <field name="description">Days to keep logs</field>
    </record>
</odoo>
```

---

## 11. File Structure

```
bpm_automation/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── api.py
│   └── webhook.py
├── data/
│   ├── config_data.xml
│   └── cron_data.xml
├── engine/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── trigger_engine.py
│   ├── action_engine.py
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── condition.py
│   │   ├── parallel_split.py
│   │   ├── parallel_join.py
│   │   ├── human_task.py
│   │   ├── wait_event.py
│   │   ├── delay.py
│   │   ├── stop.py
│   │   └── action.py
│   └── action_executors/
│       ├── __init__.py
│       ├── base.py
│       ├── update_record.py
│       ├── create_record.py
│       ├── send_email.py
│       ├── send_message.py
│       └── http_request.py
├── models/
│   ├── __init__.py
│   ├── bpm_workflow.py
│   ├── bpm_workflow_step.py
│   ├── bpm_action.py
│   ├── bpm_trigger.py
│   ├── bpm_workflow_instance.py
│   ├── bpm_instance_step_log.py
│   ├── bpm_task.py
│   ├── bpm_outbox.py
│   └── bpm_trigger_mixin.py
├── security/
│   ├── security.xml
│   ├── ir.model.access.csv
│   └── record_rules.xml
├── views/
│   ├── menu.xml
│   ├── bpm_workflow_views.xml
│   ├── bpm_instance_views.xml
│   ├── bpm_task_views.xml
│   └── bpm_dashboard_views.xml
├── wizard/
│   └── step_config_wizard.py
└── tests/
    ├── __init__.py
    ├── test_workflow.py
    ├── test_execution.py
    └── test_triggers.py
```

---

## 12. Implementation Phases

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 1** | Week 1-2 | Core models, basic orchestrator, condition/stop executors |
| **Phase 2** | Week 3 | Trigger engine, ORM mixin, all trigger types |
| **Phase 3** | Week 4-5 | All action executors (record, email, HTTP) |
| **Phase 4** | Week 6 | Human task system, escalation, activities |
| **Phase 5** | Week 7 | Parallel branches, wait events, delays |
| **Phase 6** | Week 8 | Webhooks, REST API |
| **Phase 7** | Week 9 | Dashboard, monitoring, instance controls |
| **Phase 8** | Week 10 | Polish, testing, documentation |

---

## 13. Testing Strategy

- **Unit Tests**: Individual model methods, executors, field mappings
- **Integration Tests**: Full workflow execution, trigger firing, task completion
- **API Tests**: Webhook validation, REST endpoint responses
- **Performance Tests**: Large batch processing, concurrent instances

---

## 14. Deployment Guide

### Installation

1. Clone module to addons directory
2. Update addons path in configuration
3. Install via Apps menu

### Configuration

1. Assign security groups to users
2. Configure system parameters
3. Enable trigger mixin on target models
4. Verify cron jobs are active

### Monitoring

- Check dashboard for failed instances
- Monitor outbox queue depth
- Review execution logs regularly

---

**End of Design Document**
