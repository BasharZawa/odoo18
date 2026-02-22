# BPM Automation Engine

## What This Is

A full Business Process Management (BPM) engine for Odoo 18 — a standalone module (`bpm_automation`) that lets admins build, activate, and monitor automated workflows through a no-code UI. Workflows fire on record events, schedules, or external triggers, then execute sequences of actions (update fields, send emails, create activities, call HTTP endpoints, run server actions) with conditional branching, parallel paths, and human tasks.

## Core Value

Any business record in Odoo can automatically trigger a multi-step workflow — without writing code.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Module installs cleanly on Odoo 18 with proper security groups and menus
- [ ] Workflow definitions: name, target model, steps, triggers, state (draft/active/disabled)
- [ ] Step types: action, condition (if/else gateway), parallel split/join, human task, wait event, delay, stop
- [ ] Action types: update_record, create_record, delete_record, link_records, send_email, send_message, send_sms, create_activity, server_action, http_request, webhook_call, execute_python
- [ ] Trigger types: on_create, on_write, on_delete, on_field_change, on_condition, scheduled (cron), deadline, webhook, manual, API
- [ ] Outbox-pattern execution queue (reliable async, no lost actions)
- [ ] Orchestrator cron processes outbox items with pessimistic locking
- [ ] Retry logic with exponential backoff for failed steps
- [ ] Parallel branch execution with split/join (all-complete or any-complete)
- [ ] Human task creation with assignee resolution (user/group/field/expression), deadline, escalation
- [ ] Webhook endpoint controller with token auth, HMAC signature, IP allowlist
- [ ] REST API: list workflows, start workflow, get instance status, complete task
- [ ] Monitoring dashboard: running/failed/pending counts, recent instances, failed instances
- [ ] Instance detail view: step timeline, context viewer, control buttons (pause/resume/cancel/retry)
- [ ] Full execution audit log (per-instance, categorized, filterable)
- [ ] Jinja2 + Python expression support in field mappings and conditions
- [ ] Test coverage ≥ 80%, performance: 1000 instances processed in < 5 minutes

### Out of Scope

- Approval workflows — Odoo's native `approval.request` handles this; no duplication
- Integration with existing EPT modules — BPM is standalone; EPT approval chains stay as-is
- Visual drag-and-drop workflow designer — step-based form UI is sufficient for v1
- Multi-tenancy / SaaS features — single Odoo instance target

## Context

- **Platform:** Odoo 18.0 Enterprise, custom_addons path, PostgreSQL (OdooE DB)
- **Existing modules:** 18 custom EPT modules — BPM does NOT replace or depend on them
- **Prior planning:** Detailed architecture docs in `docs/plans/` — outbox pattern, executor hierarchy, and 12-phase roadmap already designed
- **Architecture:** Event-driven async — Trigger Engine → Outbox Queue → Orchestrator → Step Executors → Action Executors
- **Security:** Python code execution needs whitelist/registry guard; Jinja templates need sanitization

## Constraints

- **Tech Stack:** Odoo 18 ORM only — no external message brokers (Celery, Redis); use `ir.cron` for scheduling
- **Compatibility:** Must not break existing EPT modules; standalone dependency tree
- **Performance:** Orchestrator must handle concurrent workers via `FOR UPDATE SKIP LOCKED`
- **Security:** `execute_python` action type requires admin-approved function registry before execution

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Outbox pattern for execution queue | Prevents lost actions on crash; enables retry and idempotency | — Pending |
| Standalone module (no EPT dependency) | Clean separation; EPT modules continue using approval.request | — Pending |
| Exclude approval workflows from BPM | Odoo approval module already handles this well; avoids duplication | — Pending |
| ir.cron as scheduler (no Redis/Celery) | Stays Odoo-native, no external infrastructure dependency | — Pending |
| Jinja2 + safe_eval for expressions | Flexible templating without full Python eval security risks | — Pending |

---
*Last updated: 2026-02-22 after initialization*
