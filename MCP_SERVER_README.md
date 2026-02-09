# Odoo MCP Server - Technical Reference

## Overview

The Odoo MCP Server (`odoo_mcp_server.py`) provides a standardized Model Context Protocol (MCP) interface to your Odoo 18 database, enabling Claude AI to interact with Odoo data and operations.

## Architecture

```
┌─────────────────────────────────────┐
│    Odoo 18 Database (PostgreSQL)    │
└──────────────┬──────────────────────┘
               │
               │ JSON-RPC API
               │ (http://localhost:8069)
               │
┌──────────────▼──────────────────────┐
│        odoo_mcp_server.py           │
│                                     │
│  • OdooClient (JSON-RPC wrapper)   │
│  • 50+ MCP Tools                   │
│  • Pydantic Schemas                │
│  • FastMCP Framework               │
└──────────────┬──────────────────────┘
               │
               │ MCP Protocol
               │ (stdio/HTTP modes)
               │
┌──────────────▼──────────────────────┐
│       Claude AI Interfaces          │
│  • Claude Desktop                   │
│  • Claude Code CLI                  │
│  • Claude Web App (via HTTP)       │
└─────────────────────────────────────┘
```

## Core Components

### 1. OdooClient Class
**Purpose**: JSON-RPC wrapper for Odoo API

**Methods**:
- `authenticate()` - Login to Odoo
- `call_kw()` - Call any Odoo model method
- `search_read()` - Search and read records
- `read()` - Read specific records by ID
- `write()` - Update records
- `create()` - Create new records
- `name_search()` - Search by name

### 2. MCP Tools (50+ available)
**Purpose**: Exposed functions that Claude can call

**Categories**:
- **CRM**: Lead search, creation, updates
- **Sales**: Order management, quotation creation
- **Inventory**: Stock picking operations
- **Accounting**: Invoice management
- **Projects**: Task management
- **HR**: Employee operations
- **Products**: Product search and details
- **Analytics**: KPIs and dashboard data

### 3. Pydantic Schemas
**Purpose**: Type safety and validation

**Examples**:
```python
class LeadSearchIn(BaseModel):
    domain: list = Field(default_factory=list)
    fields: list[str] = Field(default=DEFAULT_LEAD_FIELDS)
    limit: int = 80

class LeadSearchOut(BaseModel):
    count: int
    results: list[dict]
```

## Configuration

### Environment Variables (.env)
```bash
ODOO_URL=http://localhost:8069    # Odoo server URL
ODOO_DB=odoo                       # Database name
ODOO_USER=admin                    # Username
ODOO_PASSWORD=sedco@123            # Password
```

### Running Modes

**1. stdio Mode (for Claude Desktop/CLI)**
```bash
python odoo_mcp_server.py stdio
```
- Communication via stdin/stdout
- Used by Claude Desktop and CLI
- Process-based communication

**2. HTTP Mode (for Claude Web App)**
```python
# Create odoo_mcp_http.py
from odoo_mcp_server import mcp
import uvicorn

uvicorn.run(mcp.get_asgi_app(), host="0.0.0.0", port=8000)
```
- REST API endpoints
- Server-Sent Events (SSE)
- Web-accessible

## Available Tools Reference

### CRM Tools

#### crm_search_leads
Search and filter CRM leads
```python
params = {
    "domain": [["probability", ">=", 75]],
    "fields": ["id", "name", "probability"],
    "limit": 10
}
```

#### crm_get_lead
Get single lead by ID
```python
params = {
    "id": 44,
    "fields": ["id", "name", "email_from", "stage_id"]
}
```

#### crm_update_lead
Update lead fields
```python
params = {
    "id": 44,
    "values": {
        "probability": 90,
        "stage_id": 4
    }
}
```

### Sales Tools

#### sale_create_quote_from_lead
Create quotation from lead
```python
params = {
    "lead_id": 44,
    "partner_id": 123,
    "lines": [
        {"product_id": 1, "qty": 5, "price": 100}
    ]
}
```

#### sale_confirm_order
Confirm quotation
```python
params = {"order_id": 456}
```

### Inventory Tools

#### stock_search_picking
Search stock transfers
```python
params = {
    "domain": [["state", "=", "assigned"]],
    "fields": ["id", "name", "partner_id"]
}
```

#### stock_validate_picking
Validate stock picking
```python
params = {"picking_id": 789}
```

### Accounting Tools

#### account_search_invoices
Search invoices
```python
params = {
    "domain": [["state", "=", "posted"]],
    "fields": ["id", "name", "amount_total"]
}
```

### Analytics Tools

#### dashboard_get_kpis
Get key performance indicators
```python
params = {
    "date_from": "2026-01-01",
    "date_to": "2026-12-31"
}
```

**Returns**: Total sales, order count, lead count, weighted pipeline

### Utility Tools

#### bulk_update_records
Update multiple records at once
```python
params = {
    "model": "crm.lead",
    "ids": [1, 2, 3],
    "values": {"user_id": 5}
}
```

#### data_export_to_csv
Export data to CSV
```python
params = {
    "model": "crm.lead",
    "domain": [],
    "fields": ["id", "name", "probability"]
}
```

## Security Features

### Field Whitelisting
Only allowed fields can be updated:
```python
allowed = {"name", "probability", "email_from", "phone",
           "description", "user_id", "stage_id"}
```

### Model Restrictions
Bulk operations limited to safe models:
```python
allowed_models = {"crm.lead", "res.partner", "product.template",
                  "project.task", "hr.employee"}
```

### Input Validation
- Pydantic schemas enforce types
- Domain filtering prevents SQL injection
- ID validation prevents unauthorized access

## Error Handling

### Connection Errors
```python
try:
    ODOO.authenticate()
except Exception as e:
    raise RuntimeError(f"Odoo connection failed: {e}")
```

### Tool Execution Errors
```python
try:
    result = ODOO.search_read(...)
except Exception as e:
    raise RuntimeError(f"Failed to search leads: {e}")
```

## Testing

### Test MCP Server
```bash
cd /home/bashar/odoo18
source venv/bin/activate
python odoo_mcp_server.py stdio
# Should print: "✅ Connected to Odoo: http://localhost:8069/odoo"
```

### Test with MCP Inspector
```bash
npx @modelcontextprotocol/inspector python odoo_mcp_server.py stdio
```

### Test Odoo Connection
```bash
curl http://localhost:8069/web/database/selector
```

## Extending the Server

### Adding New Tools

1. **Define Pydantic schemas**:
```python
class MyToolInput(BaseModel):
    param1: str
    param2: int
```

2. **Create tool function**:
```python
@mcp.tool()
def my_custom_tool(input: MyToolInput) -> dict:
    """Tool description for Claude"""
    result = ODOO.call_kw("model.name", "method", [args], {})
    return result
```

3. **Test the tool**:
```python
result = my_custom_tool(MyToolInput(param1="test", param2=123))
```

### Adding Resources

```python
@mcp.resource("odoo://data/my-resource")
def my_resource() -> bytes:
    """Provide static data to Claude"""
    data = {"key": "value"}
    return json.dumps(data).encode("utf-8")
```

### Adding Prompts

```python
@mcp.prompt("my/prompt-template")
def my_prompt() -> list[dict]:
    """Prompt template for Claude"""
    return [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Template: {{variable}}"}
    ]
```

## Performance Considerations

### Limit Results
Always use `limit` parameter:
```python
params = {"domain": [], "limit": 80}  # Don't return thousands
```

### Select Specific Fields
Only request needed fields:
```python
params = {
    "fields": ["id", "name"],  # Not all fields
}
```

### Connection Pooling
MCP server maintains single Odoo session:
```python
ODOO = OdooClient(...)  # One instance
ODOO.authenticate()     # Reuses session
```

## Troubleshooting

### Server Won't Start
```bash
# Check Python environment
which python
python --version

# Check dependencies
pip list | grep -E "mcp|fastmcp|requests|pydantic"

# Check .env file
cat .env
```

### Connection Refused
```bash
# Check Odoo is running
systemctl status odoo  # or ps aux | grep odoo
curl http://localhost:8069

# Check firewall
sudo ufw status
```

### Authentication Failed
```bash
# Verify credentials in .env
cat .env

# Test credentials manually
curl -X POST http://localhost:8069/web/session/authenticate \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"db":"odoo","login":"admin","password":"sedco@123"}}'
```

## Maintenance

### Update Dependencies
```bash
source venv/bin/activate
pip install --upgrade mcp fastmcp requests pydantic python-dotenv
```

### Monitor Logs
```bash
# Run with debug output
python odoo_mcp_server.py stdio 2>&1 | tee mcp_server.log
```

### Backup Configuration
```bash
# Backup .env and configs
tar -czf mcp_backup_$(date +%Y%m%d).tar.gz \
  .env \
  odoo_mcp_server.py \
  mcp_wrapper.sh \
  ~/.config/Claude/claude_desktop_config.json
```

## Resources

- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Odoo API**: https://www.odoo.com/documentation/18.0/developer/reference/external_api.html
- **Pydantic**: https://docs.pydantic.dev/

---

**Version**: 1.0.0
**Last Updated**: 2026-02-09
**Framework**: FastMCP
**Odoo Version**: 18.0
**Python**: 3.x
