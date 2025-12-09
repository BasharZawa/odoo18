# -*- coding: utf-8 -*-

from odoo import models, fields, _


class ScrapProductConfirmation(models.TransientModel):
    _name = 'scrap.product.confirmation.wizard'
    _description = 'Scrap Product Confirmation Wizard'

    stock_scrap_id = fields.Many2one(comodel_name="stock.scrap")
    confirmation_message = fields.Text()

    def action_confirm_scrap(self):
        scrap_id = self.stock_scrap_id
        if scrap_id.check_available_qty():
            return scrap_id.do_scrap()
        else:
            ctx = dict(self.env.context)
            ctx.update({
                'default_product_id': scrap_id.product_id.id,
                'default_location_id': scrap_id.location_id.id,
                'default_scrap_id': scrap_id.id,
                'default_quantity': scrap_id.product_uom_id._compute_quantity(scrap_id.scrap_qty, scrap_id.product_id.uom_id),
                'default_product_uom_name': scrap_id.product_id.uom_name
            })
            return {
                'name': _('%(product)s: Insufficient Quantity To Scrap',
                          product=scrap_id.product_id.display_name),
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.scrap',
                'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }