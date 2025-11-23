from odoo import models, fields


class XProductLine(models.Model):
    _name = 'x.product.line'
    _description = 'Product Line'

    name = fields.Char(string='Product Line', required=True)
    description = fields.Text(string='Description')
    x_product_ids = fields.One2many('product.template', 'x_product_line_id', string='Products')    
