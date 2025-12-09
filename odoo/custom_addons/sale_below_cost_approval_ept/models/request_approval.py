from odoo import api, fields, models, api, _
from odoo.exceptions import ValidationError


class ApprovalRequestEPT(models.Model):
    _inherit = 'approval.request'

    is_discrepancy_req = fields.Boolean(string="Discrepancy Request", copy=False)

    def action_approve(self, approver=None):
        """Override approve action to automatically confirm the sale order"""
        result = super(ApprovalRequestEPT, self).action_approve(approver=approver)
        # Check if this approval is for a sale order
        for req in self:
            req = req.sudo()
            existing_request = req.search([
                ('request_owner_id', '=', req.sale_order_id.user_id.id),
                ('reference', '=', f'sale.order.discrepancy,{req.sale_order_id.id}'),
                ('category_id', '=', req.category_id.id),
                ('is_discrepancy_req', '=', True),
                ('request_status', 'in', ['new', 'pending'])
            ])
            if req.is_discrepancy_req and req.sale_order_id and req.sale_order_id.state == 'on_hold' and req.request_status == 'approved' and len(
                    existing_request) < 1:
                req.sale_order_id.write({'state': 'draft', 'has_below_cost_approved': True})
                req.sale_order_id.with_context(bypass_below_cost_check=True).action_confirm()
        return result

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection(selection_add=[('below_cost_req', 'Sale Below Cost Request')])