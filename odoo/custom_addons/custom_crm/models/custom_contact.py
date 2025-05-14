from odoo import models, fields, api
from odoo.exceptions import UserError



class custom_contact(models.Model):
    _inherit = 'res.partner'

    # Adding a new field to the res.partner model
    x_bashar_test = fields.Text(string='Test Field')

    # Override the create method to add custom logic
    @api.model
    def create(self, vals):
        if 'x_bashar_test' in vals and vals['x_bashar_test']:
            # Custom logic 
            vals['x_bashar_test']= vals['x_bashar_test'].upper()
        return super(custom_contact, self).create(vals)

    def action_test_raise(self):
        # Custom action method
        raise UserError('This is a test action method')

    def action_test(self):
        # Custom action method to show a success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
            'title': 'Success!',
            'message': 'Testing notification',
            'type': 'success',  # Types: success, warning, danger
            'sticky': False,    # If True, the notification will not disappear automatically
            },
        }