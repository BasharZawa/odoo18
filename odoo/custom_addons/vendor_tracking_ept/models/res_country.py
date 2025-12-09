from odoo import models, fields


class ResCountry(models.Model):
    _inherit = "res.country"

    sequence_prefix = fields.Char(
        string="Sequence Prefix (Customer/ Vendor Tracking)",
        help="Prefix for the vendor and customer tracking sequence specific to this country."
    )