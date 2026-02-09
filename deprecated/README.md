# Deprecated Files

This folder contains deprecated code that is no longer actively maintained.

## Files

### free_claude_chatbot.py
- **Deprecated:** 2026-02-09
- **Reason:** Redundant with Claude AI interfaces (Desktop, CLI, Web App)
- **Replacement:** Use Claude Desktop, Claude Code CLI, or Claude Web App with MCP server
- **Status:** Not maintained, may have outdated patterns

## Why Deprecated?

The Flask chatbot was a custom web interface that:
- Used pattern matching instead of real AI
- Required manual maintenance for each intent
- Duplicated functionality available in Claude interfaces

The MCP server approach is cleaner:
- MCP server provides tools (data layer)
- Claude AI provides intelligence (AI layer)
- No need for custom chatbot logic

## Migration Path

If you were using the Flask chatbot:

**Instead of:** Running Flask chatbot at http://localhost:5000
**Use:** Claude Desktop with MCP integration

**Old way:**
```bash
python free_claude_chatbot.py
# Visit http://localhost:5000
```

**New way:**
```bash
# Just open Claude Desktop - MCP auto-connects
# Or use Claude Code CLI - already integrated
# Or use claude.ai with ngrok
```

## Archive Notice

These files are kept for reference but are not supported.
Use at your own risk if you need them.

---
**Archived:** 2026-02-09
