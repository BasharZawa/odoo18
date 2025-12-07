from odoo import models, fields, api

# -*- coding: utf-8 -*-



class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_studio_customer_id = fields.Char(string='Customer ID')
    validated_by = fields.Many2one('res.users', string='Validated By')
    validation_date = fields.Datetime(string='Validation Date')
    validation_status=fields.Selection([
        ('not_validated', 'Not Validated'),
        ('validated', 'Validated'),
    ], string='Validation Status', default='not_validated')
    validation_notes = fields.Text(string='Validation Notes')
    customer_type = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),     
        ('both', 'Both'),
    ], string='Contact Type', default='customer')