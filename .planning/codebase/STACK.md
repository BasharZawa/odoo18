# Technology Stack

**Analysis Date:** 2026-02-12

## Languages

**Primary:**
- Python 3.10 - Odoo 18 framework and custom addon development
- XML - View definitions, data files, and module configuration
- JavaScript - Frontend UI enhancements and custom components (Odoo web framework)

**Secondary:**
- HTML/CSS - Frontend templates and styling
- JSON - Configuration and data exchange (n8n workflows)

## Runtime

**Environment:**
- Odoo 18.0 Enterprise (custom fork)
- WSGI application server

**Package Manager:**
- pip (Python package manager)
- Lockfile: `requirements.txt` present with version pinning

## Frameworks

**Core:**
- Odoo 18.0 Enterprise - ERP platform with ORM, views, controllers, fields system
- Odoo Web Framework - Backend JavaScript framework for dynamic UI

**Testing:**
- Odoo's built-in test framework (unittest-based)

**Build/Dev:**
- libsass - SCSS compilation for styling
- Werkzeug - WSGI application framework (2.0.2 for Python ≤3.10, 2.2.2 for 3.10-3.12, 3.0.1 for ≥3.12)

## Key Dependencies

**Critical:**
- psycopg2 (2.9.2+) - PostgreSQL database adapter for OdooE database connections
- lxml (4.8.0+) - XML/HTML parsing for view compilation and data processing
- Jinja2 (3.0.3+) - Template engine for report generation
- openpyxl (3.0.9+) - Excel file generation for exports

**Web & API:**
- requests (2.25.1+) - HTTP client for external API calls (UAE e-invoicing integration)
- zeep (4.1.0+) - SOAP/WSDL client for legacy system integration

**Data Processing:**
- openpyxl - Excel read/write for data import/export
- PyPDF2 (1.26.0+) - PDF manipulation for reports
- reportlab (3.6.8+) - PDF document generation
- python-dateutil - Date/time utilities

**Infrastructure:**
- Babel (2.9.1+) - Internationalization and localization
- pytz - Timezone support
- python-stdnum (1.17+) - Standard number validation (tax IDs, etc.)

**Security & Cryptography:**
- cryptography (3.4.8+) - Cryptographic operations
- passlib (1.7.4+) - Password hashing
- pyopenssl (21.0.0+) - TLS/SSL support

**Utilities:**
- num2words - Number-to-words conversion for reports
- qrcode - QR code generation (UAE e-invoicing)
- polib - Gettext file handling for translations
- vobject - iCalendar and vCard handling
- geoip2 (2.9.0) - GeoIP data lookups

**System & Process:**
- psutil - Process and system utilities
- gevent/greenlet - Async I/O for concurrent connections
- pyserial - Serial port communication (legacy devices)
- pyusb - USB device communication (POS hardware)

## Configuration

**Environment:**
- `.env` file present - Contains environment variables
- `odoo.conf` - Odoo server configuration (database credentials, addons path)
- Configuration parameters stored in `ir.config_parameter` model:
  - `smart_report_builder.n8n_webhook_url` - n8n webhook for AI reports
  - `smart_report_builder.n8n_auth_token` - n8n authentication
  - `api_module.api_token` - UAE e-invoicing API token
  - `CompanyID` - Company identifier for external APIs

**Build:**
- No frontend build pipeline (Odoo handles asset compilation)
- SCSS compilation via libsass for custom styles
- Static assets served from module directories: `static/src/`

## Platform Requirements

**Development:**
- Python 3.10+
- PostgreSQL database (OdooE requires PostgreSQL)
- Linux/WSL2 (project runs on WSL2)

**Production:**
- Python 3.10+
- PostgreSQL 12+
- WSGI application server (uWSGI, Gunicorn, etc.)
- File system for attachments
- SMTP for email delivery (built into Odoo)

---

*Stack analysis: 2026-02-12*
