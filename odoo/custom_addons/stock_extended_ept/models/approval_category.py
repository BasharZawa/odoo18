# -*- coding: utf-8 -*-

from odoo import models, fields


class ApprovalCategory(models.Model):
    """
    Add fields for Inventory Adjustment approval functionality
    """
    _inherit = 'approval.category'

    has_adjustment_product = fields.Selection(selection=[
        ('required', 'Required'), ('optional', 'Optional'), ('no', 'None')
    ], string="Has Adjustment Product", default="no", required=True)
    has_adjustment_location = fields.Selection(selection=[
        ('required', 'Required'), ('optional', 'Optional'), ('no', 'None')
    ], string="Has Adjustment Location", default="no", required=True)
    approval_type = fields.Selection(selection_add=[('stock_adjustment_req', 'Stock Adjustment Request')])
