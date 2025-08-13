# -*- coding: utf-8 -*-
# Extends crm.team with a priority used when multiple teams match a lead's domain.
from odoo import fields, models

class CrmTeam(models.Model):
    _inherit = "crm.team"

    # Lower number = higher priority.
    # This lets admins resolve overlaps entirely from the UI.
    sedco_assignment_priority = fields.Integer(
        string="Assignment Priority",
        help="Lower value = higher priority when multiple teams match the same lead.",
    )
