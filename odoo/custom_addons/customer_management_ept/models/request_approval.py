from odoo import api, fields, models, api, _
from odoo.exceptions import ValidationError


class ApprovalRequestEPT(models.Model):
    _inherit = 'approval.request'

    is_cust_approval_req = fields.Boolean(string="Customer Approval Request", copy=False)

    def action_approve(self, approver=None):
        """Override approve action to automatically confirm the sale order"""
        result = super(ApprovalRequestEPT, self).action_approve(approver=approver)
        # Check if this approval is for a sale order
        for req in self:
            req = req.sudo()
            if req.is_cust_approval_req and req.partner_id and req.partner_id.validation_status == 'not_validated' and req.request_status == 'approved':
                # restore to the previous state of all sale orders in validation_pending state
                orders = self.env['sale.order'].sudo().search(
                    [('partner_id', '=', req.partner_id.id), ('state', '=', 'validation_pending')])
                for order in orders:
                    if order.previous_state and order.previous_state != 'validation_pending':
                        order.state = order.previous_state
                    else:
                        order.state = 'draft'
                req.partner_id.with_context(check_bypass=True).action_validate_customer()
        return result

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection(selection_add=[('customer_validation', 'Customer Validation Request')])