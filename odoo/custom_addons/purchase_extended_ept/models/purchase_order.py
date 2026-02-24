# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import ValidationError


class PurchaseOrderExtend(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to restrict PO creation to users with the PO Creation group."""
        if not self.env.user.has_group('purchase_extended_ept.group_purchase_order_create'):
            raise ValidationError(_(
                "You do not have the rights to create a Purchase Order.\n"
                "Please contact your administrator to get access."
            ))
        return super().create(vals_list)
