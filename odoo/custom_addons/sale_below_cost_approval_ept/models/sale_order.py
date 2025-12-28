from pygments.lexer import default

from odoo import models, fields, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_below_cost_approved = fields.Boolean(string='Has Below-Cost Approved', default=False, copy=False)

    def _action_open_below_cost_wizard(self):
        self.ensure_one()
        if not self.env.context.get('no_open_wizard', False):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Below Cost Approval'),
                'res_model': 'sale.below.cost.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_order_id': self.id,
                },
            }
        # create the wizard record and call its method to send the approval request
        wiz = self.env['sale.below.cost.wizard'].sudo()
        lines = self.order_line.filtered(lambda l: l.below_cost)
        table_html = ""
        if lines:
            # HTML table header
            table_html = wiz._prepare_below_cost_lines_html(lines, include_cost=True)
            # table_html += "</tbody></table>"
        wizard = wiz.create({'order_id': self.id, 'below_lines_info': table_html, 'reason': _(
            'Auto generated approval due to alteration in Order Line Selling Below Cost Approval Request')})
        if self.order_line.filtered(lambda l: l.below_cost):
            wizard.action_request_approval()
        return False


    def action_confirm(self):
        for order in self:
            category = self.env['approval.category'].search([
                ('approval_type', '=', 'below_cost_req'), ('company_id', '=', self.env.company.id)
                ], limit=1)
            if (category and category.create_approval_request) and not order.has_below_cost_approved and not self.env.context.get('bypass_below_cost_check'):
                below_lines = order.order_line.filtered(lambda l: l.below_cost)
                if below_lines:
                    return order._action_open_below_cost_wizard()
        return super(SaleOrder, self).action_confirm()
