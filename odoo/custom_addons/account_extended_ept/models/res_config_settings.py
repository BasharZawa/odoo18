from odoo import models, fields, api

class ResConfigSettingsInvoicePolicy(models.TransientModel):
    _inherit = 'res.config.settings'

    default_invoice_policy = fields.Selection(
        [
            ('order', 'Ordered quantities'),
            ('delivery', 'Delivered quantities'),
        ],
        string='Default Invoice Policy'
    )


    def set_values(self):
        """Save values when clicking Save"""
        super().set_values()
        self.env.company.invoice_policy = self.default_invoice_policy

    @api.model
    def get_values(self):
        res = super().get_values()
        # custom logic here
        res.update(
            default_invoice_policy=self.env.company.invoice_policy
        )
        return res