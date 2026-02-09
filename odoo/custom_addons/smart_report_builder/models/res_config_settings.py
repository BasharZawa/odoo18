from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    smart_report_n8n_webhook_url = fields.Char(
        string='n8n Webhook URL',
        config_parameter='smart_report_builder.n8n_webhook_url',
        help='The n8n webhook URL that processes natural language queries via Claude AI'
    )
    smart_report_n8n_auth_token = fields.Char(
        string='n8n Auth Token',
        config_parameter='smart_report_builder.n8n_auth_token',
        help='Optional Bearer token for securing the n8n webhook'
    )
