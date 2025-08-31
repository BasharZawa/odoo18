#!/bin/bash
# MCP Server Wrapper Script
cd /home/codebind/odoo18
source venv/bin/activate
python odoo_mcp_server.py "$@"
