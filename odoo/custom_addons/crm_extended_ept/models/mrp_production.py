
from odoo import models, fields


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    model_number = fields.Char(string="Model Number", related="product_id.model_number")
