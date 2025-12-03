from odoo import models, fields


class XProductNature(models.Model):
    _name = 'product.nature'
    _description = 'Product Nature'

    name = fields.Char(string='Product Nature', required=True)
    description = fields.Text(string='Description')
    product_ids = fields.One2many('product.template', 'product_nature_id', string='Products')
