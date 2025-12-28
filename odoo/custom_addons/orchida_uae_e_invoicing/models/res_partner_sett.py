from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'




    tin = fields.Char(string="TIN")
    internal_code = fields.Char(string="Internal Code")




