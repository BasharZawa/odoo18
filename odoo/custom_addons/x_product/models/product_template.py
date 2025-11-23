# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_product_line_id = fields.Many2one('x.product.line', string='Product Line')
    x_product_nature_id = fields.Many2one('x.product.nature', string='Product Nature')
    x_hs_code = fields.Char(string='HS Code')
    x_coo = fields.Many2one('res.country',string='Country of Origin')