from odoo import fields, models


class AccountMoveChangeWizard(models.TransientModel):
    _name = 'account.move.change.wizard'
    _description = 'Account Move Change Wizard'

    move_id = fields.Many2one('account.move', string='Invoice', required=True)
    new_name = fields.Char(string='New Invoice Number', required=True)

    def action_apply(self):
        self.ensure_one()
        self.move_id.force_set_name(self.new_name)
        return {'type': 'ir.actions.act_window_close'}
