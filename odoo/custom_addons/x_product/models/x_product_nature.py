from odoo import models, fields


class XProductNature(models.Model):
    _name = 'x.product.nature'
    _description = 'Product Nature'

    name = fields.Char(string='Product Nature', required=True)
    description = fields.Text(string='Description')
    x_product_ids = fields.One2many('product.template', 'x_product_nature_id', string='Products')
