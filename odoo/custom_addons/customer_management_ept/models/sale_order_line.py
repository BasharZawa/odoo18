from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    special_price_flag = fields.Boolean(
        string="Special Price",
        compute="_compute_special_price_flag",
        store=True,
        help="Indicates if the line has special pricing applied",
    )

    @api.depends('product_id', 'price_unit')
    def _compute_special_price_flag(self):
        for line in self:
            if line.product_id and line.price_unit:
                line.special_price_flag = line.price_unit != line.product_id.lst_price
