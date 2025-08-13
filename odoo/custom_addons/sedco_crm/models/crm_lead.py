# -*- coding: utf-8 -*-
# CRM lead lifecycle extensions for Odoo 18.
# Focus:
#  - Classification (product category, service flag, origin)
#  - Partner handoff, postponement
#  - Disqualification with reason/comment
#  - Stage logging on change
#  - SLA/escalation cron
from datetime import timedelta
from odoo import api, fields, models, _

class CrmLead(models.Model):
    _inherit = "crm.lead"

    # Classification: drive routing/analytics
    product_category_id = fields.Many2one("product.category", string="Product Category")
    is_service = fields.Boolean("Is Service")
    origin_type = fields.Selection([
        ("email_reply", "Email Reply"),
        ("web_form", "Web Form"),
        ("manual", "Manual"),
        ("api", "API"),
    ], string="Origin Type")

    # Partner handoff (channel to partner/reseller/distributor)
    forwarded_partner_id = fields.Many2one("res.partner", string="Forwarded to Partner")

    # Postponement window (pauses SLA escalations while in future)
    postponed_until = fields.Date("Postponed Until")

    # Disqualification metadata
    disqual_reason = fields.Selection([
        ("not_reachable", "Not reachable"),
        ("duplicate", "Duplicate lead"),
        ("no_interest", "No longer interested"),
        ("not_a_lead", "Not a lead"),
        ("closed_by_system", "Closed by system"),
    ], string="Disqualification Reason")
    disqual_comment = fields.Text("Why not lead")

    # Stage change audit
    stage_log_ids = fields.One2many("sedco.crm.lead.stage.log", "lead_id", string="Stage Log")

    @api.model_create_multi
    def create(self, vals_list):
        # Create normally first, so we get IDs and default values (team/owner may be set by other modules).
        leads = super().create(vals_list)

        # Example: best-effort origin inference (non-invasive; safe to keep)
        for lead in leads:
            if not lead.origin_type:
                # If created via web controller, context may include website info, but we keep it simple
                # and leave origin_type empty unless explicitly set by the intake point.
                pass
        return leads

    def write(self, vals):
        # Intercept stage change to log it after the write.
        stage_changed = "stage_id" in vals
        res = super().write(vals)
        if stage_changed:
            for lead in self:
                self.env["sedco.crm.lead.stage.log"].create({
                    "lead_id": lead.id,
                    "changed_by": self.env.user.id,
                    "changed_on": fields.Datetime.now(),
                    "stage_id": lead.stage_id.id,
                })
        return res

    # SLA & Escalation engine (daily cron)
    def _sedco_run_lead_sla(self):
        today = fields.Date.today()
        # Thresholds relative to create_date
        contact_limit = today - timedelta(days=3)
        mgr_limit = today - timedelta(days=5)
        final_limit = today - timedelta(days=7)
        disq_limit = today - timedelta(days=10)

        def is_in_scope(l):
            # Only early stages, not postponed into the future.
            return (l.type == "lead"
                    and l.stage_id
                    and l.stage_id.name in ("New")
                    and (not l.postponed_until or l.postponed_until <= today))

        leads = self.search([("type", "=", "lead")])
        leads = leads.filtered(is_in_scope)

        # Day 3: notify owner to contact
        for lead in leads.filtered(lambda l: l.create_date and l.create_date.date() <= contact_limit):
            if lead.user_id:
                lead.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=lead.user_id.id,
                    summary=_("Contact your lead"),
                    note=_("Auto reminder: please move to Contacted within 3 days."),
                )

        # Day 5: escalate to team leader if any
        for lead in leads.filtered(lambda l: l.create_date and l.create_date.date() <= mgr_limit and l.team_id and l.team_id.user_id):
            lead.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=lead.team_id.user_id.id,
                summary=_("Escalation: Lead not contacted"),
                note=_("Lead still not contacted after 5 days."),
            )

        # Day 7: final warning to owner
        for lead in leads.filtered(lambda l: l.create_date and l.create_date.date() <= final_limit):
            if lead.user_id:
                lead.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=lead.user_id.id,
                    summary=_("Final warning"),
                    note=_("Lead will be auto-disqualified on day 10 if not contacted."),
                )

        # Day 10: auto-disqualify as Not Reachable
        to_close = leads.filtered(lambda l: l.create_date and l.create_date.date() <= disq_limit)
        if to_close:
            to_close.write({
                "disqual_reason": "not_reachable",
                "disqual_comment": _("Auto-closed by SLA at day 10"),
                "stage_id": self.env.ref("sedco_crm.stage_disqualified").id,
            })

    # Convenience actions you may call from server actions or buttons (kept simple)
    def action_forward_to_partner(self):
        """Move lead to 'Forwarded to Partner' and schedule follow-ups at +10 and +20 days.
        Auto-close at +30 if still untouched can be implemented by another cron if desired.
        """
        forwarded_stage = self.env.ref("sedco_crm.stage_forwarded", raise_if_not_found=False)
        for lead in self:
            if forwarded_stage:
                lead.stage_id = forwarded_stage.id
            # Follow-up activities to ensure partner handoff is monitored
            if lead.user_id:
                lead.activity_schedule("mail.mail_activity_data_todo",
                                       user_id=lead.user_id.id,
                                       summary=_("Partner follow-up (10 days)"),
                                       date_deadline=fields.Date.today() + timedelta(days=10))
                lead.activity_schedule("mail.mail_activity_data_todo",
                                       user_id=lead.user_id.id,
                                       summary=_("Partner follow-up (20 days)"),
                                       date_deadline=fields.Date.today() + timedelta(days=20))
