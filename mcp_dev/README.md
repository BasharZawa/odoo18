# MCP Development Workspace

This directory contains tools and examples for developing custom MCP tools.

## Contents

- `custom_tools.py` - Your custom tool implementations
- `test_tools.py` - Tool testing script
- `examples/` - Example tool implementations
  - `crm_custom_tools.py` - CRM-specific examples
  - `analytics_tools.py` - Analytics and reporting
  - `workflow_tools.py` - Workflow automation

## Quick Start

### 1. Create a Custom Tool

Edit `custom_tools.py` and add:

```python
@mcp.tool()
def my_tool(input: MyInput) -> MyOutput:
    """Your tool description"""
    # Your logic
    return MyOutput(...)
```

### 2. Test It

```bash
python test_tools.py
```

### 3. Add to Main Server

Copy your tool to `odoo_mcp_server.py` and restart Claude Desktop.

## Development Workflow

```
1. Write tool in custom_tools.py
2. Test with test_tools.py
3. Verify in MCP Inspector
4. Copy to odoo_mcp_server.py
5. Restart Claude Desktop
6. Test in Claude
```

## See Also

- `/MCP_DEVELOPMENT_GUIDE.md` - Complete development guide
- `/MCP_SERVER_README.md` - Technical reference
