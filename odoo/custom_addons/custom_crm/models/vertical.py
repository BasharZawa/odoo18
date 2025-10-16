from odoo import models, fields


class Vertical(models.Model):
    _name = 'vertical'
    _description = 'Vertical'

    name = fields.Char(string='Vertical', required=True)
    description = fields.Text(string='Description')
