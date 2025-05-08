from odoo import models, fields

class City(models.Model):
    _name = 'ir.city'
    _description = 'City'

    name = fields.Char(string='City Name', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one('res.country.state', string='State')