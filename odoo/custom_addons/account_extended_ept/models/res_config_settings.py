from odoo import models

class ResConfigSettingsInvoicePolicy(models.TransientModel):
    _inherit = 'res.config.settings'
    # default_invoice_policy is already defined in addons/sale with
    # default_model='product.template' and managed via ir.default.
    # No need to re-declare or override get_values/set_values here.