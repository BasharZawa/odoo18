from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_satisfaction_rating = fields.Selection(
        selection=[
            ("1", "★ 1 Star"),
            ("2", "★★ 2 Stars"),
            ("3", "★★★ 3 Stars"),
            ("4", "★★★★ 4 Stars"),
            ("5", "★★★★★ 5 Stars"),
        ],
        string="Satisfaction Rating",
    )
