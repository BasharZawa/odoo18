from odoo import models, fields


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    presales_request_id = fields.Many2one(
        'presales.request',
        string='Presales Request',
        help='Presales request this timesheet entry is linked to'
    )
