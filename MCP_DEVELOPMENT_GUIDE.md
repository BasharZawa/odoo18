# MCP Server Development Guide

**For customizing and extending the Odoo MCP Server**

---

## Development Environment Setup

### Prerequisites

✅ Python 3.x with virtual environment
✅ Odoo 18 running locally
✅ MCP dependencies installed
✅ VS Code or your preferred editor

### Directory Structure

```
/home/bashar/odoo18/
├── odoo_mcp_server.py           # Main MCP server (production)
├── mcp_dev/                     # Development workspace
│   ├── custom_tools.py          # Your custom tools
│   ├── test_tools.py            # Tool testing
│   ├── examples/                # Example implementations
│   └── README.md
├── .env                         # Credentials
└── mcp_wrapper.sh               # Production wrapper
```

---

## Quick Start: Add a Custom Tool

### 1. Create Your Custom Tool

Edit `odoo_mcp_server.py` or create a separate file:

```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Define input/output schemas
class MyToolInput(BaseModel):
    param1: str = Field(description="First parameter")
    param2: int = Field(default=10, description="Second parameter")

class MyToolOutput(BaseModel):
    result: str
    count: int

# Add tool to MCP server
@mcp.tool()
def my_custom_tool(input: MyToolInput) -> MyToolOutput:
    """
    Description that Claude will see.
    Explain what this tool does and when to use it.
    """
    # Your logic here
    result = ODOO.search_read(
        "crm.lead",
        [["name", "ilike", input.param1]],
        ["id", "name"],
        limit=input.param2
    )

    return MyToolOutput(
        result=f"Found {len(result)} leads",
        count=len(result)
    )
```

### 2. Test Your Tool

```bash
# Start MCP server in development mode
source venv/bin/activate
python odoo_mcp_server.py stdio

# Or use MCP Inspector
npx @modelcontextprotocol/inspector python odoo_mcp_server.py stdio
```

### 3. Use in Claude

Restart Claude Desktop and ask:
```
"Use my custom tool to search for 'ABC' with limit 5"
```

---

## Development Workflow

### Hot Reload Development

**Create development wrapper:** `mcp_dev_wrapper.sh`

```bash
#!/bin/bash
cd /home/bashar/odoo18
source venv/bin/activate

# Enable debug logging
export MCP_DEBUG=1

# Watch for changes and auto-reload
while true; do
    python odoo_mcp_server.py stdio
    echo "Server stopped. Restarting in 2s..."
    sleep 2
done
```

### Testing Without Claude

**Create test script:** `test_mcp_tools.py`

```python
#!/usr/bin/env python3
"""Test MCP tools without Claude Desktop"""

import sys
from dotenv import load_dotenv
load_dotenv()

from odoo_mcp_server import ODOO, mcp

# Test tool execution
def test_tool(tool_name, params):
    print(f"\n{'='*60}")
    print(f"Testing: {tool_name}")
    print(f"Params: {params}")
    print(f"{'='*60}\n")

    try:
        # Get the tool function
        tool = getattr(sys.modules['odoo_mcp_server'], tool_name)
        result = tool(params)
        print(f"✅ Success!")
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

# Run tests
if __name__ == "__main__":
    from odoo_mcp_server import LeadSearchIn

    # Test 1: Search leads
    test_tool('crm_search_leads', LeadSearchIn(
        domain=[["probability", ">=", 75]],
        limit=5
    ))

    # Test 2: Get single lead
    # test_tool('crm_get_lead', {...})

    print("\n✅ All tests completed!")
```

---

## Common Customization Patterns

### Pattern 1: Add New Model Support

**Example: Add support for HR Attendance**

```python
from pydantic import BaseModel

class AttendanceSearchIn(BaseModel):
    employee_id: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 50

@mcp.tool()
def hr_search_attendance(input: AttendanceSearchIn) -> list[dict]:
    """Search HR attendance records"""
    domain = []

    if input.employee_id:
        domain.append(["employee_id", "=", input.employee_id])
    if input.date_from:
        domain.append(["check_in", ">=", input.date_from])
    if input.date_to:
        domain.append(["check_out", "<=", input.date_to])

    return ODOO.search_read(
        "hr.attendance",
        domain,
        ["id", "employee_id", "check_in", "check_out"],
        limit=input.limit
    )
```

### Pattern 2: Add Business Logic Tools

**Example: Calculate sales commission**

```python
from decimal import Decimal

class CommissionInput(BaseModel):
    salesperson_id: int
    date_from: str
    date_to: str

class CommissionOutput(BaseModel):
    salesperson: str
    total_sales: float
    commission_rate: float
    commission_amount: float

@mcp.tool()
def calculate_commission(input: CommissionInput) -> CommissionOutput:
    """Calculate sales commission for a salesperson"""

    # Get sales orders
    orders = ODOO.search_read(
        "sale.order",
        [
            ["user_id", "=", input.salesperson_id],
            ["date_order", ">=", input.date_from],
            ["date_order", "<=", input.date_to],
            ["state", "in", ["sale", "done"]]
        ],
        ["amount_total"]
    )

    # Calculate total
    total_sales = sum(order["amount_total"] for order in orders)

    # Get commission rate from HR (example)
    user = ODOO.read("res.users", [input.salesperson_id], ["name"])[0]
    commission_rate = 0.05  # 5% - could be from settings

    return CommissionOutput(
        salesperson=user["name"],
        total_sales=total_sales,
        commission_rate=commission_rate,
        commission_amount=total_sales * commission_rate
    )
```

### Pattern 3: Add Workflow Actions

**Example: Automated follow-up creation**

```python
class FollowUpInput(BaseModel):
    lead_id: int
    days_delay: int = 7
    activity_type: str = "call"

@mcp.tool()
def schedule_follow_up(input: FollowUpInput) -> dict:
    """Schedule a follow-up activity for a lead"""
    from datetime import datetime, timedelta

    # Get lead info
    lead = ODOO.read("crm.lead", [input.lead_id], ["name", "user_id"])[0]

    # Calculate deadline
    deadline = (datetime.now() + timedelta(days=input.days_delay)).strftime("%Y-%m-%d")

    # Get activity type ID
    activity_types = ODOO.search_read(
        "mail.activity.type",
        [["name", "ilike", input.activity_type]],
        ["id"],
        limit=1
    )

    if not activity_types:
        raise ValueError(f"Activity type '{input.activity_type}' not found")

    # Create activity
    activity_id = ODOO.create("mail.activity", {
        "res_model_id": ODOO.call_kw("ir.model", "search", [[("model", "=", "crm.lead")]], {})[0],
        "res_id": input.lead_id,
        "activity_type_id": activity_types[0]["id"],
        "user_id": lead["user_id"][0] if lead["user_id"] else None,
        "date_deadline": deadline,
        "summary": f"Follow up on {lead['name']}"
    })

    return {
        "activity_id": activity_id,
        "lead_name": lead["name"],
        "deadline": deadline,
        "scheduled": True
    }
```

### Pattern 4: Add Analytics Tools

**Example: Sales pipeline analysis**

```python
class PipelineAnalysisInput(BaseModel):
    team_id: int | None = None
    date_from: str | None = None

class PipelineStage(BaseModel):
    stage_name: str
    lead_count: int
    total_revenue: float
    avg_probability: float

@mcp.tool()
def analyze_sales_pipeline(input: PipelineAnalysisInput) -> list[PipelineStage]:
    """Analyze sales pipeline by stage"""

    domain = []
    if input.team_id:
        domain.append(["team_id", "=", input.team_id])
    if input.date_from:
        domain.append(["create_date", ">=", input.date_from])

    # Use read_group for aggregation
    results = ODOO.call_kw("crm.lead", "read_group", [], {
        "domain": domain,
        "fields": ["expected_revenue", "probability"],
        "groupby": ["stage_id"]
    })

    pipeline = []
    for group in results:
        pipeline.append(PipelineStage(
            stage_name=group["stage_id"][1] if group["stage_id"] else "No Stage",
            lead_count=group["stage_id_count"],
            total_revenue=group["expected_revenue"] or 0,
            avg_probability=group["probability"] or 0
        ))

    return pipeline
```

---

## Testing & Debugging

### Method 1: MCP Inspector (Visual Testing)

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Launch inspector
npx @modelcontextprotocol/inspector python odoo_mcp_server.py stdio
```

**Opens web UI where you can:**
- ✅ See all available tools
- ✅ Test tools with parameters
- ✅ View responses
- ✅ Debug JSON-RPC messages

### Method 2: Direct Python Testing

```python
# test_my_tool.py
from dotenv import load_dotenv
load_dotenv()

from odoo_mcp_server import my_custom_tool, MyToolInput

result = my_custom_tool(MyToolInput(param1="test", param2=10))
print(result)
```

### Method 3: JSON-RPC Testing

```bash
# Test with raw JSON-RPC
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"my_custom_tool","arguments":{"param1":"test","param2":10}}}' | \
  python odoo_mcp_server.py stdio
```

### Method 4: Integration Testing

```python
# integration_test.py
import subprocess
import json

def test_mcp_tool(tool_name, params):
    """Test tool via MCP protocol"""

    process = subprocess.Popen(
        ['python', 'odoo_mcp_server.py', 'stdio'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }

    process.stdin.write(json.dumps(init_msg) + "\n")
    process.stdin.flush()

    # Call tool
    tool_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }

    process.stdin.write(json.dumps(tool_msg) + "\n")
    process.stdin.flush()

    # Read response
    response = process.stdout.readline()
    process.terminate()

    return json.loads(response)
```

---

## Advanced: Custom Resources & Prompts

### Add Custom Resources

Resources provide static data/schemas to Claude:

```python
@mcp.resource("odoo://data/commission-rates")
def commission_rates() -> bytes:
    """Commission rate configuration"""
    rates = {
        "junior": 0.03,
        "senior": 0.05,
        "manager": 0.07
    }
    return json.dumps(rates).encode("utf-8")
```

### Add Custom Prompts

Prompt templates help Claude use your tools:

```python
@mcp.prompt("sales/commission-report")
def commission_report_prompt() -> list[dict]:
    """Generate sales commission report"""
    return [
        {
            "role": "system",
            "content": "You are a sales analyst. Generate detailed commission reports."
        },
        {
            "role": "user",
            "content": (
                "Generate a commission report for salesperson {{salesperson_id}} "
                "from {{date_from}} to {{date_to}}. Include:\n"
                "- Total sales\n"
                "- Commission amount\n"
                "- Top deals\n"
                "- Performance comparison"
            )
        }
    ]
```

---

## Best Practices

### 1. Tool Design

✅ **DO:**
- Clear, descriptive tool names
- Detailed docstrings (Claude reads these!)
- Input validation with Pydantic
- Proper error handling
- Return structured data

❌ **DON'T:**
- Generic names like `do_something`
- Missing or vague descriptions
- Unvalidated inputs
- Silent failures
- Return raw strings

### 2. Security

```python
# ✅ Whitelist allowed fields
ALLOWED_FIELDS = {"name", "probability", "email_from"}
values = {k: v for k, v in input.values.items() if k in ALLOWED_FIELDS}

# ✅ Validate IDs
if input.lead_id <= 0:
    raise ValueError("Invalid lead ID")

# ✅ Check permissions
if not user_has_permission(input.operation):
    raise PermissionError("Insufficient permissions")
```

### 3. Performance

```python
# ✅ Use limits
result = ODOO.search_read(model, domain, fields, limit=100)

# ✅ Select specific fields
fields = ["id", "name", "email"]  # Not all fields

# ✅ Use read_group for aggregations
ODOO.call_kw(model, "read_group", [], {...})
```

### 4. Error Handling

```python
@mcp.tool()
def safe_tool(input: MyInput) -> MyOutput:
    """Well-designed tool with error handling"""
    try:
        # Validate input
        if not input.param1:
            raise ValueError("param1 is required")

        # Execute operation
        result = ODOO.search_read(...)

        # Validate output
        if not result:
            return MyOutput(message="No records found", count=0)

        return MyOutput(data=result, count=len(result))

    except ValueError as e:
        raise ValueError(f"Invalid input: {e}")
    except Exception as e:
        raise RuntimeError(f"Operation failed: {e}")
```

---

## Deployment

### Development → Production

1. **Test thoroughly**
   ```bash
   python test_mcp_tools.py
   ```

2. **Update documentation**
   - Add tool descriptions
   - Document parameters
   - Add usage examples

3. **Restart Claude Desktop**
   - Close completely
   - Reopen to load changes

4. **Test in Claude**
   - Try your new tools
   - Verify outputs
   - Check error handling

### Version Control

```bash
# Commit your changes
git add odoo_mcp_server.py
git commit -m "Add custom commission calculation tool"

# Tag releases
git tag -a v1.1.0 -m "Added commission and follow-up tools"
```

---

## Examples Library

Check `/home/bashar/odoo18/mcp_dev/examples/` for:
- ✅ Custom CRM tools
- ✅ Advanced search tools
- ✅ Workflow automation
- ✅ Analytics tools
- ✅ Integration examples

---

## Resources

- **MCP Specification**: https://modelcontextprotocol.io/
- **FastMCP Docs**: https://github.com/jlowin/fastmcp
- **Odoo API**: https://www.odoo.com/documentation/18.0/developer/reference/external_api.html
- **Pydantic**: https://docs.pydantic.dev/

---

**Ready to start developing? Check the examples in `mcp_dev/` or add your first custom tool!**
