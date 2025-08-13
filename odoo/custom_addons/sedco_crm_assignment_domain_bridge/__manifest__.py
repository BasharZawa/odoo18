# -*- coding: utf-8 -*-
# Manifest for Odoo 18 addon: sedco_crm_assignment_domain_bridge
# Purpose:
#   - Instantly assign Sales Team on lead creation using each team's assignment_domain (configured in UI)
#   - Keep logic source-agnostic (email replies, forms, API)
#   - Add a UI field "Assignment Priority" on Sales Team to resolve overlaps
{
    "name": "SEDCO CRM: Assignment Domain Bridge",
    "version": "18.0.1.0.0",
    "summary": "Assign team on lead create using Sales Team assignment_domain, UI-configurable.",
    "author": "SEDCO / Implementation",
    "license": "OPL-1",
    "depends": ["crm"],
    "data": [
        # Views to expose Assignment Priority on Sales Teams (form + list)
        "views/crm_team_views.xml",
        # Access CSV kept minimal; no new models here.
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
}
