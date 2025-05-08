from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    city = fields.Many2one('ir.city', string='City', ondelete='restrict')