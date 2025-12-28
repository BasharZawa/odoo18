from __future__ import annotations
import os, json, time, typing as t
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# NEW: load .env automatically from workspace root
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # loads .env if present


# ---------- Odoo JSON-RPC client ----------
class OdooClient:
    def __init__(self, url: str, db: str, user: str, password: str):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.session = requests.Session()
        self.uid = None

    def _jsonrpc(self, path: str, payload: dict):
        resp = self.session.post(
            f"{self.url}{path}",
            json={"jsonrpc": "2.0", "method": "call", "params": payload, "id": time.time()},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

    def authenticate(self):
        self.uid = self._jsonrpc("/web/session/authenticate", {
            "db": self.db, "login": self.user, "password": self.password
        })["uid"]
        return self.uid

    def call_kw(self, model: str, method: str, args: list, kwargs: dict | None = None):
        if self.uid is None:
            self.authenticate()
        return self._jsonrpc("/web/dataset/call_kw", {
            "model": model, "method": method, "args": args, "kwargs": kwargs or {}
        })

    # Helpers
    def search_read(self, model: str, domain: list, fields: list, limit=80, offset=0, order: str | None = None):
        return self.call_kw(model, "search_read", [], {
            "domain": domain, "fields": fields, "limit": limit, "offset": offset, "order": order or "id desc"
        })

    def read(self, model: str, ids: list[int], fields: list[str]):
        return self.call_kw(model, "read", [ids], {"fields": fields})

    def write(self, model: str, ids: list[int], values: dict):
        return self.call_kw(model, "write", [ids, values])

    def create(self, model: str, values: dict):
        return self.call_kw(model, "create", [values])

    def name_search(self, model: str, name: str, args=None, operator="ilike", limit=1):
        return self.call_kw(model, "name_search", [name, args or [], operator, limit])

# ---------- MCP server ----------
mcp = FastMCP("Odoo 18 MCP Server")

# bootstrap Odoo client from env
try:
    ODOO = OdooClient(
        url=os.environ["ODOO_URL"],
        db=os.environ["ODOO_DB"],
        user=os.environ["ODOO_USER"],
        password=os.environ["ODOO_PASSWORD"],
    )
    # Test connection
    ODOO.authenticate()
    print(f"✅ Connected to Odoo: {ODOO.url}/{ODOO.db}")
except KeyError as e:
    raise RuntimeError(f"Missing required environment variable: {e}")
except Exception as e:
    print(f"❌ Failed to connect to Odoo: {e}")
    raise RuntimeError(f"Odoo connection failed: {e}")


# ----- Schemas (Pydantic models) -----
class Domain(list): ...
DEFAULT_LEAD_FIELDS = ["id","name","email_from","probability","stage_id","user_id","expected_revenue"]

class LeadSearchIn(BaseModel):
    domain: list = Field(default_factory=list, description="Odoo domain, e.g., [[\"probability\", \">=\", 50]]")
    fields: list[str] = Field(default=DEFAULT_LEAD_FIELDS, description="Whitelisted fields to return")
    limit: int = 80
    offset: int = 0
    order: str | None = None

class LeadSearchOut(BaseModel):
    count: int
    results: list[dict]

class LeadGetIn(BaseModel):
    id: int
    fields: list[str] = Field(default=DEFAULT_LEAD_FIELDS)

class LeadUpdateIn(BaseModel):
    id: int
    values: dict = Field(description="Allowed: name, probability, email_from, phone, description, user_id, stage_id")

class SaleLine(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    price: float | None = None
    discount: float | None = Field(default=None, description="0..100")

class CreateQuoteIn(BaseModel):
    lead_id: int
    partner_id: int | None = None
    pricelist_id: int | None = None
    lines: list[SaleLine]

class PurchaseLine(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    price: float | None = None

class InvoiceLine(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    price_unit: float | None = None
    name: str | None = None

# ----- Tools -----
@mcp.tool()
def crm_search_leads(params: LeadSearchIn) -> LeadSearchOut:
    """Search crm.lead using Odoo domain + fields. Use to find leads to act on."""
    try:
        res = ODOO.search_read("crm.lead", params.domain, params.fields, params.limit, params.offset, params.order)
        # count efficiently (separate search_count)
        count = ODOO.call_kw("crm.lead", "search_count", [params.domain], {})
        return LeadSearchOut(count=count, results=res)
    except Exception as e:
        raise RuntimeError(f"Failed to search leads: {e}")

@mcp.tool()
def crm_get_lead(input: LeadGetIn) -> dict:
    """Get a single lead by id."""
    if input.id <= 0:
        raise ValueError("Invalid lead ID")
    try:
        rows = ODOO.read("crm.lead", [input.id], input.fields)
        if not rows:
            raise ValueError(f"Lead {input.id} not found")
        return rows[0]
    except Exception as e:
        raise RuntimeError(f"Failed to get lead {input.id}: {e}")

@mcp.tool()
def crm_update_lead(input: LeadUpdateIn) -> dict:
    """Safely update a lead. Only allowed fields will be persisted."""
    # Add validation
    if input.id <= 0:
        raise ValueError("Invalid lead ID")
    
    allowed = {"name","probability","email_from","phone","description","user_id","stage_id"}
    values = {k:v for k,v in input.values.items() if k in allowed}
    if not values:
        raise ValueError("No allowed fields provided")
    
    # Validate probability range
    if "probability" in values and not (0 <= values["probability"] <= 100):
        raise ValueError("Probability must be between 0 and 100")
        
    try:
        ok = ODOO.write("crm.lead", [input.id], values)
        return {"updated": bool(ok), "id": input.id, "values": values}
    except Exception as e:
        return {"error": f"Failed to update lead: {e}", "id": input.id}

@mcp.tool()
def res_partner_find_or_create(name: str | None = None, email: str | None = None, phone: str | None = None) -> dict:
    """Find partner by email or name; create minimal partner if not exist."""
    if email:
        found = ODOO.search_read("res.partner", [["email","=",email]], ["id","name","email"], limit=1)
        if found:
            return {"partner_id": found[0]["id"], "created": False}
    if name:
        ns = ODOO.name_search("res.partner", name, limit=1)
        if ns:
            return {"partner_id": ns[0][0], "created": False}
    partner_id = ODOO.create("res.partner", {"name": name or email or "New Partner", "email": email, "phone": phone})
    return {"partner_id": partner_id, "created": True}

@mcp.tool()
def sale_create_quote_from_lead(input: CreateQuoteIn) -> dict:
    """Create a draft sale.order from a lead and line items."""
    if input.lead_id <= 0:
        raise ValueError("Invalid lead ID")
    if not input.lines:
        raise ValueError("At least one line item is required")
    
    try:
        lead = ODOO.read("crm.lead", [input.lead_id], ["partner_id","name"])[0]
        partner_id = input.partner_id or (lead["partner_id"][0] if lead["partner_id"] else None)
        if not partner_id:
            raise ValueError("No partner found; pass partner_id or set partner on the lead first.")
        
        order_vals = {
            "partner_id": partner_id,
            "client_order_ref": f"Lead {input.lead_id}",
            "pricelist_id": input.pricelist_id,
            "origin": lead["name"],
            "order_line": [
                (0,0,{
                    "product_id": ln.product_id,
                    "product_uom_qty": ln.qty,
                    **({"price_unit": ln.price} if ln.price is not None else {}),
                    **({"discount": ln.discount} if ln.discount is not None else {}),
                }) for ln in input.lines
            ],
        }
        order_id = ODOO.create("sale.order", order_vals)
        order = ODOO.read("sale.order", [order_id], ["id","name","amount_total"])[0]
        return order
    except Exception as e:
        raise RuntimeError(f"Failed to create quote from lead {input.lead_id}: {e}")

@mcp.tool()
def sale_confirm_order(order_id: int) -> dict:
    """Confirm a quotation (sale.order -> Sale)."""
    ODOO.call_kw("sale.order", "action_confirm", [[order_id]], {})
    state = ODOO.read("sale.order", [order_id], ["state","name"])[0]
    return {"order_id": order_id, "name": state["name"], "state": state["state"]}

@mcp.tool()
def sale_get_order(id: int | None = None, name: str | None = None) -> dict:
    """Fetch a sale.order by id or name (exact)."""
    recs = []
    if id:
        recs = ODOO.read("sale.order", [id], ["id","name","partner_id","state","amount_total"])
    elif name:
        recs = ODOO.search_read("sale.order", [["name","=",name]], ["id","name","partner_id","state","amount_total"], limit=1)
    else:
        raise ValueError("Provide id or name")
    if not recs:
        raise ValueError("Order not found")
    return recs[0]

@mcp.tool()
def stock_search_picking(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search stock pickings (transfers) with optional domain filtering."""
    domain = domain or []
    fields = fields or ["id", "name", "state", "picking_type_id", "partner_id", "scheduled_date"]
    return ODOO.search_read("stock.picking", domain, fields, limit)

@mcp.tool()
def stock_get_picking(picking_id: int) -> dict:
    """Get detailed stock picking information."""
    return ODOO.read("stock.picking", [picking_id], [
        "id", "name", "state", "picking_type_id", "partner_id", "scheduled_date",
        "move_ids", "move_line_ids", "origin", "backorder_id"
    ])[0]

@mcp.tool()
def stock_validate_picking(picking_id: int) -> dict:
    """Validate/confirm a stock picking."""
    ODOO.call_kw("stock.picking", "button_validate", [[picking_id]], {})
    return ODOO.read("stock.picking", [picking_id], ["id", "name", "state"])[0]

@mcp.tool()
def purchase_search_orders(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search purchase orders."""
    domain = domain or []
    fields = fields or ["id", "name", "state", "partner_id", "date_order", "amount_total"]
    return ODOO.search_read("purchase.order", domain, fields, limit)

@mcp.tool()
def purchase_create_order(partner_id: int, order_line: list) -> dict:
    """Create a purchase order with line items."""
    vals = {
        "partner_id": partner_id,
        "order_line": [(0, 0, line) for line in order_line]
    }
    order_id = ODOO.create("purchase.order", vals)
    return ODOO.read("purchase.order", [order_id], ["id", "name", "state", "amount_total"])[0]

@mcp.tool()
def account_search_invoices(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search account invoices (bills and invoices)."""
    domain = domain or []
    fields = fields or ["id", "name", "state", "partner_id", "invoice_date", "amount_total", "payment_state"]
    return ODOO.search_read("account.move", domain, fields, limit)

@mcp.tool()
def account_create_invoice(partner_id: int, move_type: str, invoice_line_ids: list) -> dict:
    """Create an invoice (move_type: 'out_invoice', 'out_refund', 'in_invoice', 'in_refund')."""
    vals = {
        "partner_id": partner_id,
        "move_type": move_type,
        "invoice_line_ids": [(0, 0, line) for line in invoice_line_ids]
    }
    invoice_id = ODOO.create("account.move", vals)
    return ODOO.read("account.move", [invoice_id], ["id", "name", "state", "amount_total"])[0]

@mcp.tool()
def project_search_tasks(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search project tasks."""
    domain = domain or []
    fields = fields or ["id", "name", "state", "project_id", "user_id", "date_deadline", "priority"]
    return ODOO.search_read("project.task", domain, fields, limit)

@mcp.tool()
def project_create_task(project_id: int, name: str, user_id: int = None, description: str = None) -> dict:
    """Create a new project task."""
    vals = {"project_id": project_id, "name": name}
    if user_id:
        vals["user_id"] = user_id
    if description:
        vals["description"] = description
    task_id = ODOO.create("project.task", vals)
    return ODOO.read("project.task", [task_id], ["id", "name", "state", "project_id"])[0]

@mcp.tool()
def hr_search_employees(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search HR employees."""
    domain = domain or []
    fields = fields or ["id", "name", "work_email", "department_id", "job_id", "user_id"]
    return ODOO.search_read("hr.employee", domain, fields, limit)

@mcp.tool()
def hr_create_employee(name: str, work_email: str = None, department_id: int = None) -> dict:
    """Create a new employee record."""
    vals = {"name": name}
    if work_email:
        vals["work_email"] = work_email
    if department_id:
        vals["department_id"] = department_id
    emp_id = ODOO.create("hr.employee", vals)
    return ODOO.read("hr.employee", [emp_id], ["id", "name", "work_email"])[0]

@mcp.tool()
def product_search_products(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search product templates."""
    domain = domain or []
    fields = fields or ["id", "name", "default_code", "list_price", "type", "categ_id"]
    return ODOO.search_read("product.template", domain, fields, limit)

@mcp.tool()
def product_get_product(product_id: int) -> dict:
    """Get detailed product information."""
    return ODOO.read("product.template", [product_id], [
        "id", "name", "default_code", "list_price", "standard_price", "type",
        "categ_id", "uom_id", "description", "image_1920"
    ])[0]

@mcp.tool()
def analytic_search_entries(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search analytic account entries (timesheets, expenses)."""
    domain = domain or []
    fields = fields or ["id", "name", "account_id", "date", "unit_amount", "amount", "user_id"]
    return ODOO.search_read("account.analytic.line", domain, fields, limit)

@mcp.tool()
def calendar_search_events(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search calendar events."""
    domain = domain or []
    fields = fields or ["id", "name", "start", "stop", "partner_ids", "user_id", "location"]
    return ODOO.search_read("calendar.event", domain, fields, limit)

@mcp.tool()
def calendar_create_event(name: str, start: str, stop: str, partner_ids: list = None) -> dict:
    """Create a calendar event."""
    vals = {"name": name, "start": start, "stop": stop}
    if partner_ids:
        vals["partner_ids"] = [(6, 0, partner_ids)]
    event_id = ODOO.create("calendar.event", vals)
    return ODOO.read("calendar.event", [event_id], ["id", "name", "start", "stop"])[0]

@mcp.tool()
def workflow_schedule_activity(model: str, res_id: int, activity_type_id: int, summary: str, user_id: int = None, date_deadline: str = None) -> dict:
    """Schedule an activity on any record (follow-up, call, meeting, etc.)."""
    vals = {
        "activity_type_id": activity_type_id,
        "summary": summary,
        "res_model_id": ODOO.call_kw("ir.model", "search", [[("model", "=", model)]], {})[0],
        "res_id": res_id
    }
    if user_id:
        vals["user_id"] = user_id
    if date_deadline:
        vals["date_deadline"] = date_deadline
    activity_id = ODOO.create("mail.activity", vals)
    return {"activity_id": activity_id, "scheduled": True}

@mcp.tool()
def report_get_dashboard_data(model: str, domain: list = None, group_by: str = None, measures: list = None) -> dict:
    """Get aggregated data for reporting/dashboard purposes."""
    domain = domain or []
    if group_by:
        # Use read_group for grouped data
        result = ODOO.call_kw(model, "read_group", [], {
            "domain": domain,
            "fields": measures or ["id"],
            "groupby": [group_by]
        })
        return {"grouped_data": result}
    else:
        # Simple count and basic stats
        count = ODOO.call_kw(model, "search_count", [domain], {})
        return {"count": count, "domain": domain}

@mcp.tool()
def automation_run_server_action(action_id: int, model: str, record_ids: list) -> dict:
    """Execute a server action on specified records."""
    result = ODOO.call_kw("ir.actions.server", "run", [], {
        "action_id": action_id,
        "records": ODOO.read(model, record_ids, ["id"])
    })
    return {"executed": True, "records_affected": len(record_ids)}

@mcp.tool()
def mass_mailing_create_campaign(name: str, mailing_model: str, contact_list_ids: list, subject: str, body_html: str) -> dict:
    """Create a mass mailing campaign."""
    vals = {
        "name": name,
        "mailing_model_id": ODOO.call_kw("ir.model", "search", [[("model", "=", mailing_model)]], {})[0],
        "contact_list_ids": [(6, 0, contact_list_ids)],
        "subject": subject,
        "body_html": body_html,
        "state": "draft"
    }
    mailing_id = ODOO.create("mailing.mailing", vals)
    return ODOO.read("mailing.mailing", [mailing_id], ["id", "name", "state"])[0]

@mcp.tool()
def website_search_pages(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search website pages."""
    domain = domain or []
    fields = fields or ["id", "name", "url", "website_id", "is_published"]
    return ODOO.search_read("website.page", domain, fields, limit)

@mcp.tool()
def survey_search_surveys(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search surveys."""
    domain = domain or []
    fields = fields or ["id", "title", "state", "response_count", "questions_count"]
    return ODOO.search_read("survey.survey", domain, fields, limit)

@mcp.tool()
def helpdesk_search_tickets(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search helpdesk tickets (if helpdesk module is installed)."""
    try:
        domain = domain or []
        fields = fields or ["id", "name", "partner_id", "stage_id", "user_id", "priority"]
        return ODOO.search_read("help.ticket", domain, fields, limit)
    except:
        return {"error": "Helpdesk module not installed"}

@mcp.tool()
def pos_search_orders(domain: list = None, fields: list = None, limit: int = 80) -> list:
    """Search Point of Sale orders."""
    try:
        domain = domain or []
        fields = fields or ["id", "name", "state", "partner_id", "amount_total", "date_order"]
        return ODOO.search_read("pos.order", domain, fields, limit)
    except:
        return {"error": "Point of Sale module not installed"}

@mcp.tool()
def bulk_update_records(model: str, ids: list, values: dict) -> dict:
    """Update multiple records at once with the same values."""
    allowed_models = {"crm.lead", "res.partner", "product.template", "project.task", "hr.employee"}
    if model not in allowed_models:
        raise ValueError(f"Bulk update not allowed for model: {model}")
    
    # Validate fields based on model
    allowed_fields = {
        "crm.lead": {"probability", "user_id", "stage_id", "tag_ids"},
        "res.partner": {"user_id", "category_id"},
        "product.template": {"list_price", "standard_price"},
        "project.task": {"user_id", "stage_id"},
        "hr.employee": {"department_id", "job_id"}
    }
    
    safe_values = {k: v for k, v in values.items() if k in allowed_fields.get(model, set())}
    if not safe_values:
        raise ValueError("No allowed fields provided for bulk update")
    
    result = ODOO.write(model, ids, safe_values)
    return {"updated": bool(result), "records_affected": len(ids), "values": safe_values}

@mcp.tool()
def data_export_to_csv(model: str, domain: list, fields: list, filename: str = None) -> dict:
    """Export data to CSV format (returns data, doesn't save file)."""
    records = ODOO.search_read(model, domain, fields, limit=1000)
    if not records:
        return {"data": "", "count": 0}
    
    import csv, io
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    
    return {
        "data": output.getvalue(),
        "count": len(records),
        "filename": filename or f"{model}_export.csv"
    }

@mcp.tool()
def advanced_search_with_joins(base_model: str, domain: list, joins: list, fields: list, limit: int = 80) -> list:
    """Advanced search with related field joins."""
    # This is a simplified version - in practice you'd need more complex logic
    # for handling joins across related models
    return ODOO.search_read(base_model, domain, fields, limit)

@mcp.tool()
def notification_send(model: str, res_id: int, partner_ids: list, subject: str, body: str) -> dict:
    """Send internal notification to users/partners."""
    message_vals = {
        "model": model,
        "res_id": res_id,
        "partner_ids": [(6, 0, partner_ids)],
        "subject": subject,
        "body": body,
        "message_type": "notification"
    }
    msg_id = ODOO.call_kw("mail.message", "create", [message_vals], {})
    return {"message_id": msg_id, "sent": True}

@mcp.tool()
def dashboard_get_kpis(date_from: str = None, date_to: str = None) -> dict:
    """Get key performance indicators for dashboard."""
    # This would typically aggregate data from multiple models
    kpis = {}
    
    # Sales KPIs
    try:
        sale_orders = ODOO.search_read("sale.order", 
            [["date_order", ">=", date_from], ["date_order", "<=", date_to]] if date_from and date_to else [],
            ["amount_total"], limit=10000)
        kpis["total_sales"] = sum(order["amount_total"] for order in sale_orders)
        kpis["order_count"] = len(sale_orders)
    except:
        kpis["sales_error"] = "Sales module not accessible"
    
    # CRM KPIs
    try:
        leads = ODOO.search_read("crm.lead", [], ["probability"], limit=10000)
        kpis["total_leads"] = len(leads)
        kpis["weighted_pipeline"] = sum(lead["probability"] * 100 for lead in leads if lead["probability"])
    except:
        kpis["crm_error"] = "CRM module not accessible"
    
    return kpis

@mcp.tool()
def integration_webhook_call(url: str, method: str = "POST", data: dict = None) -> dict:
    """Call external webhook/integration endpoint."""
    # Note: This should be restricted and monitored in production
    import requests
    try:
        response = requests.request(method, url, json=data or {}, timeout=30)
        return {
            "status_code": response.status_code,
            "response": response.text[:1000],  # Limit response size
            "success": response.status_code < 400
        }
    except Exception as e:
        return {"error": str(e), "success": False}

@mcp.tool()
def ai_insights_generate(model: str, record_ids: list, insight_type: str) -> dict:
    """Generate AI-powered insights for records (placeholder for ML integration)."""
    records = ODOO.read(model, record_ids, ["id", "name"])
    
    insights = []
    for record in records:
        if insight_type == "sales_prediction":
            insights.append({
                "record_id": record["id"],
                "insight": f"Predicted sales potential for {record['name']}: High",
                "confidence": 0.85
            })
        elif insight_type == "risk_assessment":
            insights.append({
                "record_id": record["id"],
                "insight": f"Risk assessment for {record['name']}: Low risk",
                "score": 0.2
            })
    
    return {"insights": insights, "model": model, "type": insight_type}

# ----- Resources (read-only context) -----
@mcp.resource("odoo://schemas/lead.json")
def lead_schema() -> bytes:
    """JSON Schema for safe lead fields (used by clients for form-filling / validation)."""
    schema = {
        "$schema":"https://json-schema.org/draft/2020-12/schema",
        "title":"crm.lead (safe subset)",
        "type":"object",
        "properties":{
            "name":{"type":"string"},
            "email_from":{"type":"string","format":"email"},
            "probability":{"type":"number","minimum":0,"maximum":100},
            "user_id":{"type":["integer","null"]},
            "stage_id":{"type":["integer","null"]},
            "expected_revenue":{"type":["number","null"]}
        },
        "additionalProperties": False
    }
    return json.dumps(schema, ensure_ascii=False, indent=2).encode("utf-8")

@mcp.resource("odoo://schemas/sale_order.json")
def sale_order_schema() -> bytes:
    """JSON Schema for sale order operations."""
    schema = {
        "$schema":"https://json-schema.org/draft/2020-12/schema",
        "title":"sale.order schema",
        "type":"object",
        "properties":{
            "partner_id":{"type":"integer"},
            "pricelist_id":{"type":["integer","null"]},
            "order_line":{"type":"array","items":{"type":"object"}}
        }
    }
    return json.dumps(schema, ensure_ascii=False, indent=2).encode("utf-8")

@mcp.resource("odoo://capabilities/inventory.json")
def inventory_capabilities() -> bytes:
    """List available inventory/stock management capabilities."""
    caps = {
        "models": ["stock.picking", "stock.move", "product.product", "stock.quant"],
        "operations": ["search", "read", "validate", "transfer"],
        "features": ["real_time_stock", "lot_tracking", "serial_numbers"]
    }
    return json.dumps(caps, ensure_ascii=False, indent=2).encode("utf-8")

@mcp.resource("odoo://capabilities/finance.json")
def finance_capabilities() -> bytes:
    """List available financial management capabilities."""
    caps = {
        "models": ["account.move", "account.invoice", "account.payment", "account.journal"],
        "operations": ["create_invoice", "record_payment", "reconcile", "financial_reports"],
        "features": ["multi_currency", "tax_calculation", "payment_terms"]
    }
    return json.dumps(caps, ensure_ascii=False, indent=2).encode("utf-8")

# ----- Prompts (templates the client can fetch) -----
@mcp.prompt("sales/follow_up_email")
def prompt_follow_up_email() -> list[dict]:
    """Prompt template to draft a follow-up email for a lead (pass {lead_json})."""
    return [
        {"role":"system","content":"You are a sales assistant. Write a concise, helpful email."},
        {"role":"user","content":(
            "Lead details (JSON): {{lead_json}}\n\n"
            "Write a friendly follow-up email in Arabic and English, with:\n"
            "- 2 subject line options\n- a short body\n- a clear CTA\n"
        )}
    ]

@mcp.prompt("business/report_generation")
def prompt_business_report() -> list[dict]:
    """Prompt template for generating business reports."""
    return [
        {"role":"system","content":"You are a business analyst. Generate insightful reports from Odoo data."},
        {"role":"user","content":(
            "Generate a business report using the following data: {{data_json}}\n\n"
            "Include:\n"
            "- Executive summary\n- Key metrics\n- Trends analysis\n- Recommendations\n"
            "Format as a professional business report."
        )}
    ]

@mcp.prompt("crm/lead_qualification")
def prompt_lead_qualification() -> list[dict]:
    """Prompt template for lead qualification assessment."""
    return [
        {"role":"system","content":"You are a sales qualification expert. Assess lead quality and next steps."},
        {"role":"user","content":(
            "Assess this lead for qualification: {{lead_json}}\n\n"
            "Evaluate:\n"
            "- BANT criteria (Budget, Authority, Need, Timeline)\n- Lead score (1-10)\n- Recommended next action\n- Expected close probability"
        )}
    ]

@mcp.prompt("inventory/stock_analysis")
def prompt_stock_analysis() -> list[dict]:
    """Prompt template for inventory and stock analysis."""
    return [
        {"role":"system","content":"You are an inventory management expert. Analyze stock levels and recommend actions."},
        {"role":"user","content":(
            "Analyze this inventory data: {{inventory_json}}\n\n"
            "Provide:\n"
            "- Stock level assessment\n- Reorder recommendations\n- Slow-moving items\n- Optimization suggestions"
        )}
    ]

@mcp.prompt("finance/payment_reminder")
def prompt_payment_reminder() -> list[dict]:
    """Prompt template for payment reminder emails."""
    return [
        {"role":"system","content":"You are a collections specialist. Write professional payment reminders."},
        {"role":"user","content":(
            "Invoice details: {{invoice_json}}\n\n"
            "Write a payment reminder email that includes:\n"
            "- Polite but firm tone\n- Invoice details\n- Payment terms\n- Consequences of non-payment\n- Contact information"
        )}
    ]

if __name__ == "__main__":
    # Run as: python odoo_mcp_server.py stdio
    import sys
    mcp.run(sys.argv[1] if len(sys.argv) > 1 else "stdio")
