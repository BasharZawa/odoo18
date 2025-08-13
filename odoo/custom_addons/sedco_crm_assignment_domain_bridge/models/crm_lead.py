# -*- coding: utf-8 -*-
# Hook lead creation to instantly set team_id using Sales Team assignment_domain (UI-configured).
# Notes:
#   - We only assign team_id here; salesperson assignment stays with Odoo's native scheduler.
#   - We call a post-hook '_sedco_after_team_assignment' so another addon can optionally
#     implement instant salesperson assignment without touching this module.
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

class CrmLead(models.Model):
    _inherit = "crm.lead"

    # Optional helper if you route by product category from forms/API.
    # If unused, it remains harmless.
    product_category_id = fields.Many2one("product.category", string="Product Category")

    @api.model_create_multi
    def create(self, vals_list):
        # 1) Create leads using standard logic first.
        leads = super().create(vals_list)

        # 2) Compute team assignment for each lead based on teams' assignment_domain.
        Team = self.env["crm.team"].sudo()

        # Preload all active teams once; if you use multi-company, we filter per lead below.
        all_teams = Team.search([("active", "=", True)])

        for lead in leads:
            # Skip if team_id is already set (e.g., by alias defaults or API explicitly)
            if lead.team_id:
                continue

            # Scope teams by company: team.company_id == lead.company_id OR team is global (company_id = False)
            candidate_teams = all_teams.filtered(
                lambda t: (not t.company_id) or (t.company_id == lead.company_id)
            )

            matched = []
            for t in candidate_teams:
                domain = []
                # Safely evaluate the team's assignment_domain string into a proper domain list.
                # If invalid, ignore that team silently to avoid breaking lead creation.
                if "assignment_domain" in t._fields and t.assignment_domain:
                    try:
                        domain = safe_eval(t.assignment_domain)
                    except Exception:
                        domain = []
                # We check if THIS lead matches the team's domain by searching for itself + domain.
                # Using search_count ensures the domain is evaluated consistently by ORM.
                if self.search_count([("id", "=", lead.id)] + (domain or [])):
                    matched.append(t)

            if matched:
                # Deterministic pick: by 'sedco_assignment_priority' ascending, then by id ascending.
                matched.sort(key=lambda r: (r.sedco_assignment_priority or 1000, r.id))
                lead.team_id = matched[0].id

        # 3) Optional post-hook: no-op here, overridden by the instant member assignment addon.
        self._sedco_after_team_assignment(leads)
        return leads

    def _sedco_after_team_assignment(self, leads):
        """Extension hook.
        This method does nothing here. Another addon may override it to perform
        instant salesperson assignment (e.g., round-robin) after team_id is set.
        """
        return None
