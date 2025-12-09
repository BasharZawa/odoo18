# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompanyExtended(models.Model):
    _inherit = "res.company"

    header_img = fields.Binary(string="Invoice Header Image",
                               help="This image will be displayed in the header of the invoices.")
    street_arabic = fields.Char(string="Street Arabic")
    street2_arabic = fields.Char(string="Street2 Arabic")
    fax = fields.Char(string="Fax")
