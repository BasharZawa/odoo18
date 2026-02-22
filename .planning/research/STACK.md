# Technology Stack: BPM Automation Engine (bpm_automation)

**Project:** bpm_automation — Odoo 18 Enterprise BPM workflow engine
**Researched:** 2026-02-22
**Confidence:** HIGH (all findings verified directly from Odoo 18 source code)

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Odoo ORM (models.Model) | 18.0 | Persistent state for all BPM entities | Native transactions, access control, search, views for free. No external persistence needed. |
| ir.cron + ir.cron.trigger | 18.0 | Outbox poll orchestrator and delay/timer steps | Built-in distributed locking via `FOR NO KEY UPDATE SKIP LOCKED`. Odoo 18 adds `_notify_progress()` API for partial-completion signaling. |
| PostgreSQL | 14+ (bundled) | Queue locking, outbox table | `FOR NO KEY UPDATE SKIP LOCKED` is the correct lock level — conflicts with all write locks but not `KEY SHARE` (foreign key locks), preventing FK-reference deadlocks. |
| odoo.tools.safe_eval | 18.0 | Condition expression evaluation | Bytecode-level opcode whitelist. Allows `env`, `record`, `user`, `datetime`, `time`. Already used by ir.actions.server for all code execution. |
| mail.render.mixin + inline_template | 18.0 | Template rendering for send_email step | Three render engines: `inline_template` (safe_eval-based `{{ expr }}`), `qweb` (full XML template), `qweb_view` (external view ref). Use `inline_template` for BPM. |
| mail.template.send_mail() | 18.0 | Sending emails via template | Call `template.send_mail(res_id, force_send=True)` or `send_mail_batch(res_ids)`. Handles localization, attachments, layout. |
| ir.actions.server | 18.0 | Delegating to native action executors | States: `object_write`, `object_create`, `code`, `webhook`, `multi`. Run via `action.with_context(active_id=X, active_model=Y).run()`. Extend by adding `_run_action_<state>` methods. |
| odoo.http.Controller + @route | 18.0 | REST webhook trigger endpoint | Pattern proven in `base_automation`'s `/web/hook/<uuid>` controller. Use `type='json'`, `auth='public'`, `csrf=False` for BPM REST API. |
| base.automation (reference only) | 18.0 | Reference for ORM hook injection pattern | Do NOT inherit — read its `_register_hook()` pattern for how to patch `create`/`write`/`unlink` via `make_create()` closures. |

### Database Layer

| Technology | Purpose | Notes |
|------------|---------|-------|
| `FOR NO KEY UPDATE SKIP LOCKED` | Outbox queue worker exclusion | Exact SQL used by Odoo 18 ir.cron (`_acquire_one_job`). Safe for concurrent workers because it skips locked rows instead of blocking. |
| `FOR NO KEY UPDATE NOWAIT` | Admin UI conflict detection | Used by `ir.cron._try_lock()` — raises `psycopg2.OperationalError` immediately if locked. Use this in BPM admin actions to prevent editing running instances. |
| `ir.cron.trigger` (signal table) | Wake cron on-demand | `cron._trigger(at=datetime)` inserts a row; the cron worker polls this table. Use to wake the orchestrator immediately after outbox insert instead of waiting for the next scheduled tick. |
| `ir_cron_progress` pattern | Partial batch reporting | New in Odoo 18. Call `cron._notify_progress(done=N, remaining=M)` inside the server action so the cron framework knows to reschedule ASAP vs. FULLY_DONE. Adopt this for the outbox orchestrator. |
| `odoo.tools.SQL` class | Composable, injection-safe raw SQL | New in Odoo 18. Replaces ad-hoc `%s` string building. `SQL("SELECT ... WHERE id = %s", record_id)` with nested `SQL.identifier(tablename)`. Prefer over plain `cr.execute()` string concatenation. |
| `cr.postcommit.add(fn)` | After-commit side effects | Used by ir.cron to `pg_notify` cron workers after a transaction commits. Use this in the trigger engine: write outbox row first, then `cr.postcommit.add(wake_orchestrator)` to avoid waking before the row is visible. |
| `cr.precommit.add(fn)` | Before-commit flush hooks | Available but less relevant for BPM; ORM uses it for field recomputation flushing. |

### Expression Evaluation

| Approach | API | Use Case | Confidence |
|----------|-----|----------|------------|
| `safe_eval(expr, {'record': rec, 'env': env, ...})` | `odoo.tools.safe_eval.safe_eval()` | Condition expressions in condition steps; field value expressions in update_record steps | HIGH — verified from ir.actions.server source |
| `render_inline_template(parse_inline_template(txt), vars)` | `odoo.tools.rendering_tools` | Dynamic string interpolation in email subjects, step names, log messages | HIGH — verified from rendering_tools.py |
| `safe_eval(expr, mode="exec")` | same, with `nocopy=True` | Multi-line code blocks (advanced executor) | HIGH — verified from `_run_action_code_multi` |

**Do not use:** Jinja2 directly. Odoo 18 does not use Jinja2 for server-side expression evaluation. `rendering_tools.py` uses the custom `{{ expr }}` inline template syntax backed by `safe_eval`, not `jinja2.SandboxedEnvironment`. The only Jinja2 reference in Odoo 18 tools is a comment in `ir_qweb.py` line 466. Using raw Jinja2 would bypass Odoo's opcode whitelist and create a security gap.

### eval_context Standard Shape

Based on `IrActionsServer._get_eval_context()` (verified from source):

```python
eval_context = {
    # base (from IrActions._get_eval_context)
    'uid': env.uid,
    'user': env.user,
    'time': safe_eval.time,
    'datetime': safe_eval.datetime,
    'dateutil': safe_eval.dateutil,
    'timezone': timezone,
    'float_compare': float_compare,
    'b64encode': base64.b64encode,
    'b64decode': base64.b64decode,
    'Command': Command,
    # extended (from IrActionsServer._get_eval_context)
    'env': env,
    'model': model,
    'record': record,       # single browse record or None
    'records': records,     # multi browse recordset or None
    'UserError': odoo.exceptions.UserError,
    'log': log_fn,
    '_logger': LoggerProxy,
}
```

Use this exact shape for BPM condition and expression evaluation. Extend it with BPM-specific context (`workflow_instance`, `step`, `payload`) but never remove the standard keys.

### ORM Hook Injection Pattern

Based on `base_automation._register_hook()` (verified from source):

```python
# CORRECT pattern for trigger engine — use closures to avoid late-binding bugs
def make_create():
    @api.model_create_multi
    def create(self, vals_list, **kw):
        records = create.origin(self, vals_list, **kw)
        # fire BPM triggers here
        self.env['bpm.trigger.engine']._on_create(self._name, records)
        return records
    return create

# Register in _register_hook():
Model._patch_method('create', make_create())
```

**Critical:** Always wrap patched methods in factory functions (`make_create()`, `make_write()`). Without the factory closure, all patched models share the same function reference, causing the last model's patch to overwrite all previous ones. This is documented in `base_automation.py` line 760.

### HTTP Controller Pattern

Based on `base_automation/controllers/main.py` (verified from source):

```python
from odoo.http import request, route, Controller

class BpmWebhookController(Controller):

    @route(['/bpm/webhook/<string:process_key>'],
           type='json',         # use 'json' not 'http' for REST API
           auth='api_key',      # use api_key auth, not 'public'
           methods=['POST'],
           csrf=False,
           save_session=False)
    def trigger_process(self, process_key, **kwargs):
        payload = request.get_json_data()
        # ...
        return {'status': 'ok', 'instance_id': instance.id}
```

Difference from base_automation: Use `type='json'` (not `'http'`) so Odoo handles JSON serialization. Use `auth='api_key'` so the endpoint requires an Odoo API key header, not a public-facing unauthenticated endpoint.

### Supporting Libraries (Already Bundled in Odoo 18)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `psycopg2` | 2.9.x | Raw SQL execution, locking | Already Odoo's DB driver. Import `psycopg2.extensions.TransactionRollbackError` for serialization error handling in queue workers. |
| `requests` | bundled | HTTP executor (http_request step) | Used by ir.actions.server's `_run_action_webhook`. Copy the 1s timeout pattern with `raise_for_status()`. |
| `pytz` | bundled | Timezone-aware delay calculation | Used in ir.cron `_reschedule_later`. Required for BPM delay steps to handle DST correctly. |
| `dateutil.relativedelta` | bundled | Human-friendly delay expressions | "3 days", "1 month" delay steps — use `relativedelta` not `timedelta`. |
| `markupsafe.Markup` | bundled | Safe HTML in templates | Wrap HTML template outputs in `Markup()` to prevent double-escaping when passed to QWeb. |

### No External Dependencies Needed

| What You Might Consider | Why Not |
|------------------------|---------|
| Celery + Redis | Introduces external infrastructure Odoo deployments don't have. ir.cron + SKIP LOCKED is the Odoo-native equivalent and is already present. |
| Jinja2 SandboxedEnvironment | Not used by Odoo 18 for server-side eval. `safe_eval` with opcode whitelist is more restrictive and already deployed. |
| SpiffWorkflow / BPMN engine libs | These assume they own the process state. You need Odoo ORM ownership for access control, views, and auditability. Build your own state machine on top of ORM. |
| asyncio / async workers | Odoo 18 workers are synchronous WSGI. No async support. The ir.cron pattern (poll + SKIP LOCKED) achieves concurrency without async. |
| Django Q / Huey | Same as Celery objection — external infra. Also incompatible with Odoo's connection pool. |

---

## Odoo 18 Specific — Differences from Odoo 16/17

| Area | Odoo 16/17 | Odoo 18 | Impact on BPM |
|------|-----------|---------|--------------|
| Cron locking | `FOR UPDATE SKIP LOCKED` | `FOR NO KEY UPDATE SKIP LOCKED` | Use `NO KEY UPDATE` — weaker lock that doesn't conflict with FK `KEY SHARE`. Copy exactly from ir_cron.py line 295. |
| Cron progress | No progress API | `ir.cron.progress` model + `_notify_progress(done, remaining)` | Enables partial batch processing. Critical for outbox orchestrator to signal "more items pending" without running indefinitely. |
| Cron partial done | Not supported | `CompletionStatus.PARTIALLY_DONE` → `_reschedule_asap()` | Orchestrator can process 10 items, report remaining, and get rescheduled immediately by the framework. Use `MAX_BATCH_PER_CRON_JOB = 10` as a guide. |
| SQL building | String formatting | `odoo.tools.SQL` class | Use `SQL("...", param)` not `"... %s" % param` for all raw queries. Already used in ir_cron.py's `_notifydb`. |
| ir.actions.server webhook state | Not present | `state='webhook'` + `webhook_url` field | Odoo 18 natively supports webhook actions. BPM's `http_request` step can delegate to this or implement independently. |
| `_run_action_*` naming | `run_action_*` (public, deprecated) | `_run_action_*` (private) | In Odoo 18, `_get_runner()` warns if `run_action_` prefix is found. Use `_run_action_<type>` with underscore prefix. |
| cron `_trigger()` | Existed in 16 | Unchanged API, still present | `cron._trigger(at=datetime)` to wake orchestrator. Use `postcommit` to call after transaction. |

---

## Key API Signatures (Verified from Source)

```python
# 1. FOR NO KEY UPDATE SKIP LOCKED — outbox worker query
cr.execute("""
    SELECT id FROM bpm_outbox
    WHERE state = 'pending'
      AND scheduled_at <= (now() at time zone 'UTC')
    ORDER BY priority, id
    LIMIT %s
    FOR NO KEY UPDATE SKIP LOCKED
""", [batch_size])

# 2. Trigger cron immediately after outbox insert
cron = self.env.ref('bpm_automation.cron_orchestrator')
self._cr.postcommit.add(lambda: cron._trigger())

# 3. Cron progress reporting (Odoo 18 only)
cron._notify_progress(done=processed, remaining=remaining_count)
# If remaining > 0, framework calls _reschedule_asap() automatically

# 4. safe_eval for condition expressions
from odoo.tools.safe_eval import safe_eval
result = safe_eval(condition_expr, {
    'record': self,
    'env': self.env,
    'user': self.env.user,
    'datetime': safe_eval_module.datetime,
    'time': safe_eval_module.time,
})

# 5. Inline template rendering
from odoo.tools.rendering_tools import parse_inline_template, render_inline_template
instructions = parse_inline_template("Hello {{ record.partner_id.name }}!")
rendered = render_inline_template(instructions, {'record': record, 'user': env.user})

# 6. mail.template send_mail
template = self.env.ref('bpm_automation.email_template_task_assigned')
template.send_mail(record.id, force_send=True, email_values={'email_to': 'x@y.com'})
# Or batch:
template.send_mail_batch(record_ids)

# 7. ir.actions.server delegation
action = self.env['ir.actions.server'].browse(action_id)
action.with_context(
    active_id=record.id,
    active_ids=[record.id],
    active_model=record._name,
).run()

# 8. ORM postcommit hook (safe for notifications)
self._cr.postcommit.add(self._send_external_notification)

# 9. SQL class for composable queries
from odoo.tools import SQL
cr.execute(SQL(
    "UPDATE %s SET state = %s WHERE id = %s",
    SQL.identifier('bpm_outbox'),
    'done',
    outbox_id,
))
```

---

## Sources

All findings verified directly from Odoo 18 Enterprise source code at `/home/bashar/odoo18/odoo/`:

- `addons/base/models/ir_cron.py` — FOR NO KEY UPDATE SKIP LOCKED (line 295), `_notify_progress`, `ir.cron.progress`, `_trigger()`, `postcommit`
- `addons/base/models/ir_actions.py` — `_get_eval_context()` (lines 134, 900), `_run_action_code_multi` (line 826), `_run_action_webhook` (line 850), `state` Selection choices (line 542)
- `tools/safe_eval.py` — `safe_eval()` signature (line 347), allowed builtins, opcode whitelist
- `tools/rendering_tools.py` — `parse_inline_template()`, `render_inline_template()`, `template_env_globals`
- `tools/sql.py` — `SQL` class (line 48)
- `sql_db.py` — `postcommit`, `precommit` cursor callbacks (lines 147-165)
- `ent_addons/base_automation/models/base_automation.py` — `_register_hook()` closure pattern (line 752), trigger types
- `ent_addons/base_automation/controllers/main.py` — webhook controller pattern
- `ent_addons/mail/models/mail_render_mixin.py` — `_render_eval_context()` (line 255), render engines
- `ent_addons/mail/models/mail_template.py` — `send_mail()` (line 596), `send_mail_batch()` (line 621)
