# 🧠 Smart Report Builder — Odoo 18 + n8n + Claude AI

> Ask for any report in plain English → Get table + chart instantly

## Architecture

```
User types "sales by salesperson this quarter"
        │
        ▼
┌─ Odoo 18 Module ────────────────────────┐
│  OWL 2 Component  →  Python Controller  │
└──────────────────────┬──────────────────┘
                       │ POST /webhook/smart-report
                       ▼
┌─ n8n (Hetzner) ─────────────────────────┐
│  Webhook → Prepare Context → Claude API │
│  → Parse Response → Respond to Webhook  │
└──────────────────────┬──────────────────┘
                       │ Structured JSON
                       ▼
┌─ Odoo 18 ───────────────────────────────┐
│  Execute read_group() → Return data     │
│  → Render Table + Chart.js              │
└─────────────────────────────────────────┘
```

## Setup Guide (Step by Step)

### Step 1: Get Claude API Key

1. Go to **https://console.anthropic.com**
2. Sign up / log in
3. Go to **Settings → API Keys**
4. Click **Create Key** → name it "smart-report"
5. Copy the key (starts with `sk-ant-...`)
6. Add $5-10 credit (this will last you months for this use case)

### Step 2: Import n8n Workflow

1. Open your n8n instance on Hetzner
2. Go to **Settings → Environment Variables**
3. Add: `CLAUDE_API_KEY` = your key from Step 1
4. Go to **Workflows → Import from File**
5. Import `n8n_workflow.json` (included in this module)
6. Open the workflow → click **Active** toggle (top right)
7. Copy the **Webhook URL** (click the Webhook node → "Production URL")
   - It will look like: `https://your-n8n.hetzner.com/webhook/smart-report`

### Step 3: Install Odoo Module

1. Copy `smart_report_builder` folder to your Odoo addons path
2. Restart Odoo: `sudo systemctl restart odoo`
3. Go to **Apps** → Update Apps List
4. Search "Smart Report" → Install

### Step 4: Configure

1. Go to **Settings** → scroll to **Smart Report Builder**
2. Paste your n8n Webhook URL
3. (Optional) Add a Bearer token for security
4. Click **Save**

### Step 5: Use It!

1. Click **Smart Reports** in the main menu
2. Click **Report Builder**
3. Type: "Total sales by salesperson this quarter"
4. Hit **Generate** ⚡

## Example Queries

| Query | What it does |
|-------|-------------|
| "Sales by salesperson this month" | `sale.order` grouped by `user_id`, measure `amount_total:sum` |
| "Count of open leads by stage" | `crm.lead` grouped by `stage_id`, measure `id:count` |
| "Top 10 customers by invoiced amount" | `account.move` grouped by `partner_id`, limit 10, ordered desc |
| "Monthly revenue trend this year" | `account.move` grouped by `invoice_date:month` |
| "Products with most stock moves" | `stock.move` grouped by `product_id`, measure `product_uom_qty:sum` |
| "Average deal size by sales team" | `crm.lead` grouped by `team_id`, measure `expected_revenue:avg` |

## Extending: Add More Models

Edit `models/smart_report.py` → `get_available_models()` → add your custom models:

```python
target_models = [
    'sale.order',
    'your.custom.model',  # ← add here
    ...
]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "n8n webhook URL not configured" | Go to Settings → Smart Report Builder |
| "Cannot connect to n8n" | Check n8n is running, URL is correct, firewall allows connection |
| "AI response missing field" | Check n8n workflow execution log for Claude's raw response |
| "Model not found" | The queried model isn't installed in your Odoo |
| Chart not rendering | Chart.js loads from CDN — check internet/CSP headers |

## File Structure

```
smart_report_builder/
├── __manifest__.py          # Module definition
├── __init__.py
├── models/
│   ├── smart_report.py      # Saved reports model + schema helper
│   └── res_config_settings.py  # n8n URL configuration
├── controllers/
│   └── main.py              # API endpoints (query, save, load)
├── security/
│   └── ir.model.access.csv  # Access rights
├── views/
│   ├── smart_report_views.xml        # Menus, actions, list/form views
│   └── res_config_settings_views.xml # Settings page
├── static/src/
│   ├── js/smart_report_builder.js    # OWL 2 component
│   ├── css/smart_report_builder.css  # Styles
│   └── xml/smart_report_builder.xml  # OWL template
├── n8n_workflow.json        # Import this into n8n
└── README.md                # This file
```

## Cost Estimate

- **Claude Sonnet API**: ~$0.003 per query (avg 1K input + 200 output tokens)
- **1000 queries/month** = ~$3/month
- **n8n self-hosted**: Free (community edition)

## Next Steps

- [ ] Add Arabic language support for queries
- [ ] Add scheduled reports (n8n cron → email PDF)
- [ ] Add drill-down (click chart segment → detailed records)
- [ ] Add dashboard mode (multiple reports on one screen)
