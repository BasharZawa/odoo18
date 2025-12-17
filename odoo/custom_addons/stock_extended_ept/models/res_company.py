# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompanyExtend(models.Model):
    _inherit = 'res.company'

    is_bayan_code_applicable = fields.Boolean(string="BOE Number Applicable")
