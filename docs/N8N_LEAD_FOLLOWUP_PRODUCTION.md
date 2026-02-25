# Lead Follow-up Automation — Production Setup Guide

Workflow: Odoo CRM Lead Created → n8n → 2/5/9-day chatter reminders

---

## Architecture

```
Odoo (ir.actions.server, state='webhook')
  └─ POST http://<n8n-host>/webhook/lead-followup
       └─ n8n workflow (ID: loFxDXzaX7kPC1ma)
            ├─ Wait 2 days → check stage → 2-day reminder (chatter)
            ├─ Wait 3 more days → check stage → 5-day reminder (chatter)
            └─ Wait 4 more days → check stage → 9-day escalation (chatter)
```

**Payload sent by Odoo to n8n:**
```json
{
  "id": 42,
  "model": "crm.lead",
  "name": "Lead Name",
  "stage_id": 1,
  "user_id": 3
}
```

---

## Current Dev Values (change for production)

| Setting | Dev Value | Production |
|---------|-----------|------------|
| Odoo → n8n URL | `http://localhost:5678/webhook/lead-followup` | `https://n8n.yourcompany.com/webhook/lead-followup` |
| n8n → Odoo URL | `http://host.docker.internal:8069` | `http://<odoo-server-ip>:8069` |
| Odoo DB | `OdooE` | your production DB name |
| Odoo UID | `2` (admin) | UID of dedicated API user |
| Odoo password | `admin` | strong password |

---

## Step 1 — Update Odoo Webhook URL

Run via `odoo-bin shell` on the production server:

```python
sa = env['ir.actions.server'].browse(715)
sa.write({'webhook_url': 'https://n8n.yourcompany.com/webhook/lead-followup'})
env.cr.commit()
print("Done")
```

---

## Step 2 — Create a Dedicated Odoo API User

```python
user = env['res.users'].create({
    'name': 'n8n Integration',
    'login': 'n8n_api',
    'password': 'CHANGE_ME_STRONG_PASSWORD',
    'groups_id': [(6, 0, [
        env.ref('base.group_user').id,
        env.ref('mail.group_mail_manager').id,
    ])]
})
env.cr.commit()
print(f"API user UID: {user.id}")
```

Note the UID — you will use it in Step 3.

---

## Step 3 — Update n8n Code Nodes

In the n8n workflow, all **Read Stage** nodes and **Build Reminder** nodes contain hardcoded values. Update them via the n8n UI or REST API.

### Read Stage nodes (3 nodes: Read Stage 1, 2, 3)

Replace:
```javascript
args: ['OdooE', 2, 'admin', 'crm.lead', 'read', ...]
```
With:
```javascript
args: ['<PROD_DB>', <API_USER_UID>, '<API_USER_PASSWORD>', 'crm.lead', 'read', ...]
```

Also replace the Odoo URL in the **Get Lead** HTTP nodes:
- Old: `http://host.docker.internal:8069/jsonrpc`
- New: `http://<odoo-server-ip>:8069/jsonrpc`

### Build Reminder nodes (3 nodes: Build 2-Day, 5-Day, 9-Day)

Same replacements:
```javascript
args: ['<PROD_DB>', <API_USER_UID>, '<API_USER_PASSWORD>', 'mail.message', 'create', ...]
```

And update the **Post Reminder** HTTP nodes URL to the production Odoo address.

---

## Step 4 — Verify n8n Workflow is Active

```bash
curl -s http://<n8n-host>:5678/api/v1/workflows/loFxDXzaX7kPC1ma \
  -H "X-N8N-API-KEY: <your-api-key>" | python3 -m json.tool | grep '"active"'
```

Expected: `"active": true`

If not active:
```bash
curl -s -X POST http://<n8n-host>:5678/api/v1/workflows/loFxDXzaX7kPC1ma/activate \
  -H "X-N8N-API-KEY: <your-api-key>"
```

---

## Step 5 — Test End-to-End

1. Create a test lead in Odoo CRM
2. Check n8n event log to confirm execution started:
   ```bash
   docker exec n8n tail -10 /home/node/.n8n/n8nEventLog.log
   ```
   You should see `n8n.workflow.started` and `n8n.node.started` for `Wait 2 Days`
3. For quick verification, temporarily set wait times to 1 minute (restore after test)

---

## Server Restart Behavior

| Scenario | Behavior |
|----------|----------|
| Odoo restart | `base_automation` hooks re-register **automatically** — no action needed |
| n8n restart | Waiting executions resume automatically from saved state |
| n8n down when lead created | Webhook call is silently dropped (1-second timeout). Lead gets no follow-up. |

---

## Step 6 — Fallback Safety Net (ir.cron)

The Odoo webhook has a 1-second timeout. If n8n is down when a lead is created, the follow-up chain never starts. This cron runs daily and posts an alert to the lead chatter for any lead that has had **no activity for 10+ days**, catching anything n8n missed.

### What it does

- Runs every day at 08:00
- Finds leads with `create_date` AND `write_date` both older than 10 days
- Posts a chatter message on each stalled lead
- Skips leads that already received a safety net alert in the last 24 hours (no duplicate spam)

### Create via odoo-bin shell

```python
# Save as /tmp/create_safety_net_cron.py and pipe to odoo-bin shell
cron_code = """
ten_days_ago = datetime.now() - dateutil.relativedelta.relativedelta(days=10)
one_day_ago  = datetime.now() - dateutil.relativedelta.relativedelta(days=1)

stalled_leads = env['crm.lead'].search([
    ('active',       '=', True),
    ('type',         '=', 'opportunity'),
    ('create_date',  '<', ten_days_ago),
    ('write_date',   '<', ten_days_ago),
])

for lead in stalled_leads:
    already_alerted = env['mail.message'].search_count([
        ('model',  '=', 'crm.lead'),
        ('res_id', '=', lead.id),
        ('body',   'ilike', 'SAFETY NET'),
        ('date',   '>',  one_day_ago),
    ])
    if already_alerted:
        continue

    env['mail.message'].create({
        'body': (
            '<p>🛡️ <strong>[SAFETY NET] Lead Stalled – Manual Review Required</strong></p>'
            '<p>This lead has had no activity for over <strong>10 days</strong>. '
            'The automated n8n follow-up workflow may not have fired. '
            'Please review and take action.</p>'
        ),
        'model':       'crm.lead',
        'res_id':      lead.id,
        'message_type': 'comment',
        'subtype_id':  1,
    })
"""

model_id = env['ir.model'].search([('model', '=', 'crm.lead')], limit=1).id

cron = env['ir.cron'].create({
    'name':            'CRM: Safety Net – Flag Stalled Leads (n8n Fallback)',
    'model_id':        model_id,
    'state':           'code',
    'code':            cron_code,
    'interval_number': 1,
    'interval_type':   'days',
    'numbercall':      -1,
    'active':          True,
    'nextcall':        '2025-01-01 08:00:00',  # set to tomorrow 08:00 in production
})
env.cr.commit()
print(f"Cron created: ID={cron.id}")
```

Run it:
```bash
source venv/bin/activate
python3 odoo-bin shell -d <YOUR_DB> \
  --db_host=localhost --db_port=5432 \
  --db_user=<DB_USER> --db_password="<DB_PASS>" \
  --no-http < /tmp/create_safety_net_cron.py
```

### Create via Odoo UI (alternative)

**Settings → Technical → Automation → Scheduled Actions → New**

| Field | Value |
|-------|-------|
| Name | `CRM: Safety Net – Flag Stalled Leads (n8n Fallback)` |
| Model | `Lead/Opportunity (crm.lead)` |
| Execute Every | `1 Day` |
| Next Execution | tomorrow at 08:00 |
| Action | Execute Python Code |

Paste the Python code from `cron_code` above into the **Code** field.

### Verify it's scheduled

```python
# In odoo-bin shell
cron = env['ir.cron'].search([('name', 'ilike', 'Safety Net')])
print(f"ID={cron.id}  active={cron.active}  nextcall={cron.nextcall}  interval={cron.interval_number} {cron.interval_type}")
```

### Trigger manually to test

```python
# Run it now without waiting for the schedule
cron = env['ir.cron'].browse(<CRON_ID>)
cron.method_direct_trigger()
```

### How it interacts with n8n

| Scenario | n8n | Safety Net Cron |
|----------|-----|-----------------|
| n8n working, lead progresses | Posts reminders, stops | Does nothing (write_date recent) |
| n8n working, lead stalls | Posts reminders at day 2/5/9 | May also fire at day 10+ |
| n8n down at lead creation | Silent, no follow-up | **Fires at day 10** — the backstop |
| n8n down, resumes later | Missed executions not recovered | **Cron is the only alert** |

> **Note:** The cron posts a generic "stalled" alert — it does not replay the 2/5/9-day
> schedule. It is purely a visibility backstop. If n8n is restored, new leads will follow
> the normal schedule automatically.

---

## Error Handling (Recommended for Production)

### n8n: Add error workflow

In the workflow settings, set `errorWorkflow` to a workflow that sends an alert (Slack, email, etc.) when the follow-up chain fails mid-execution (e.g., Odoo API call fails after the wait).

### Summary: two-layer safety

| Layer | What it catches |
|-------|----------------|
| n8n workflow | Normal case — per-lead reminders at day 2, 5, 9 |
| `ir.cron` safety net | n8n was down at lead creation, or workflow crashed silently |

---

## Odoo Records Reference

| Record | ID | Description |
|--------|----|-------------|
| `ir.actions.server` | 715 | Webhook server action |
| `base.automation` | 1 | Automation rule (trigger: on_create, model: crm.lead) |
| `mail.message.subtype` | 1 | "Discussions" subtype (used for chatter comments) |

## n8n Records Reference

| Record | Value |
|--------|-------|
| Workflow ID | `loFxDXzaX7kPC1ma` |
| Webhook path | `lead-followup` |
| Wait times | 2 days → 3 days → 4 days (cumulative: day 2, 5, 9) |
