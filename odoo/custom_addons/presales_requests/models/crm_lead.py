from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    presales_request_ids = fields.One2many(
        'presales.request',
        'opportunity_id',
        string='Presales Requests',
        help='Presales requests linked to this opportunity'
    )
