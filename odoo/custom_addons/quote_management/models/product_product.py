from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    quote_description = fields.Text(string='Quote Description')
    product_nature = fields.Selection([
        ('hardware', 'Hardware'),
        ('software', 'Software'),
        ('service', 'Service'),
    ], string='Product Nature', help="Nature of the product for discount approval purposes")
    