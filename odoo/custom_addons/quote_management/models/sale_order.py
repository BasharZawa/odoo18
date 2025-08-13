from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    incoterm_location = fields.Char(string="Incoterm Location")
    warranty_months = fields.Integer(string="Warranty (Months)")
    delivery_time = fields.Text(string="Delivery Time")
    revised_from_id = fields.Many2one('sale.order', string='Revised From')

    def write(self, vals):
        for order in self:
            if order.state == 'sent':
                raise UserError("You cannot modify a quotation that has been sent.")
        return super().write(vals)

    def unlink(self):
        for order in self:
            if order.state == 'sent':
                raise UserError("You cannot delete a quotation that has been sent.")
        return super().unlink()

    def action_create_revision(self):
        self.ensure_one()
        new_quotation = self.copy({
            'state': 'draft',
            'revised_from_id': self.id,
            'name': f"{self.name or ''} (Rev)",
        })
        # Note: order_line is automatically copied by the copy() method
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': new_quotation.id,
            'target': 'current',
        }

    def action_confirm(self):
        for order in self:
            for line in order.order_line:
                if line.approval_required and not line.approved_by_manager:
                    raise UserError(f"Discount for product '{line.product_id.display_name}' exceeds the allowed limit and requires manager approval.")
        return super().action_confirm()
