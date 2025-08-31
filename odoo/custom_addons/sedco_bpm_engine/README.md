# SEDCO BPM Engine (Odoo 18 EE)
- Offline-first BPMN editor (local file then CDN)
- JSON widgets avoided (render as text)
- <chatter/> used instead of legacy mail_thread
- Depends on base_automation

Health check:
```python
self.env['ir.http']._json_call('/bpm/health')
```
This is a complete overview of the BPM engine you now have (v18.0.6). It combines a visual BPMN modeler, a BPMN→JSON compiler, and a durable workflow runtime (cron-driven orchestrator, timers, events, human tasks, exactly-once outbox).
Use this document to onboard a developer to continue the work.

1) What the system does
At a glance

Design-time (BPMN in the browser):

Use the BPMN Diagram tab to draw flows with bpmn-js (offline-first).

Click Save XML or Compile to JSON.

The editor calls server RPC with the XML payload to store/compile it.

Compile-time (BPMN → internal JSON DSL):

The compiler reads BPMN 2.0 XML and emits a compact JSON definition (definition_json) that the engine executes.

Supported mapping (MVP): Start/End, UserTask, ServiceTask, ExclusiveGateway (IF), Parallel split/join, Timer catch, Message catch.

Run-time (engine executes instances):

A Process Definition can be bound to a business model (e.g., crm.lead) and set to auto-start on new records via base.automation.

“Start Test” creates a process instance manually for testing.

A cron orchestrator advances ready activities:

creates mail.activity to assign UserTask with Approve/Reject links,

invokes whitelisted System Actions,

forks and joins via Parallel,

waits on Timers and Events.

An Outbox ensures exactly-once dispatch of email/webhook/system effects.

2) Directory layout & responsibilities
Path	Purpose	Highlights / Key Methods
__manifest__.py	Module metadata	Declares assets, menus, views, crons. Version 18.0.6.0.0.
__init__.py	Module loader	Imports models and controllers.
security/ir.model.access.csv	Basic ACLs	Grants users access to definitions, instances, activities, etc.
data/ir_cron.xml	Scheduled jobs	3 crons: orchestrator tick, outbox dispatcher, timers.
views/*	Backend UI	Definitions, Instances, Activities, Outbox, Registry menus & forms.
static/src/js/bpmn_editor.js	BPMN editor (widget)	Offline-first loader (local → CDN), two RPCs: action_save_bpmn_xml(xml), action_compile_bpmn_from_xml(xml). Shows banner if loading fails.
static/src/js/bpm_registry.js	Asset stub	Placeholder for future frontend registry needs.
static/lib/bpmn-js/README.txt	Offline note	Where to drop bpmn-modeler.development.js for air-gapped installs.
controllers/api.py	HTTP/JSON API	/bpm/start/<key> (start by key), /bpm/event (signal message events), /bpm/task/complete (approve/reject).
models/process_definition.py	Definition model & compiler	Fields: bpmn_xml, definition_json, bind settings. Methods: action_compile_bpmn, action_save_bpmn_xml, action_compile_bpmn_from_xml, action_start_for_record, auto-apply binder.
models/process_instance.py	Process instance	Tracks status, context (ctx_json), chatter.
models/activity_instance.py	Activity instance	One row per node per process; status, assignee, timestamps, node data.
models/event_subscription.py	Wait-event storage	Message event waits with correlation key.
models/timer.py	Wait-time storage	Scheduled due times to resume flows.
models/outbox.py	Exactly-once effects	Email/Webhook/SystemAction with dedup_key, dispatcher.
models/registry.py	Whitelist registry	Only registered dotted paths can be executed as System Actions / resolvers.
models/orchestrator.py	Engine runtime	Main state machine: executes nodes, enqueues next, handles joins, creates tasks, fires actions, consumes timers/events.
demo_actions.py	Sample callable	sedco_bpm_engine.demo_actions.ok(env, ctx) for quick tests.
3) Data model (core fields)
bpm.process.definition

name, key, version, is_active

bpmn_xml (Text): raw BPMN 2.0 XML

definition_json (Text): compiled JSON DSL

Binding: model_id (business model), auto_apply (bool), start_on_create_domain (domain string)

bpm.process.instance

definition_id (M2O), business_key (Char)

status: running|done|failed

ctx_json (JSON): process context (e.g., {model, res_id, proc_id, ...})

One2many activity_ids

bpm.activity.instance

proc_id, node_id, type

status: ready|waiting|done|failed

assignee_id, started_at, ended_at

data (JSON): node-specific payload (e.g., next, on_true, delay_seconds)

Wait stores & outbox

bpm.event.subscription(event_name, correlation_key, status)

bpm.timer(due_at, payload, status)

bpm.outbox(kind, dedup_key, payload, status, last_error)

Whitelist

bpm.registry(name, dotted_path, kind) — kinds: system_action, assignee

4) Design-time: the BPMN editor (frontend)

Widget path: static/src/js/bpmn_editor.js.

Loading strategy: try local static/lib/bpmn-js/bpmn-modeler.development.js, then fallback to CDN unpkg.com. Shows an in-page warning banner if both fail (useful for air-gapped servers).

Buttons:

Save XML → RPC action_save_bpmn_xml(xml_content) (persists XML).

Compile to JSON → RPC action_compile_bpmn_from_xml(xml_content) (saves and compiles).

No dependency on unsaved Odoo form state (fixes “xml_content required” class of issues).

5) Compile-time: BPMN → JSON mapping (MVP)

The compiler builds an array of nodes with minimal data the runtime needs.

Supported BPMN elements → JSON nodes
BPMN	JSON type	Key fields in data
startEvent	start	next
endEvent	end	—
userTask	task	label, assignee_id, next, next_approve, next_reject (approve/reject come from BPMN extensions)
serviceTask	sys	action, next (action is a whitelisted dotted path)
exclusiveGateway	if	expression, on_true, on_false (first flow with condition is taken as on_true; second is on_false)
parallelGateway (fan-out)	pbranch	branches[], join, next
parallelGateway (multi-incoming)	pwait	next
intermediateCatchEvent + timerEventDefinition	wtime	delay_seconds, next
intermediateCatchEvent + messageEventDefinition	wevent	event_name, correlation_key, next
BPMN Extensions (XML)

Add inside <bpmn:extensionElements>:

<!-- userTask assignment -->
<sedco:assignment value="1"/>            <!-- assignee user_id -->

<!-- userTask routing -->
<sedco:approve target="NodeOnApprove"/>
<sedco:reject  target="NodeOnReject"/>

<!-- serviceTask action -->
<sedco:action dotted="your_module.your_callable"/>

<!-- timer -->
<sedco:timer seconds="300"/>

<!-- message -->
<sedco:message name="client.approved" correlation="requestId"/>

JSON DSL (shape)
{
  "nodes": [
    {"id":"StartEvent_1","type":"start","next":"Task_1"},
    {"id":"Task_1","type":"task","label":"Manager Approval","assignee_id":7,"next":"EndEvent_1","next_approve":"EndEvent_1","next_reject":"Gateway_1"},
    {"id":"Gateway_1","type":"if","expression":"ctx.get('score',0) >= 80","on_true":"EndEvent_1","on_false":"ServiceTask_1"},
    {"id":"ServiceTask_1","type":"sys","action":"your_module.do_something","next":"EndEvent_1"},
    {"id":"EndEvent_1","type":"end"}
  ]
}

6) Run-time: engine orchestration
How an instance starts

Manual: Definition form → Start Test (creates bpm.process.instance, enqueues start).

Auto-apply: On the definition, set:

model_id (e.g., crm.lead),

auto_apply = True,

optional start_on_create_domain (e.g., [('type','=','opportunity')]).

When active, an Automated Action is created to start a process on record creation that matches the domain.

Cron workers

Orchestrator Tick: picks bpm.activity.instance with status='ready' and executes per type.

Timers: promotes due bpm.timer rows (status scheduled and due_at <= now) and enqueues their next.

Outbox: dispatches pending effects (email/webhook/system) exactly once.

Activity execution semantics (simplified)

start: mark done → enqueue next.

if: evaluate expression with safe_eval (ctx available) → enqueue on_true or on_false.

task (UserTask):

Creates an Odoo To-Do activity (mail.activity) with Approve/Reject links (controller route).

Sets activity instance to waiting.

When a user clicks Approve/Reject → controller:

marks done and enqueues next_approve / next_reject (fallback: next).

sys (ServiceTask):

Adds an Outbox record with kind='sys' and {action, ctx}, deduped by (proc_id, node_id, action).

Marks done → enqueue next. Dispatcher later calls the whitelisted callable.

pbranch (Parallel split):

Marks done, enqueues each branch, and allocates/initializes matching pwait with a remaining counter.

pwait (Parallel join):

Each completing branch decrements remaining. When zero → mark done → enqueue next.

wtime (Timer wait):

Schedules a bpm.timer(due_at) and sets waiting. Timer cron enqueues next when due.

wevent (Message wait):

Creates bpm.event.subscription with event_name + correlation_key, sets waiting.

External code can hit /bpm/event to resume (see APIs).

end: mark process instance done.

7) Public APIs (for integration)
7.1 Start process by key
POST /bpm/start/<key>
Content-Type: application/json
{ "business_key": "SO123", "ctx": { "amount": 1200 } }


Response

{ "ok": true, "proc_id": 42 }

7.2 Push a message event (resume wevent)
POST /bpm/event
Content-Type: application/json
{
  "event_name": "client.approved",
  "correlation_key": "REQ-9af2",
  "next_node": "AfterEventNodeId"   // optional; else the compiler's 'next'
}


Response: { "ok": true, "matched": 1 }

7.3 Complete a user task (from link)
GET /bpm/task/complete?act_id=123&decision=approve|reject


Redirects back to the instance form.

8) Whitelist: System Actions & Resolvers

Only functions registered in BPM → Whitelist can be invoked.

Record example:

Name: “OK”

Dotted path: sedco_bpm_engine.demo_actions.ok

Kind: System Action

Implementing your own action

# my_module/actions.py
def notify_manager(env, ctx):
    # ctx holds proc_id, model, res_id, and any context you set earlier
    lead = env['crm.lead'].browse(ctx.get('res_id'))
    if lead:
        lead.message_post(body="Manager notified.")
    return True


Add to whitelist with dotted path my_module.actions.notify_manager, then reference in BPMN:

<sedco:action dotted="my_module.actions.notify_manager"/>

9) Developer workflow (how to continue)

Install / Upgrade

Use 18.0.6 zip you have.

For air-gapped servers, drop bpmn-modeler.development.js under
sedco_bpm_engine/static/lib/bpmn-js/ and upgrade the module.

Design flows

Draw in BPMN Diagram → Compile to JSON → validate Definition (JSON).

Bind to a business model

Set model_id, enable auto_apply, set creation domain if needed.

Test end-to-end

Click Start Test, or create a record that matches your domain.

Complete tasks via Approve/Reject links.

Watch Instances and Outbox.

Add system actions

Write callable → register in Whitelist → reference from BPMN.

Production hardening

Tune cron intervals if throughput is high.

Add monitoring on bpm.outbox(status='error').

10) Extending the system (roadmap hooks)
A) Countersign / OR-sign / n-of-m approvals

Compiler: add <sedco:approval mode="all|any|n_of_m" n="2"/> to userTask.

Runtime: represent one logical task node with multiple assignee sub-tasks; complete when the rule is satisfied; cancel remaining.

B) Boundary timers / escalations

BPMN: boundaryTimerEvent on userTask.

Runtime: on first enter, schedule SLA timer; if task not done by due, auto-route to escalation node, reassign, or send email via Outbox.

C) Sub-process / CallActivity

Compiler: translate CallActivity into a child bpm.process.instance (parent_context), wait for completion.

D) Dynamic assignee resolvers

BPMN: <sedco:assignment value="resolver:my_module.resolvers.pick_manager"/>

Runtime: detect resolver: prefix, call whitelisted resolver to return user_id.

E) Live token overlay on diagram

UI: subscribe to Odoo bus; render “current nodes” highlighted in the diagram canvas.

11) Security & safety

safe_eval only on the IF expression with controlled globals; if in doubt, replace with whitelisted resolvers.

Whitelist registry blocks arbitrary code execution for System Actions.

Approver links are behind auth='user'; Odoo’s usual access rules apply.

Outbox dedup prevents duplicate side-effects (idempotence).

12) Troubleshooting
Symptom	Likely cause	Fix
BPMN Diagram tab is empty	bpmn-js not loaded (CSP/No Internet)	Put local file under static/lib/bpmn-js/… or allow unpkg.com, then ?debug=assets and hard refresh.
Clicking Save XML returns xml_content required	Old build using unsaved field	You’re now on 18.0.5 which sends XML via RPC; ensure upgraded assets loaded.
Compile to JSON toast does not show	JS assets cached	Open with ?debug=assets and hard refresh; check browser console.
Tasks not created	No userTask assignee / cron stopped	Ensure cron is running; add <sedco:assignment value="user_id"/>.
System Action never runs	Not whitelisted	Add dotted path to Whitelist; check Outbox for errors.
13) Version notes

18.0.3 — Added BPMN editor, auto-apply (model binding), Approve/Reject links.

18.0.4 — Offline-first editor (local → CDN) + visible error banner.

18.0.6 — Editor sends XML via RPC (action_save_bpmn_xml, action_compile_bpmn_from_xml) to avoid field-saving race; keeps offline-first loading.

14) Example end-to-end recipe

Whitelist sedco_bpm_engine.demo_actions.ok (System Action).

Definition → draw:

Start → IF (ctx.get('amount',0) > 1000)

True → UserTask “Manager Approval”

<sedco:assignment value="1"/>

<sedco:approve target="SysOK"/>

<sedco:reject target="EndEvent_1"/>

False → SysOK

SysOK (ServiceTask) → <sedco:action dotted="sedco_bpm_engine.demo_actions.ok"/> → End

Compile to JSON.

Bind to sale.order, auto_apply=✓, domain [('amount_total','>',0)].

Create a sale order → instance starts → if amount > 1000 → assignee sees Approve/Reject buttons.

15) What to build next (suggested plan)

n-of-m approvals (countersign)

Boundary timers and escalation policies

Assignee resolvers (by group / domain function)

Sub-process support

Live token overlay on diagram

