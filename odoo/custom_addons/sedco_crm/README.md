# sedco_crm

Core CRM extensions for Odoo 18 used by SEDCO.

## Scope
- Extend `crm.lead` with:
  - Classification fields (product category, is_service, origin_type)
  - Partner handoff: `forwarded_partner_id`
  - Postponement: `postponed_until`
  - Disqualification: `disqual_reason`, `disqual_comment`
  - Stage change logging: `stage_log_ids`
- SLA & escalation cron:
  - Day 3: remind owner to contact
  - Day 5: escalate to team leader
  - Day 7: final warning
  - Day 10: auto-disqualify as Not Reachable
- Standard views (list/form) updated with new fields (using <list>, not <tree>).
- Stages seeded: Prospect, New, Contacted, Postponed, Forwarded to Partner, Qualified, Disqualified.

## Out of scope
- Team or salesperson assignment (kept in `sedco_crm_assignment_domain_bridge` and optional instant module).

## Notes
- All code commented for maintainability.
