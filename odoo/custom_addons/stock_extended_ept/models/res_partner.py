# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartnerExtended(models.Model):
    _inherit = 'res.partner'

    is_special_customer = fields.Boolean(string="Is Special Customer",
                                         help="Indicates whether the partner is a special customer.")
    header_img = fields.Binary(string="Document Header Image",
                               help="This image will be displayed in the header of the documents.")
    footer_img = fields.Binary(string="Document Footer Image",
                               help="This image will be displayed in the footer of the documents.")
