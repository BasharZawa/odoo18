# Connect Odoo MCP Server to Claude AI

This guide shows how to connect your Odoo MCP server to Claude AI interfaces.

## Available Claude Interfaces

Your MCP server works with any Claude AI interface:
1. **Claude Desktop** (Local, Private, FREE)
2. **Claude Web App** (claude.ai - Requires public endpoint)
3. **Claude Code CLI** (Already working in this terminal!)

---

## Quick Comparison

| Method | Setup | Access | Privacy | Cost | Status |
|--------|-------|--------|---------|------|--------|
| **Claude Desktop** | Easy | Local app | Full privacy | Free | ✅ Configured |
| **Claude Code CLI** | ✅ Done | Terminal/IDE | Full privacy | Free | ✅ Working |
| **Web App (ngrok)** | Medium | Browser | Tunneled | Free | Available |
| **Web App (cloud)** | Hard | Browser | Cloud-hosted | $5-20/mo | Available |

---

## Prerequisites for All Methods

### 1. Create Environment Variables File

Create `.env` file in `/home/bashar/odoo18/`:

```bash
ODOO_URL=http://localhost:8069
ODOO_DB=your_database_name
ODOO_USER=admin
ODOO_PASSWORD=your_password
```

### 2. Fix Wrapper Script Path

Update `/home/bashar/odoo18/mcp_wrapper.sh`:

```bash
#!/bin/bash
cd /home/bashar/odoo18
source venv/bin/activate
python odoo_mcp_server.py "$@"
```

Make it executable:
```bash
chmod +x /home/bashar/odoo18/mcp_wrapper.sh
```

---

## Method 1: Claude Desktop (Recommended)

### Step 1: Download Claude Desktop
- **FREE Download:** https://claude.ai/download
- Available for Windows, Mac, Linux

### Step 2: Create Config File

**Linux:** `~/.config/Claude/claude_desktop_config.json`
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "odoo18": {
      "command": "/home/bashar/odoo18/mcp_wrapper.sh",
      "args": ["stdio"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "your_database_name",
        "ODOO_USER": "admin",
        "ODOO_PASSWORD": "your_password"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop

1. Close Claude Desktop completely
2. Reopen the application
3. MCP server connects automatically

### Step 4: Test It!

Ask Claude Desktop:
- "Search for leads in Odoo with probability over 80%"
- "Show me recent sales orders"
- "Create a new customer named 'AI Test Customer'"

---

## Method 2: Claude Web App (claude.ai)

The web app requires a **publicly accessible** endpoint. Choose one option:

### Option 2A: Use ngrok (Quick Test)

**Step 1:** Create HTTP server wrapper `odoo_mcp_http.py`:

```python
#!/usr/bin/env python3
from odoo_mcp_server import mcp
import uvicorn

if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())

    # Run MCP over HTTP/SSE
    uvicorn.run(
        mcp.get_asgi_app(),
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
```

**Step 2:** Install dependencies:
```bash
source venv/bin/activate
pip install uvicorn
```

**Step 3:** Install and configure ngrok:
```bash
# Install
sudo snap install ngrok

# Get auth token from: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_TOKEN_HERE

# Start MCP server
python odoo_mcp_http.py &

# Create public tunnel
ngrok http 8000
```

**Step 4:** Copy ngrok URL (e.g., `https://abc123.ngrok-free.app`)

**Step 5:** Configure in Claude web app:
1. Go to https://claude.ai
2. Click profile → Settings
3. Go to Developer → MCP Servers
4. Click "Add Server":
   - **Name:** Odoo 18
   - **URL:** Your ngrok URL
   - **Type:** SSE/HTTP

### Option 2B: Cloud Deployment (Production)

Deploy to cloud platform:

**Railway** (Easiest):
1. Create account: https://railway.app
2. Connect GitHub repo
3. Set environment variables
4. Deploy - you get a public URL

**Fly.io** (Free tier):
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly launch
fly secrets set ODOO_URL=... ODOO_DB=... ODOO_USER=... ODOO_PASSWORD=...
fly deploy
```

Then use the public URL in claude.ai settings.

---

## Method 3: Claude Code CLI ✅ (Already Working!)

**You're using this right now!** Claude Code CLI has direct MCP integration.

Test it in this conversation:
- "Search for CRM leads with high probability"
- "Show me today's sales orders"
- "Find customer by email"

---

## MCP Server Architecture

```
┌─────────────────────────────────────┐
│       Your Odoo Database            │
│    (PostgreSQL - Business Data)     │
└──────────────┬──────────────────────┘
               │
               │ Odoo JSON-RPC API
               │
┌──────────────▼──────────────────────┐
│      MCP Server (Core Engine)       │
│     odoo_mcp_server.py (29KB)      │
│                                     │
│  • 50+ Tools (search, create, etc) │
│  • Standardized MCP Protocol       │
│  • Authentication & Security       │
└──────────────┬──────────────────────┘
               │
               │ MCP Protocol (stdio/HTTP)
               │
       ┌───────┼───────┬───────┐
       │       │       │       │
   ┌───▼──┐ ┌─▼───┐ ┌─▼────┐ ┌▼────┐
   │Claude│ │Claude│ │Claude│ │Other│
   │Desktop│ │ CLI │ │ Web │ │Clients│
   └──────┘ └─────┘ └──────┘ └─────┘
```

**Key Principle:** MCP server = Data layer, Claude AI = Intelligence layer

---

## Troubleshooting

### MCP Server Won't Start
```bash
# Test directly
cd /home/bashar/odoo18
source venv/bin/activate
python odoo_mcp_server.py stdio

# Check Odoo connection
curl http://localhost:8069/web/database/selector
```

### Claude Desktop Not Detecting
1. Verify config file exists:
   ```bash
   cat ~/.config/Claude/claude_desktop_config.json
   ```
2. Check JSON syntax: Use jsonlint or VS Code
3. Verify path in config matches actual script location
4. Check logs: `~/.config/Claude/logs/`

### ngrok Connection Issues
- Free tier URLs expire - regenerate for each session
- May see "ngrok warning" page - click "Visit Site"
- Check firewall allows ngrok

---

## Security Best Practices

⚠️ **IMPORTANT:**

1. **Never commit credentials to git**
   - `.env` file is in `.gitignore`
   - Don't hardcode passwords

2. **For ngrok:**
   - URLs are temporary (regenerate each time)
   - Anyone with URL can access until you stop ngrok
   - Only use for testing

3. **For production cloud:**
   - Use HTTPS only
   - Add authentication layer
   - Implement rate limiting
   - Restrict by IP if possible

4. **MCP Server Access:**
   - Only exposes specific Odoo operations (not full admin)
   - Field validation prevents unauthorized changes
   - See `odoo_mcp_server.py` for allowed operations

---

## Available MCP Tools (50+ tools!)

### CRM
✅ `crm_search_leads` - Search and filter leads
✅ `crm_get_lead` - Get lead details
✅ `crm_update_lead` - Update lead information

### Sales
✅ `sale_create_quote_from_lead` - Create quotations
✅ `sale_confirm_order` - Confirm orders
✅ `sale_get_order` - Get order details

### Inventory
✅ `stock_search_picking` - Search stock transfers
✅ `stock_get_picking` - Get transfer details
✅ `stock_validate_picking` - Validate transfers

### Accounting
✅ `account_search_invoices` - Search invoices
✅ `account_create_invoice` - Create invoices

### Purchasing
✅ `purchase_search_orders` - Search purchase orders
✅ `purchase_create_order` - Create PO

### Projects
✅ `project_search_tasks` - Search tasks
✅ `project_create_task` - Create tasks

### HR
✅ `hr_search_employees` - Search employees
✅ `hr_create_employee` - Create employee records

### Products
✅ `product_search_products` - Search products
✅ `product_get_product` - Get product details

### Analytics
✅ `dashboard_get_kpis` - Get KPIs
✅ `report_get_dashboard_data` - Dashboard data

### Automation
✅ `workflow_schedule_activity` - Schedule activities
✅ `automation_run_server_action` - Run server actions
✅ `bulk_update_records` - Bulk updates

**...and 30+ more tools!** See `odoo_mcp_server.py` for complete list.

---

## Test Queries to Try

Once connected to any Claude interface, try:

**CRM:**
- "Find all leads with probability > 50% and show their expected revenue"
- "Update lead 123 to probability 75%"
- "Create a follow-up email for lead ID 45"

**Sales:**
- "Show me sales orders from this week"
- "Create a quote for lead 67 with products X, Y, Z"
- "What's the total sales amount this month?"

**Inventory:**
- "Show pending stock transfers"
- "Validate picking 234"

**Analytics:**
- "Show me KPIs for last month"
- "Generate a sales report"

---

## Next Steps

1. ✅ Create `.env` file with Odoo credentials
2. ✅ Fix `mcp_wrapper.sh` path
3. ✅ Choose your method (Desktop, Web, or CLI)
4. ✅ Test with a simple query
5. ✅ Start automating Odoo workflows with AI!

---

**Last Updated:** 2026-02-09
**MCP Protocol:** FastMCP
**Odoo Version:** 18.0
**Claude Desktop:** Free Download
**Claude Web App:** claude.ai
**Claude Code CLI:** Already integrated!
