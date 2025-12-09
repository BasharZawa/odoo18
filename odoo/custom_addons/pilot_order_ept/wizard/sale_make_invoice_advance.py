# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        # Check for pilot orders without customer confirmation
        pilot_orders = sale_orders.filtered(lambda order: order.is_pilot_order and not order.customer_confirmation)
        if pilot_orders:
            raise UserError(_(
                "Cannot create invoices for pilot orders that haven't received customer confirmation. "
                "The following orders require customer confirmation: %s"
            ) % ', '.join(pilot_orders.mapped('name')))

        return super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)
