from odoo import api, fields, models, api, _
from odoo.exceptions import ValidationError


class ApprovalRequestEPT(models.Model):
    _inherit = 'approval.request'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    is_credit_req = fields.Boolean(string="Credit Request", copy=False)

    def action_approve(self, approver=None):
        """Override approve action to automatically confirm the sale order"""
        result = super(ApprovalRequestEPT, self).action_approve(approver=approver)
        # Check if this approval is for a sale order
        for req in self:
            req = req.sudo()
            if req.is_credit_req and req.sale_order_id and req.sale_order_id.state == 'on_hold' and req.request_status == 'approved':
                req.sale_order_id.write({'state': 'draft'})
                req.sale_order_id.with_context(from_approval=True).action_confirm()
        return result

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection(selection_add=[('sales_credit_req', 'Sales Credit Request')])
    create_approval_request = fields.Boolean(
        string="Create Approval Request ?",
        help="If enabled, an approval request will be created for the selected category."
    )