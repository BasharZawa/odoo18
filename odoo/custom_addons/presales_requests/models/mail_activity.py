from odoo import models, api

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None):
        # Always filter presales request activities to show only to assigned users
        current_user = self.env.user
        
        # Add domain to filter presales activities
        presales_filter = [
            '|',
            ('res_model', '!=', 'presales.request'),
            ('user_id', '=', current_user.id)
        ]
        
        args = args + presales_filter
        
        return super()._search(args, offset, limit, order)