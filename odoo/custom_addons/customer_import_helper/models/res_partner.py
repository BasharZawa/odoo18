# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartnerImportHelper(models.Model):
    _inherit = 'res.partner'

    # Override fields to remove readonly for import
    customer_id = fields.Char(
        string='Customer ID',
        readonly=False,  # Allow import
        copy=False,
        help="Unique identifier for customer contacts"
    )

    validation_date = fields.Datetime(
        string='Validation Date',
        readonly=False,  # Allow import
        help="Date when the customer contact was validated"
    )

    validated_by = fields.Many2one(
        'res.users',
        string='Validated By',
        readonly=False,  # Allow import
        help="User who validated this customer contact"
    )