# -*- coding: utf-8 -*-

import math
from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockScrapExtended(models.Model):
    _inherit = 'stock.scrap'


    def action_validate(self):
        # Override the action to include tolerance check before scrapping
        self.ensure_one()
        self._check_positive_quantity()

        tolerance, prod_qty, already_scrapped_qty, scrap_limit = self._calculate_tolerance_limits()

        if tolerance and prod_qty and scrap_limit < self.scrap_qty:
            message = self._get_tolerance_message(tolerance, scrap_limit)
            return self._get_tolerance_wizard_action(message)

        return self._process_scrap_validation()

    def _check_positive_quantity(self):
        """Check if scrap quantity is positive"""
        if float_is_zero(self.scrap_qty, precision_rounding=self.product_uom_id.rounding):
            raise UserError(_('You can only enter positive quantities.'))

    def _calculate_tolerance_limits(self):
        """Calculate tolerance and scrap limits"""
        tolerance = self.product_id.tolerance
        prod_qty = sum(self.production_id.move_raw_ids.filtered(
            lambda m: m.product_id == self.product_id).mapped('product_uom_qty'))
        already_scrapped_qty = sum(self.production_id.scrap_ids.filtered(
            lambda s: s.product_id == self.product_id and s.state == 'done').mapped('scrap_qty'))
        scrap_limit = math.floor(prod_qty * tolerance / 100) - already_scrapped_qty
        return tolerance, prod_qty, already_scrapped_qty, scrap_limit

    def _is_tolerance_exceeded(self, tolerance, prod_qty, scrap_limit):
        """Check if scrap quantity exceeds tolerance limits"""
        return

    def _get_tolerance_message(self, tolerance, scrap_limit):
        """Generate tolerance warning message"""
        if scrap_limit <= 0:
            return _(
                'You are trying to scrap %(scrap_qty)s units of %(product)s '
                'which exceeds the allowed tolerance of %(tolerance)s%%. '
                'Do you want to proceed?') % {
                'scrap_qty': self.scrap_qty,
                'product': self.product_id.display_name,
                'tolerance': tolerance,
            }
        else:
            return _(
                'You are trying to scrap %(scrap_qty)s units of %(product)s '
                'which exceeds the allowed tolerance of %(tolerance)s%% '
                '(%(scrap_limit)s units). Do you want to proceed?') % {
                'scrap_qty': self.scrap_qty,
                'product': self.product_id.display_name,
                'tolerance': tolerance,
                'scrap_limit': scrap_limit
            }

    def _get_tolerance_wizard_action(self, message):
        """Return tolerance confirmation wizard action"""
        return {
            'name': _('%(product)s: Tolerance Confirmation',
                      product=self.product_id.display_name),
            'view_mode': 'form',
            'res_model': 'scrap.product.confirmation.wizard',
            'view_id': self.env.ref(
                'mrp_extended_ept.view_scrap_product_confirmation_wizard_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_stock_scrap_id': self.id,
                'default_confirmation_message': message
            },
            'target': 'new'
        }

    def _get_insufficient_qty_action(self):
        """Return insufficient quantity warning action"""
        ctx = dict(self.env.context)
        ctx.update({
            'default_product_id': self.product_id.id,
            'default_location_id': self.location_id.id,
            'default_scrap_id': self.id,
            'default_quantity': self.product_uom_id._compute_quantity(self.scrap_qty,
                                                                      self.product_id.uom_id),
            'default_product_uom_name': self.product_id.uom_name
        })
        return {
            'name': _('%(product)s: Insufficient Quantity To Scrap',
                      product=self.product_id.display_name),
            'view_mode': 'form',
            'res_model': 'stock.warn.insufficient.qty.scrap',
            'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }

    def _process_scrap_validation(self):
        """Process the final scrap validation"""
        if self.check_available_qty():
            return self.do_scrap()
        else:
            return self._get_insufficient_qty_action()
