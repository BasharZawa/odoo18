from odoo import models, fields


class ProductLineEpt(models.Model):
    _name = "product.line.ept"
    _description = "Product Line"

    name = fields.Char(string="Product Line", required=True)
