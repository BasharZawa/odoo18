# -*- coding: utf-8 -*-
# Main CRM extension module for SEDCO on Odoo 18.
{
    "name": "SEDCO CRM",
    "version": "18.0.1.0.0",
    "summary": "Lead lifecycle extensions: fields, stage logging, postponement, partner handoff, SLA.",
    "author": "SEDCO / Implementation",
    "license": "OPL-1",
    "depends": ["crm", "mail", "utm"],
    "data": [
        "security/ir.model.access.csv",
        "data/crm_stage.xml",
        "data/ir_cron.xml",
        "views/crm_lead_views.xml",
    ],
    "installable": True,
    "application": False,
}
