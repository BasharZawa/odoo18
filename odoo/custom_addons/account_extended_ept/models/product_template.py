# -*- coding: utf-8 -*-

from odoo import models


class ProductTemplateExtended(models.Model):
    _inherit = "product.template"

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'invoice_policy' in fields_list or not self.env.context.get('default_invoice_policy', False):
            res['invoice_policy'] = self.env.company.invoice_policy
        return res
