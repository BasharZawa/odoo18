# -*- coding: utf-8 -*-

from odoo import models, fields


class StockLotExtend(models.Model):
    _inherit = 'stock.lot'

    bayan_code = fields.Char(string="Bayan Code")

    def _compute_display_name(self):
        """
        Inherited _compute_display_name to add bayan_code in display name
        """
        res = super()._compute_display_name()
        for rec in self:
            add_on = rec.bayan_code and f" ({rec.bayan_code})" or ""
            if add_on and add_on not in rec.display_name:
                rec.display_name += add_on
        return res