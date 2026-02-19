from odoo import fields, models


class PurchaseOrderChangeWizard(models.TransientModel):
    _name = 'purchase.order.change.wizard'
    _description = 'Purchase Order Change Wizard'

    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', required=True)
    new_name = fields.Char(string='New Purchase Order Reference', required=True)

    def action_apply(self):
        self.ensure_one()
        self.purchase_id.force_set_name(self.new_name)
        return {'type': 'ir.actions.act_window_close'}
