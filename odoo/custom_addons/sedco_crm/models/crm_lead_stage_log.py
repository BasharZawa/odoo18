# -*- coding: utf-8 -*-
# Stage change audit trail for crm.lead
from odoo import fields, models

class SedcoCrmLeadStageLog(models.Model):
    _name = "sedco.crm.lead.stage.log"
    _description = "Lead Stage Log"
    _order = "changed_on desc, id desc"

    # Link back to the lead (cascade delete to keep data tidy if lead removed)
    lead_id = fields.Many2one("crm.lead", required=True, ondelete="cascade")
    # Who changed the stage
    changed_by = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    # When it was changed
    changed_on = fields.Datetime(required=True, default=fields.Datetime.now)
    # To which stage
    stage_id = fields.Many2one("crm.stage", required=True)
