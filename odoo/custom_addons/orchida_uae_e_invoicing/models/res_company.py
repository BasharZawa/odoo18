from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    tin = fields.Char(string="TIN")
    internal_code = fields.Char(string="Internal Code")