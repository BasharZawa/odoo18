from odoo import models, fields


class InterestedSolution(models.Model):
    _name = 'interested.solution'
    _description = 'Interested Solution'

    name = fields.Char(string='Interested Solution', required=True)
    description = fields.Text(string='Description')
    product_line_id = fields.Many2one('product.line', string='Aligned Product Category')