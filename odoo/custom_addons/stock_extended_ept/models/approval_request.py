# -*- coding: utf-8 -*-

from odoo import models, fields


class ApprovalRequest(models.Model):
    """
    Add fields for Inventory Adjustment approval functionality
    """
    _inherit = 'approval.request'

    has_adjustment_product = fields.Selection(related='category_id.has_adjustment_product')
    has_adjustment_location = fields.Selection(related='category_id.has_adjustment_location')
    stock_quant_product_id = fields.Many2one(comodel_name='product.product', string="Adjustment Product")
    stock_quant_location_id = fields.Many2one(comodel_name='stock.location', string="Adjustment Location")

    def action_approve(self, approver=None):
        """
        Approve the inventory adjustment request:
        - Updates the related stock.quant with the approved quantity.
        - Applies the inventory adjustment.
        """
        res = super().action_approve()
        for approval in self:
            if approval.category_id == self.env.ref('stock_extended_ept.approval_type_inv_adjust_stock'):
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', approval.stock_quant_product_id.id),
                    ('location_id', '=', approval.stock_quant_location_id.id)
                ])
                quant.with_context(from_approval=True).write({
                    'inventory_quantity': approval.quantity,
                    'inventory_quantity_set': True,
                })
                quant.action_apply_inventory()
        return res

    def action_refuse(self,  approver=None):
        """
        Refuse the inventory adjustment request:
        - Resets the related stock.quant quantities and user assignment.
        """
        res = super().action_refuse(approver=None)
        for approval in self:
            if approval.category_id == self.env.ref('stock_extended_ept.approval_type_inv_adjust_stock'):
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', approval.stock_quant_product_id.id),
                    ('location_id', '=', approval.stock_quant_location_id.id)
                ])
                quant.write({
                    'inventory_quantity': 0,
                    'inventory_diff_quantity':0,
                    'inventory_quantity_set': False,
                    'user_id': False
                })
        return res