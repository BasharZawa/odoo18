#!/usr/bin/env python3
"""
Custom MCP Tools - Development Workspace

Add your custom tools here and test them before adding to the main server.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

# Import from main server
import sys
sys.path.insert(0, '/home/bashar/odoo18')
from odoo_mcp_server import mcp, ODOO


# ============================================================================
# EXAMPLE 1: Custom Search with Advanced Filters
# ============================================================================

class AdvancedLeadSearchInput(BaseModel):
    """Advanced lead search with multiple filters"""
    min_probability: int = Field(default=0, ge=0, le=100)
    max_probability: int = Field(default=100, ge=0, le=100)
    min_revenue: float = Field(default=0, ge=0)
    stage_names: Optional[List[str]] = Field(default=None)
    team_id: Optional[int] = None
    limit: int = Field(default=20, le=100)

@mcp.tool()
def advanced_lead_search(input: AdvancedLeadSearchInput) -> dict:
    """
    Advanced CRM lead search with multiple filter options.
    Use this when you need to search leads with complex criteria.
    """
    domain = [
        ["probability", ">=", input.min_probability],
        ["probability", "<=", input.max_probability],
        ["expected_revenue", ">=", input.min_revenue]
    ]

    if input.team_id:
        domain.append(["team_id", "=", input.team_id])

    if input.stage_names:
        domain.append(["stage_id.name", "in", input.stage_names])

    results = ODOO.search_read(
        "crm.lead",
        domain,
        ["id", "name", "partner_name", "probability", "expected_revenue", "stage_id"],
        limit=input.limit
    )

    total_revenue = sum(lead.get("expected_revenue", 0) for lead in results)

    return {
        "leads": results,
        "count": len(results),
        "total_expected_revenue": total_revenue,
        "filters_applied": {
            "probability_range": [input.min_probability, input.max_probability],
            "min_revenue": input.min_revenue,
            "stages": input.stage_names
        }
    }


# ============================================================================
# EXAMPLE 2: Sales Performance Analytics
# ============================================================================

class SalesPerformanceInput(BaseModel):
    """Input for sales performance analysis"""
    salesperson_id: Optional[int] = None
    team_id: Optional[int] = None
    date_from: str = Field(description="Start date YYYY-MM-DD")
    date_to: str = Field(description="End date YYYY-MM-DD")

@mcp.tool()
def analyze_sales_performance(input: SalesPerformanceInput) -> dict:
    """
    Analyze sales performance for a salesperson or team.
    Returns win rates, conversion metrics, and revenue statistics.
    """
    domain = [
        ["date_order", ">=", input.date_from],
        ["date_order", "<=", input.date_to]
    ]

    if input.salesperson_id:
        domain.append(["user_id", "=", input.salesperson_id])
    if input.team_id:
        domain.append(["team_id", "=", input.team_id])

    # Get all leads in period
    all_leads = ODOO.search_read(
        "crm.lead",
        domain,
        ["id", "name", "probability", "expected_revenue", "stage_id", "won_status"]
    )

    # Get confirmed orders
    won_leads = [l for l in all_leads if l.get("won_status") == "won"]

    # Calculate metrics
    total_leads = len(all_leads)
    total_won = len(won_leads)
    win_rate = (total_won / total_leads * 100) if total_leads > 0 else 0

    total_revenue = sum(lead.get("expected_revenue", 0) for lead in won_leads)
    avg_deal_size = (total_revenue / total_won) if total_won > 0 else 0

    return {
        "period": {"from": input.date_from, "to": input.date_to},
        "metrics": {
            "total_leads": total_leads,
            "won_leads": total_won,
            "lost_leads": total_leads - total_won,
            "win_rate_percent": round(win_rate, 2),
            "total_revenue": round(total_revenue, 2),
            "average_deal_size": round(avg_deal_size, 2)
        },
        "top_deals": sorted(
            won_leads,
            key=lambda x: x.get("expected_revenue", 0),
            reverse=True
        )[:5]
    }


# ============================================================================
# EXAMPLE 3: Automated Task Creation
# ============================================================================

class AutoTaskInput(BaseModel):
    """Input for automated task creation"""
    lead_id: int = Field(gt=0)
    task_type: str = Field(description="follow_up, demo, proposal, or meeting")
    days_from_now: int = Field(default=7, ge=1, le=90)
    assign_to_lead_owner: bool = Field(default=True)

@mcp.tool()
def create_automated_task(input: AutoTaskInput) -> dict:
    """
    Automatically create a task/activity for a lead.
    Useful for scheduling follow-ups, demos, or meetings.
    """
    from datetime import datetime, timedelta

    # Get lead info
    lead = ODOO.read(
        "crm.lead",
        [input.lead_id],
        ["name", "user_id", "partner_id"]
    )[0]

    # Task templates
    task_templates = {
        "follow_up": {
            "name": f"Follow up: {lead['name']}",
            "description": "Check in with customer about their interest"
        },
        "demo": {
            "name": f"Product Demo: {lead['name']}",
            "description": "Schedule and conduct product demonstration"
        },
        "proposal": {
            "name": f"Send Proposal: {lead['name']}",
            "description": "Prepare and send proposal/quotation"
        },
        "meeting": {
            "name": f"Meeting: {lead['name']}",
            "description": "Schedule meeting to discuss requirements"
        }
    }

    if input.task_type not in task_templates:
        raise ValueError(f"Invalid task_type. Must be one of: {list(task_templates.keys())}")

    template = task_templates[input.task_type]

    # Calculate deadline
    deadline = (datetime.now() + timedelta(days=input.days_from_now)).strftime("%Y-%m-%d")

    # Get activity type ID
    activity_type = ODOO.search_read(
        "mail.activity.type",
        [["name", "ilike", "todo"]],
        ["id"],
        limit=1
    )[0]

    # Determine assignee
    user_id = lead["user_id"][0] if (input.assign_to_lead_owner and lead["user_id"]) else None

    # Create activity
    activity_id = ODOO.create("mail.activity", {
        "res_model_id": ODOO.call_kw("ir.model", "search", [[("model", "=", "crm.lead")]], {})[0],
        "res_id": input.lead_id,
        "activity_type_id": activity_type["id"],
        "user_id": user_id,
        "date_deadline": deadline,
        "summary": template["name"],
        "note": template["description"]
    })

    return {
        "activity_id": activity_id,
        "lead_name": lead["name"],
        "task_type": input.task_type,
        "deadline": deadline,
        "assigned_to": user_id,
        "created": True
    }


# ============================================================================
# EXAMPLE 4: Product Recommendations
# ============================================================================

class ProductRecommendationInput(BaseModel):
    """Input for product recommendations"""
    customer_id: int = Field(gt=0)
    category_id: Optional[int] = None
    max_price: Optional[float] = None
    limit: int = Field(default=5, le=20)

@mcp.tool()
def recommend_products(input: ProductRecommendationInput) -> dict:
    """
    Recommend products to a customer based on their purchase history
    and preferences.
    """
    # Get customer's past orders
    past_orders = ODOO.search_read(
        "sale.order",
        [
            ["partner_id", "=", input.customer_id],
            ["state", "in", ["sale", "done"]]
        ],
        ["order_line"],
        limit=10
    )

    # Get purchased product categories
    purchased_categories = set()
    for order in past_orders:
        # This is simplified - in reality you'd need to read order lines
        pass

    # Build product search domain
    domain = [["sale_ok", "=", True]]

    if input.category_id:
        domain.append(["categ_id", "=", input.category_id])
    if input.max_price:
        domain.append(["list_price", "<=", input.max_price])

    # Search products
    products = ODOO.search_read(
        "product.template",
        domain,
        ["id", "name", "list_price", "categ_id", "description_sale"],
        limit=input.limit
    )

    return {
        "customer_id": input.customer_id,
        "recommendations": products,
        "count": len(products),
        "based_on": f"{len(past_orders)} past orders"
    }


# ============================================================================
# Add your own custom tools below
# ============================================================================

# TODO: Add your custom tool here
# @mcp.tool()
# def my_custom_tool(input: MyInput) -> MyOutput:
#     """Description"""
#     pass


if __name__ == "__main__":
    print("Custom MCP Tools loaded")
    print(f"Available custom tools: {len([advanced_lead_search, analyze_sales_performance, create_automated_task, recommend_products])}")
