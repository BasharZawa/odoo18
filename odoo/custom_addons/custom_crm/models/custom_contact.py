from odoo import models, fields, api


class custom_contact(models.Model):
    _inherit = 'res.partner'

    # Adding a new field to the res.partner model
    x_bashar_test = fields.Text(string='Test Field')

    # Override the create method to add custom logic
    @api.model
    def create(self, vals):
        # Show a confirmation message on the front
        if 'x_bashar_test' in vals:
            # Custom logic to show a confirmation message
            # This is just a placeholder; actual implementation may vary
            print("Confirmation: A new contact is being created with the test field.")
            #confirm message = "Are you sure you want to create this contact?"
            if confirm(message):
                raise UserError("Contact creation cancelled by user.")
        return super(custom_contact, self).create(vals)

