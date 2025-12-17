from odoo import models, fields, api


class StockQuantImportHelper(models.Model):
    _inherit = 'stock.quant'

    # Override in_date field to remove readonly - allows import mapping
    in_date = fields.Datetime(
        string='Incoming Date',
        readonly=False,
        required=True,
        default=fields.Datetime.now,
    )

    @api.model
    def _get_inventory_fields_create(self):
        """Add in_date to allowed fields during inventory import"""
        res = super()._get_inventory_fields_create()
        if 'in_date' not in res:
            res.append('in_date')
        return res

    @api.model
    def _get_inventory_fields_write(self):
        """Add in_date to allowed fields during inventory write"""
        res = super()._get_inventory_fields_write()
        if 'in_date' not in res:
            res.append('in_date')
        return res

