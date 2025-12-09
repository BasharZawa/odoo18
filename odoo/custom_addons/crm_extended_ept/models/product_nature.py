from odoo import models, fields


class ProductNatureEpt(models.Model):
    _name = "product.nature.ept"
    _description = "Product Nature"

    name = fields.Char(string="Product Nature", required=True)
