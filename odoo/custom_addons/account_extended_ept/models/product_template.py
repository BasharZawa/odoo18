# -*- coding: utf-8 -*-

from odoo import models


class ProductTemplateExtended(models.Model):
    _inherit = "product.template"
    # default_get override removed: the standard sale module handles
    # invoice_policy defaults via ir.default (default_model on res.config.settings).
