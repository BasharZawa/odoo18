# sedco_crm_assignment_domain_bridge

**Purpose**
- At lead creation, assign `team_id` by evaluating each active Sales Team's `assignment_domain`
  (configured in UI via "Assignment Rules → Edit Domain").
- If multiple teams match, pick the one with the lowest `sedco_assignment_priority` (then lowest id).

**What this addon does _not_ do**
- It does **not** assign the salesperson. Keep using Odoo's native Rule-based Assignment, or
  install the optional `sedco_crm_instant_member_assignment` addon.

**Key files**
- `models/crm_lead.py`: create() hook + post-hook.
- `models/crm_team.py`: adds `sedco_assignment_priority` integer.
- `views/crm_team_views.xml`: exposes the priority on form & list views.
