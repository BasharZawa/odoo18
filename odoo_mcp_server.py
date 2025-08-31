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
def mail_message_post(model: str, res_id: int, body_markdown: str) -> dict:
    """Post a note to chatter on crm.lead or sale.order."""
    if model not in {"crm.lead","sale.order"}:
        raise ValueError("model must be crm.lead or sale.order")
    msg_id = ODOO.call_kw(model, "message_post", [[res_id]], {"body": body_markdown})
    return {"message_id": msg_id}

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

if __name__ == "__main__":
    # Run as: python odoo_mcp_server.py stdio
    import sys
    mcp.run(sys.argv[1] if len(sys.argv) > 1 else "stdio")
