from odoo import models, fields


class ProductLine(models.Model):
    _name = 'product.line'
    _description = 'Product Line'

    name = fields.Char(string='Product Line', required=True)
    description = fields.Text(string='Description')
