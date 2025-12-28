from odoo import models, fields

class ResConfigSettingsApiToken(models.TransientModel):
    _inherit = 'res.config.settings'

    api_token = fields.Char(string="API Token", config_parameter='api_module.api_token')
    companyid= fields.Char(string="Company ID", config_parameter='CompanyID')







