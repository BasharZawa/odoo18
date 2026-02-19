from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def force_set_name(self, new_name):
        self.ensure_one()
        self.sudo().write({'name': new_name})
        return True
