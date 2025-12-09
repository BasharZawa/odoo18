from odoo import models, fields


class CrmTag(models.Model):
    _inherit = 'crm.tag'

    is_pilot_approval = fields.Boolean(
        string='Is Pilot Approval',
        help='Indicates if this tag is used for pilot order approvals'
    )
