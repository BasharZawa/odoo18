# SEDCO BPM Engine (Odoo 18 EE)
```markdown
# SEDCO BPM Engine for Odoo 18 (EE) — Simple Guide

A visual BPMN editor + a BPMN→JSON compiler + a durable workflow runtime for human tasks, system actions, timers, events, and parallel flows. Version: 18.0.6.0.0

## What you get
- Offline‑first BPMN editor (local file, then CDN fallback)
- One‑click “Save XML” and “Compile to JSON” (no JSON widgets; stored as text)
- Auto‑start on record create via base_automation
- Human tasks with Approve/Reject links in chatter
- Service tasks via whitelisted Python callables (exactly‑once outbox)
- Timers, message events, exclusive gateways, and parallel split/join

## How it works (in 3 steps)
1) Design: Open the “BPMN Diagram” tab, draw your flow, Save XML or Compile to JSON.
2) Compile: The server parses BPMN 2.0 XML and writes a compact JSON DSL into `definition_json`.
3) Run: A cron‑driven orchestrator advances activities; timers/events wait; outbox dispatches effects once.

## Quick start
1) Install module and upgrade assets. For air‑gapped servers, drop `bpmn-modeler.development.js` under:
  `sedco_bpm_engine/static/lib/bpmn-js/`
2) Create a Process Definition. Draw your diagram → Compile to JSON.
3) Bind to a model (e.g., `crm.lead`), enable “Auto‑apply on Create”, set an optional creation domain.
4) Test: Click “Start Test” or create a record that matches your domain. Complete tasks via links.

## Supported BPMN → JSON (MVP)
- startEvent → start(next) : This maps a BPMN start event to the JSON start action, where "next" indicates the subsequent node in the flow.
- endEvent → end : This maps a BPMN end event to the JSON end action, effectively terminating the process.
- userTask → task(label, assignee_id, next, next_approve, next_reject) : 
  This converts a BPMN user task into a JSON task, detailing the task label, the assignee's identifier, the next action on completion, and alternative paths for approval or rejection.
- serviceTask → sys(action, next) :
   This changes a BPMN service task into a JSON system action, specifying the action to execute and indicating the following step.
- exclusiveGateway → if(expression, on_true, on_false) :
   This translates an exclusive gateway into a JSON conditional check with an "if" function, executing different paths based on the evaluated expression.
- parallelGateway (split) → pbranch(branches[], join) :
   This maps a BPMN parallel gateway for splitting flows into a JSON parallel branch directive with an array of branches and a join node to later synchronize the flows.
- parallelGateway (join) → pwait(next) :
   This represents a BPMN parallel gateway for joining flows into a JSON wait action, using "next" to resume the process after synchronization.
- intermediateCatchEvent+timer → wtime(delay_seconds, next) :
   This converts a BPMN timer event into a JSON wait time function, where "delay_seconds" defines the duration before moving to the next node.
- intermediateCatchEvent+message → wevent(event_name, correlation_key, next) :
   This represents a BPMN message event in JSON, using "event_name" and "correlation_key" for identification and routing to the following action.
  ## BPMN Extensions in Process Definitions

  These custom BPMN extensions are used within `<bpmn:extensionElements>` in your BPMN diagrams to enhance standard elements with additional workflow logic. For example:

  - `<sedco:assignment value="1"/>` assigns a specific user ID as the assignee for a user task.
  - `<sedco:approve target="NodeId"/>` and `<sedco:reject target="NodeId"/>` define the subsequent node based on the outcome of a task.
  - `<sedco:action dotted="my_module.actions.notify"/>` triggers a whitelisted system action via a Python callable.
  - `<sedco:timer seconds="300"/>` introduces a delay before the process proceeds.
  - `<sedco:message name="event.name" correlation="requestId"/>` handles message events with a defined name and correlation key.

  These elements are embedded in your BPMN XML to instruct the compiler on how to convert your visual design into the corresponding JSON DSL.  

## Runtime basics
- Orchestrator cron picks ready activities and executes them by type
- Timers cron enqueues expired waits; Outbox cron guarantees exactly‑once side‑effects
- User tasks create `mail.activity` with Approve/Reject links; system tasks go through Outbox

## Bind & Auto‑start
On a definition:
- Set `model_id` (target business model)
- Enable `auto_apply`
- Optionally set `start_on_create_domain` (Python domain string)
The module creates the automation and server action for you.

## Whitelist your callables
Add entries in BPM → Whitelist:
- Name: any
- Dotted path: e.g., `my_module.actions.notify_manager`
- Kind: System Action (or Assignee resolver)
Use the dotted path in a serviceTask via `<sedco:action dotted="..."/>`.

## Minimal health check
In a shell or server action:
```python
self.env['ir.http']._json_call('/bpm/health')
```

## Key menus (backend)
- Process Definitions, Instances, Activities
- Timers, Event Subscriptions, Outbox
- Whitelist (System Actions / Resolvers)

## Public APIs
- Start by key: `POST /bpm/start/<key>` → `{ business_key, ctx }` → `{ ok, proc_id }`
- Push message event: `POST /bpm/event` → `{ event_name, correlation_key, next_node? }`
- Complete task: `GET /bpm/task/complete?act_id=ID&decision=approve|reject`

## Troubleshooting
- Diagram empty: Provide local `bpmn-modeler.development.js` or allow CDN; hard‑refresh with `?debug=assets`.
- Save/Compile does nothing: Browser cache; hard‑refresh; check console.
- No tasks created: Ensure assignee is set and crons are running.
- System action not executed: Add dotted path to Whitelist; check Outbox errors.

## What changed in 18.0.6
- Editor now sends XML via RPC (`action_save_bpmn_xml`, `action_compile_bpmn_from_xml`) to avoid form save races
- Kept offline‑first loading with clear error banner if bpmn‑js can’t load

## Pointers (where things live)
- Manifest: `__manifest__.py` (assets, menus, crons) — version 18.0.6.0.0
- Compiler & binder: `models/process_definition.py`
- Runtime/orchestrator: `models/orchestrator.py`
- Stores: `models/activity_instance.py`, `timer.py`, `event_subscription.py`, `outbox.py`
- HTTP API: `controllers/` (start, event, complete)
- Editor widget: `static/src/js/bpmn_editor.js`

—
Short, practical, and safe by default. Build flows visually, keep code whitelisted, and let the engine run them reliably.
```


bpm.event.subscription(event_name, correlation_key, status)
