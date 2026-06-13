# Odoo 18 Server Source

This folder contains the Odoo 18 server source only.

The authoritative SEDCO Odoo project context is:

`..\CLAUDE.md`

Before changing server code:

- Read `..\CLAUDE.md` for runtime paths, commands, and project boundaries.
- Search `..\custom_addons\custom_addons\` before implementing functionality
  in Odoo core.
- Prefer a SEDCO custom addon over modifying Odoo core when inheritance or
  extension can provide the required behavior.
- Treat `..\custom_addons\ent_addons\` as vendored and read-mostly.
- Use `..\config\odoo-native.conf` for the active addon and data paths.
- Preserve unrelated changes in this Git repository.

CRM migration is governed separately by `..\..\..\MIGRATION-CURRENT.md`.
n8n development belongs under `..\..\n8n-project\`, not in this repository.
