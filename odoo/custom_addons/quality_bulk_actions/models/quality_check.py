from odoo import models
from odoo.exceptions import UserError


class QualityCheck(models.Model):
    _inherit = "quality.check"

    # Methods moved to quality.check.bulk.wizard
