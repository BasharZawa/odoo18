from odoo import models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for picking in self:
            if picking.picking_type_code != "incoming":
                continue

            # Total expected serials based on move quantities
            total_expected = sum(picking.move_ids.filtered(
                lambda m: m.product_id.tracking == 'serial'
            ).mapped('product_uom_qty'))

            if total_expected == 0:
                continue

            inspected = self.env["quality.check"].search_count([
                ("picking_id", "=", picking.id),
                ("quality_state", "!=", "none"),
            ])

            if inspected < int(total_expected):
                raise UserError(
                    "لا يمكن اعتماد الاستلام قبل فحص جميع Serial Numbers (%s/%s)" % (inspected, int(total_expected))
                )

        return super().button_validate()
