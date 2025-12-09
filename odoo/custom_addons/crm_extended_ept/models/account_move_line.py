
from odoo import models, fields


class AccountMoveLineExtended(models.Model):
    _inherit = "account.move.line"

    model_number = fields.Char(string="Model Number", related="product_id.model_number")
    product_line_id = fields.Many2one(comodel_name="product.line.ept", store=True,
                                      related="product_id.product_line_id")
    product_nature_id = fields.Many2one(comodel_name="product.nature.ept", store=True,
                                        related="product_id.product_nature_id")
