from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    below_cost = fields.Boolean(string='Below Cost', compute='_compute_below_cost', store=True, copy=False)

    @api.depends('price_unit', 'discount', 'product_id', 'product_uom_qty')
    def _compute_below_cost(self):
        for line in self:
            line_disc_prod = self.company_id.sale_discount_product_id
            if not line.product_id or line.display_type or line.is_delivery or (
                    line_disc_prod and line.product_id == line_disc_prod):
                line.below_cost = False
                continue
            if line.discount:
                unit_price = line.price_unit * (1.0 - (line.discount / 100.0))
            else:
                unit_price = line.price_unit
            cost = line.product_id.standard_price
            line.below_cost = unit_price < cost - 1e-6

    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        # Trigger below-cost check only when price changes and it's not a delivery line
        if 'price_unit' in vals:
            for line in self:
                if not line.is_delivery:
                    order = line.order_id
                    if order:
                        # Reset approval flag
                        order.write({'has_below_cost_approved': False})
                        # Trigger approval wizard silently
                        order.with_context(no_open_wizard=True)._action_open_below_cost_wizard()
        return res
