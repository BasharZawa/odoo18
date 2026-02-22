# External Integrations

**Analysis Date:** 2026-02-12

## APIs & External Services

**UAE E-Invoicing:**
- Orchida Soft E-Invoicing API - Automatic invoice submission to UAE government e-invoicing system
  - SDK/Client: `requests` (HTTP POST)
  - Endpoint: `https://dev.orchida-einvoice.com/api-pub/api/InvGenerateQr`
  - Implementation: `odoo/custom_addons/orchida_uae_e_invoicing/models/account_move.py`
  - Auth: Bearer token + Company-id header
  - Trigger: Automatic on invoice posting (`action_post`)
  - Config params: `api_module.api_token`, `CompanyID`

**AI Report Generation (n8n + Claude):**
- n8n Webhook - Sends natural language queries to n8n workflow
  - SDK/Client: `requests` (HTTP POST)
  - Implementation: `odoo/custom_addons/smart_report_builder/controllers/main.py`
  - Auth: Bearer token (optional)
  - Payload: Natural language query + Odoo model metadata
  - Response: read_group parameters (model, domain, groupby, measures)
  - Config params: `smart_report_builder.n8n_webhook_url`, `smart_report_builder.n8n_auth_token`
  - Workflow file: `odoo/custom_addons/smart_report_builder/n8n_workflow.json`

## Data Storage

**Databases:**
- PostgreSQL - OdooE enterprise database
  - Connection: `psycopg2` adapter
  - Host/Port: Configured in `odoo.conf`
  - Database name: `OdooE` (per CLAUDE.md)
  - Credentials: user: `admin`, password: `admin`
  - Client: Odoo ORM (all database queries use Odoo's ORM, not raw SQL)

**File Storage:**
- Local filesystem - Attachment storage in Odoo's file store
  - Location: Configured in `odoo.conf` (`data_dir` parameter)
  - No cloud storage integration detected

**Caching:**
- Redis - Not detected in dependencies or custom code
- In-memory: Odoo's default session caching

## Authentication & Identity

**Auth Provider:**
- Custom (Odoo native authentication)
  - Implementation: Odoo's built-in user/password system
  - Database: `res.users` model with password hashing via `passlib`
  - Session management: Odoo's HTTP session/cookie system

**LDAP Support:**
- Available (ldap dependency optional): `python-ldap 3.4.0+`
- Not actively configured in custom modules
- Can be enabled via Odoo settings if needed

## Monitoring & Observability

**Error Tracking:**
- None detected in custom code
- Logging: Standard Python logging module via `logging` (seen in smart_report_builder)

**Logs:**
- Approach: Python logging to console/file configured in `odoo.conf`
- Logger instances: `_logger = logging.getLogger(__name__)` pattern used in custom modules
- Example: `odoo/custom_addons/smart_report_builder/controllers/main.py` logs query failures

**Request Tracing:**
- Request tracking recorded in `api.sent.invoice` model for UAE e-invoicing calls
- Stores: timestamp, HTTP response code, response body, success flag

## CI/CD & Deployment

**Hosting:**
- Local development: WSL2 at `http://localhost:8069`
- Deployment target: WSGI application (Gunicorn/uWSGI)

**CI Pipeline:**
- None detected in custom modules
- Version control: Git with 30 custom addons

## Environment Configuration

**Required env vars:**
- Database credentials (from `odoo.conf` or environment)
- `api_module.api_token` - UAE e-invoicing bearer token
- `CompanyID` - Company identifier for e-invoicing
- `smart_report_builder.n8n_webhook_url` - n8n webhook endpoint
- `smart_report_builder.n8n_auth_token` - n8n authentication (optional)

**Secrets location:**
- `.env` file present - Contains environment configuration
- `ir.config_parameter` model - Stores system parameters including API tokens
- `odoo.conf` - Server configuration file
- CAUTION: Tokens stored in config parameters are accessible to authenticated users with technical settings access

## Webhooks & Callbacks

**Incoming:**
- n8n Webhook Response - Receives JSON with query parameters from n8n
  - Route: Implicit callback from n8n `requests.post()` in smart_report_builder
  - Format: `{'model': str, 'domain': list, 'groupby': list, 'measures': list}`
  - Implementation: `_call_n8n()` method expects synchronous HTTP response

**Outgoing:**
- UAE E-Invoicing API POST - Sends invoice data to Orchida API
  - Trigger: Invoice validation in `account_move.action_post()`
  - Route: `POST https://dev.orchida-einvoice.com/api-pub/api/InvGenerateQr`
  - Payload: Invoice line items, amounts, company info, buyer details
  - Response: Stored in `api.sent.invoice` record

- n8n Webhook POST - Sends natural language query + metadata
  - Trigger: User submits query in Smart Report Builder UI
  - Route: Configurable via `smart_report_builder.n8n_webhook_url` parameter
  - Payload: `{'query': str, 'today': str, 'models': dict}`
  - Response: Query execution parameters (read_group format)

## Legacy/SOAP Integration

**SOAP/WSDL Support:**
- zeep (4.1.0+) available but not actively used in visible custom modules
- Indicates potential for legacy system integration (ERP, accounting systems, etc.)

## External Data References

**GeoIP:**
- geoip2 (2.9.0) available in dependencies
- Not configured in visible custom modules
- Could be used for location-based logic if needed

---

*Integration audit: 2026-02-12*
