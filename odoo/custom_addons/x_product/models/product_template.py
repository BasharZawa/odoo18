# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_line_id = fields.Many2one('product.line', string='Product Line')
    product_nature_id = fields.Many2one('product.nature', string='Product Nature')
    hs_code = fields.Char(string='HS Code')
    coo = fields.Many2one('res.country',string='Country of Origin')
    model_number = fields.Char(string='Model Number')