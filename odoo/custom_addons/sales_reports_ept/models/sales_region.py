# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalesRegion(models.Model):
    _name = 'sales.region'
    _description = 'Sales Region'
    _order = 'sequence, name'

    name = fields.Char(string='Region Name', required=True)
    code = fields.Char(string='Code', size=10)
    sequence = fields.Integer(string='Sequence', default=10)
    country_ids = fields.Many2many(
        'res.country',
        'sales_region_country_rel',
        'region_id',
        'country_id',
        string='Countries',
        help='Countries belonging to this region'
    )
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Region name must be unique!'),
        ('code_unique', 'UNIQUE(code)', 'Region code must be unique!'),
    ]
    
    def toggle_active(self):
        """Toggle the active status of the region"""
        for record in self:
            record.active = not record.active
