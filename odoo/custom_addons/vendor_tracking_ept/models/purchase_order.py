# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrderExtended(models.Model):
    _inherit = 'purchase.order'

    boe_number = fields.Char(string="BOE Number", help="Bill Of Entry Number")

    def button_confirm(self):
        """
        Inherited button_confirm to write boe_number to related stock pickings.
        """
        res = super().button_confirm()
        if 'boe_number' in self.env['stock.picking']._fields:
            for order in self:
                if order.boe_number:
                    for pick in order.picking_ids:
                        pick.write({
                            'boe_number': order.boe_number,
                        })
        return res
