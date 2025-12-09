from odoo import api, fields, models, api, _
from odoo.exceptions import ValidationError


class ApprovalRequestEPT(models.Model):
    _inherit = 'approval.request'

    is_disc_req = fields.Boolean(string="Discount Request", copy=False)
    parent_request_id = fields.Many2one('approval.request', string='Parent Request', readonly=True)
    child_request_ids = fields.One2many('approval.request', 'parent_request_id', string='Child Requests', readonly=True)

    def action_approve(self, approver=None):
        """Override approve action to enforce parent-child logic and automatically confirm the sale order"""
        for req in self:
            req = req.sudo()
            # Check if all child requests are approved
            if req.is_disc_req and req.sale_order_id and req.sale_order_id.state == 'on_hold' and req.child_request_ids and any(
                    child.request_status != 'approved' for child in req.child_request_ids):
                raise ValidationError(_("You cannot approve this request until all child requests are approved."))

        result = super(ApprovalRequestEPT, self).action_approve(approver=approver)

        for req in self:
            req = req.sudo()
            # Notify parent request
            if req.is_disc_req and req.parent_request_id:
                req.parent_request_id.message_post(
                    body=_("Child request %s has been approved by %s.") % (req.name, self.env.user.name)
                )

            # Check if this approval is for a sale order and it is the final parent (no parent_id)
            if req.is_disc_req and req.sale_order_id and req.sale_order_id.state == 'on_hold' and req.request_status == 'approved' and not req.parent_request_id:
                req.sale_order_id.write({'state': 'draft'})
                req.sale_order_id.with_context(from_disc_approval=True).action_confirm()
        return result

    def action_refuse(self, approver=None):
        """Refuse the entire parent-child hierarchy in a single pass (no recursion)."""

        disc_reqs = self.filtered(
            lambda r: r.is_disc_req and r.sale_order_id and r.sale_order_id.state == 'on_hold'
        )
        if not disc_reqs:
            return super(ApprovalRequestEPT, self).action_refuse(approver=approver)
        top_parents = self.env['approval.request']
        for req in disc_reqs:
            top = req
            while top.parent_request_id:
                top = top.parent_request_id
            top_parents |= top
        all_requests = self.env['approval.request']
        queue = list(top_parents)
        while queue:
            node = queue.pop(0)
            if node not in all_requests:
                all_requests |= node
                queue += node.child_request_ids
        cancel_remaining = all_requests.filtered(
            lambda r: r.request_status not in ['refused', 'approved', 'cancelled'] and r.id != self[0].id
        )
        if cancel_remaining:
            cancel_remaining.sudo().action_cancel()
        res = super(ApprovalRequestEPT, self).action_refuse(approver=approver)
        return res


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection(selection_add=[('discount_request', 'Discount Request')])
