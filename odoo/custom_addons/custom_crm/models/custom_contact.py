from odoo import models, fields, api
from odoo.exceptions import UserError
import logging



class custom_contact(models.Model):
    _inherit = 'res.partner'

    # Adding a new field to the res.partner model
    x_bashar_test = fields.Text(string='Test Field')

    # Override the create method to add custom logic
    @api.model_create_multi
    def create(self, vals_list):
        _logger = logging.getLogger(__name__)
        for vals in vals_list:
            _logger.info("Creating a new contact with values: %s", vals)
            if 'email' in vals and vals['email']:
                vals['email'] = vals['email'].lower()
        return super(custom_contact, self).create(vals_list)
    
    # Override the write method to add custom logic
    @api.model
    def write(self, vals):
        _logger = logging.getLogger(__name__)
        _logger.info("Updating a contact with values: %s", vals)
        if 'email' in vals and vals['email']:
            vals['email'] = vals['email'].lower()
        return super(custom_contact, self).write(vals)

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