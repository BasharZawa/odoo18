# SEDCO Metabase Reports

## Overview

`sedco_metabase_reports` embeds selected Metabase dashboards inside Odoo 18 under a dedicated **Reports** menu.

The module is designed around two access-control layers:

1. Odoo group-based access decides which users can see a dashboard entry.
2. A signed Metabase embed JWT can lock dashboard parameters to the current Odoo user, so the same dashboard can show user-specific data.

This module uses Metabase signed static embedding and does not depend on Metabase Pro or Enterprise features.

## What the Module Provides

- A top-level **Reports** menu in Odoo.
- A reports index page at `/metabase/reports`.
- One embed route per dashboard at `/metabase/embed/<code>`.
- A configurable model, `metabase.dashboard`, for dashboard metadata and permissions.
- A registry model, `metabase.sync.model`, for Odoo models that may be refreshed before rendering a dashboard.
- Optional on-demand sync with UXServer before an iframe is shown.

## Module Structure

- `__manifest__.py`: module metadata and loaded XML files.
- `controllers/main.py`: routes, permission checks, JWT creation, and sync trigger.
- `models/metabase_dashboard.py`: dashboard configuration model.
- `models/metabase_sync_model.py`: syncable model registry.
- `security/metabase_groups.xml`: security groups.
- `security/ir.model.access.csv`: model ACLs.
- `views/metabase_templates.xml`: reports index and embed templates.
- `views/metabase_dashboard_views.xml`: configuration UI for dashboards.
- `views/menus.xml`: reports menu tree and URL actions.
- `data/ir_config_parameter.xml`: seeded system parameter placeholder.
- `data/metabase_sync_models.xml`: seeded sync model registry.
- `data/metabase_dashboards.xml`: seeded dashboard records.

## Main User Flow

1. A logged-in Odoo user opens **Reports** or visits `/metabase/reports`.
2. The controller loads active `metabase.dashboard` records with `sudo()`.
3. The controller filters them against the real user’s `groups_id`.
4. When the user opens `/metabase/embed/<code>`, the controller:
   - finds the matching active dashboard,
   - verifies access again,
   - reads Metabase config from `ir.config_parameter`,
   - optionally triggers UXServer sync,
   - computes locked Metabase parameters,
   - signs a short-lived JWT,
   - renders an iframe pointing to Metabase’s signed embed URL.

## Security Model

### 1. Menu-Level Access

Menus are gated by Odoo groups in `views/menus.xml`.

Seeded groups:

- `group_mb_viewer`: standard business dashboards.
- `group_mb_manager`: implies viewer access and can manage dashboard configuration.
- `group_mb_ops`: operational dashboards such as sync/health views.

### 2. Controller-Level Access

Even if a user knows a dashboard URL, the controller still checks:

- the dashboard exists,
- it is active,
- the user belongs to at least one allowed group for that dashboard.

If not, the route returns `403 Forbidden`.

### 3. Row-Level Access in Metabase

For dashboards with filtering enabled, the JWT payload includes locked parameters.

Current filter modes:

- `none`: no locked parameters are sent.
- `salesperson`: always lock the configured parameter to the current Odoo user ID.
- `salesperson_bypass_manager`: same as above, except users in `bypass_group_id` receive an empty array and therefore bypass the row filter.

The default locked parameter name is `owner_id`, but each dashboard can override it with names such as `salesperson_id`.

## Configuration

### Required System Parameters

Set these in **Settings -> Technical -> Parameters -> System Parameters**:

- `sedco_metabase_reports.site_url`
  - Base URL of Metabase, for example `https://metabase.example.com`
- `sedco_metabase_reports.jwt_secret`
  - Metabase embedding secret used to sign JWTs

### Optional System Parameters

These enable on-demand sync before dashboard render:

- `sedco_metabase_reports.uxserver_url`
  - Base URL of UXServer
- `sedco_metabase_reports.uxserver_sync_api_key`
  - API key sent as `X-API-KEY` to the reload endpoint

### Seeded Parameter Behavior

Only `sedco_metabase_reports.site_url` is seeded, with a placeholder value of `http://localhost:3000`.

The JWT secret and UXServer settings are intentionally not seeded. This avoids silently passing validation with fake values.

## Data Models

### `metabase.dashboard`

This is the core configuration model for embedded dashboards.

Important fields:

- `name`: display label shown in Odoo.
- `code`: stable route key used in `/metabase/embed/<code>`.
- `metabase_id`: numeric Metabase dashboard ID.
- `allowed_group_ids`: Odoo groups allowed to access the dashboard.
- `filter_mode`: whether row-level filtering is applied.
- `locked_parameter_name`: parameter name expected by Metabase.
- `bypass_group_id`: group that bypasses row-level filtering for bypass modes.
- `active`: controls visibility and route availability.
- `sequence`: ordering in UI.
- `sync_model_ids`: models to request from UXServer before opening the dashboard.
- `sync_timeout_seconds`: timeout for sync request.

Constraint:

- `code` must be unique.

### `metabase.sync.model`

This is a registry of Odoo model names that UXServer understands.

Important fields:

- `name`: technical model name such as `sale.order`.
- `display`: friendly label for the configuration form.
- `active`: enable/disable the registry record.

Constraint:

- `name` must be unique.

## Seeded Dashboards

The module seeds five dashboard records:

- `sales_orders`
  - Viewer + Manager access
  - Filtered by `salesperson_id`
  - Managers bypass the row filter
  - Triggers sync for sales-related models
- `accounts`
  - Viewer + Manager access
  - No row-level filter
  - Triggers sync for partner/account-related lookup models
- `contacts`
  - Viewer + Manager access
  - No row-level filter
  - Triggers sync for contact-related data
- `migration_kpis`
  - Manager + Ops access
  - No sync on open
- `sync_health`
  - Ops access only
  - No sync on open

The records are loaded with `noupdate="1"`, which is important:

- module upgrades do not overwrite edited dashboard definitions,
- real `metabase_id` values are preserved after operators set them,
- dashboards can be safely tuned in production from the Odoo UI.

## On-Demand Sync

Before rendering the iframe, the controller may call:

- `POST <uxserver_url>/api/OdooSyncReload`

Request body:

```json
{
  "models": ["sale.order", "sale.order.line", "res.partner"]
}
```

Request headers:

- `Content-Type: application/json`
- `X-API-KEY: <uxserver_sync_api_key>`

Behavior:

- If `uxserver_url` or `uxserver_sync_api_key` is missing, sync is skipped.
- If the dashboard has no `sync_model_ids`, sync is skipped.
- If sync succeeds, the dashboard renders normally.
- If sync times out or returns an HTTP error, the dashboard still renders, but the page shows a stale-data warning.

This is a deliberate degrade-but-alive design.

## JWT Payload

The JWT created by the controller contains:

- `resource.dashboard`: the Metabase dashboard ID
- `params`: locked parameter values, if any
- `exp`: expiration time

Token lifetime is currently 600 seconds.

The signature algorithm is `HS256`.

## UI and Routes

### Routes

- `/metabase/reports`
  - Reports landing page listing dashboards the user can access
- `/metabase/embed/<code>`
  - Embed page for a single dashboard

Both routes use `auth='user'`, so anonymous users cannot access them.

### Odoo Menus

The module adds:

- a root **Reports** menu,
- one menu item per seeded dashboard,
- a **Configuration** submenu for managers.

The configuration menu opens the `metabase.dashboard` list/form view.

## How to Add a New Dashboard

### In Metabase

1. Create and publish the dashboard in Metabase.
2. If row-level filtering is needed, add a locked embed parameter with a stable slug such as `salesperson_id`.
3. Note the numeric Metabase dashboard ID.

### In Odoo

1. Open **Reports -> Configuration -> Metabase Dashboards**.
2. Create a new dashboard record.
3. Set:
   - `name`
   - `code`
   - `metabase_id`
   - `allowed_group_ids`
   - `filter_mode`
   - `locked_parameter_name` if filtering is used
   - `bypass_group_id` if using a bypass mode
   - `sync_model_ids` if the dashboard should request fresh data on open
4. Save the record.

### If You Want a Dedicated Menu Entry

The dashboard record alone makes the route work, but the menu tree in this module is still XML-defined. To expose a dedicated sidebar entry for a new dashboard, add:

1. an `ir.actions.act_url` record pointing to `/metabase/embed/<code>`,
2. a `menuitem` referencing that action and the correct groups.

This is currently not fully data-driven.

## How Row-Level Filtering Must Align

For filtering to work correctly, the same parameter concept must line up in three places:

1. `locked_parameter_name` on the Odoo dashboard record
2. the Metabase dashboard embed parameter slug
3. the underlying Metabase SQL/dashboard filter logic

Example:

- Odoo sends `{"salesperson_id": 42}`
- Metabase dashboard expects locked parameter `salesperson_id`
- the query or filter logic restricts results to that user

If these names do not match exactly, the dashboard may render but ignore the intended filter.

## Permissions and ACLs

Model access is intentionally narrow:

- Viewer and Ops can read dashboard and sync-model records.
- Manager can read, create, write, and delete both models.

The controller uses `sudo()` only for reading configuration and metadata, then performs authorization checks against the actual request user. This avoids accidental ACL failures while still enforcing real access control.

## Failure Modes and Troubleshooting

### "Embed not configured"

Check:

- `sedco_metabase_reports.site_url` is set correctly
- `sedco_metabase_reports.jwt_secret` is set
- `metabase_id` is greater than `0`

### User sees `403 Forbidden`

Check:

- the dashboard is active,
- the user belongs to one of the dashboard’s `allowed_group_ids`,
- the user also has the relevant menu group if you expect the menu item to appear.

### Dashboard opens but shows unexpected data

Check:

- `filter_mode`
- `locked_parameter_name`
- the Metabase embed parameter slug
- whether the user belongs to the bypass group

### Dashboard opens with stale-data warning

Check:

- UXServer URL and API key
- dashboard `sync_model_ids`
- UXServer endpoint health
- dashboard sync timeout value

## Developer Notes

### Why Dashboard Data Uses `noupdate="1"`

Operator-managed values such as real `metabase_id` must survive module upgrades. Without `noupdate="1"`, a module update could reset production dashboards back to placeholder IDs.

### Why the Controller Rechecks Access

Menu visibility alone is not sufficient protection. Users can hit routes directly, so the controller enforces the same authorization again before generating the embed URL.

### Why Sync Failures Do Not Block Rendering

The module treats live sync as a freshness optimization, not a hard dependency. Reports remain available even when UXServer is slow or unavailable.

## Current Limitations

- Menu entries are seeded in XML and are not auto-generated from dashboard records.
- The module embeds dashboards only; it does not manage Metabase content lifecycle.
- JWT row filters are based on the current Odoo `res.users.id`, so Metabase queries must be designed around that identity.

## Recommended Operational Checklist

After installing or updating this module:

1. Set `site_url` and `jwt_secret`.
2. Publish each Metabase dashboard and enter its real `metabase_id`.
3. Assign Odoo users to the correct Metabase groups.
4. Verify row-level filtering with a viewer user and a manager user.
5. If using live sync, verify UXServer connectivity and timeout behavior.
6. Open each reports menu entry and confirm it renders as expected.
