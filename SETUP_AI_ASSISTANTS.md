# Claude Desktop MCP Setup Guide

## Step 1: Download Claude Desktop (FREE)
1. Go to: https://claude.ai/download
2. Download for your OS (Windows/Mac/Linux)
3. Install normally

## Step 2: Configure MCP Server
Claude Desktop config location:
- **Linux**: ~/.config/Claude/claude_desktop_config.json
- **Mac**: ~/Library/Application Support/Claude/claude_desktop_config.json  
- **Windows**: %APPDATA%\Claude\claude_desktop_config.json

## Step 3: Use the Configuration
Copy the content from: /home/codebind/odoo18/claude_config.json

## Step 4: Restart Claude Desktop
After copying config, restart Claude Desktop

## Step 5: Test Integration
In Claude Desktop, you can now ask:
- "Search for leads in Odoo with probability over 80%"
- "Create a new customer named 'AI Test Customer'"
- "Update lead ID 44 with a new description"
- "Post a message to lead chatter"

## Alternative: VS Code Continue (Also FREE)
1. Install Continue extension in VS Code
2. Configure with your MCP server
3. Use within your development environment

## Your MCP Server Commands:
- Start server: `python odoo_mcp_server.py stdio`
- Test server: `python test_mcp.py`
- View config: `cat claude_config.json`

## Available MCP Tools:
✅ crm_search_leads - Search CRM leads
✅ crm_get_lead - Get lead details  
✅ crm_update_lead - Update lead information
✅ res_partner_find_or_create - Manage customers
✅ sale_create_quote_from_lead - Create quotations
✅ mail_message_post - Post to chatter
✅ Lead schema resource for validation
✅ Follow-up email prompt template
