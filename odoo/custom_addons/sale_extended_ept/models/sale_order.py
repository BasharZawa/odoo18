from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(
        selection_add=[("on_hold", "On Hold")],
        ondelete={"on_hold": "set default"},
    )

    credit_on_hold = fields.Boolean(
        string="Credit On Hold",
        help="Set automatically if the customer has overdue invoices at confirmation time.",
        readonly=True,
        copy=False,
    )

    credit_overdue_amount = fields.Monetary(
        string="Overdue Amount",
        currency_field="currency_id",
        compute="_compute_credit_overdue_amount",
        store=False,
    )

    approval_request_id = fields.Many2one(
        "approval.request",
        string="Approval Request",
        readonly=True,
        copy=False,
    )

    approval_status = fields.Selection(
        related="approval_request_id.request_status",
        string="Approval Status",
        readonly=True,
        store=False,
    )

    credit_available = fields.Monetary(
        string="Available Credit",
        currency_field="currency_id",
        compute="_compute_credit_available",
        store=False,
    )

    approval_count = fields.Integer(
        string="Approval Count",
        compute="_compute_approval_count",
        store=False,
    )

    boe_number = fields.Char(string="BOE Number", help="Bill Of Entry Number")

    def _compute_credit_overdue_amount(self):
        for order in self:
            order.credit_overdue_amount = order._compute_credit_available()

    def _compute_approval_count(self):
        for order in self:
            order.approval_count = self.env["approval.request"].search_count([
                ("sale_order_id", "=", order.id)
            ])

    def _compute_credit_available(self, partner=False):
        """Compute overdue amount for a specific partner"""
        for order in self:
            current_amount = (order.amount_total / order.currency_rate)
            partner = order.partner_id.commercial_partner_id
            partner = partner.sudo()
            credit_to_invoice = partner.credit_to_invoice
            total_credit = partner.credit + credit_to_invoice + current_amount
            credit_limit = partner.credit_limit or 0.0
            order.credit_available = credit_limit - total_credit
            if not partner.credit_limit or total_credit <= partner.credit_limit:
                return 0.0
            return total_credit

    def _has_partner_overdue_invoices(self):
        """Check if partner has any overdue invoices"""
        self.ensure_one()
        overdue_invoices = self.env['account.move'].search(self._get_overdue_invoices_domain(self.partner_id.commercial_partner_id.id))
        return (len(overdue_invoices) if overdue_invoices else 0) > 0

    def _get_overdue_invoices_domain(self, partner_id=None):
        return [
            ('state', 'not in', ('cancel', 'draft')),
            ('move_type', 'in', ('out_invoice', 'out_receipt')),
            ('payment_state', 'not in', ('in_payment', 'paid', 'reversed', 'blocked', 'invoicing_legacy')),
            ('invoice_date_due', '<', fields.Date.today()),
            ('partner_id', '=', partner_id or self.env.user.partner_id.id),
        ]

    def _is_credit_limit_exceeded(self):
        self.ensure_one()
        return self.credit_available < self.amount_total

    def action_confirm(self):
        hold_reason = []
        for order in self:
            if not order.env.context.get(
                    "from_approval") and order.approval_request_id.request_status != 'approved' and order.company_id.account_use_credit_limit:
                if order._has_partner_overdue_invoices():
                    hold_reason.append("overdue invoices")
                if order._is_credit_limit_exceeded():
                    hold_reason.append("credit limit exceeded")

                if hold_reason:
                    order.write({
                        "state": "on_hold",
                        "credit_on_hold": True,
                    })
                    # Create approval request
                    order._create_approval_request()
                    # Create a chatter note for visibility
                    reason_text = " and ".join(hold_reason)
                    order.message_post(
                        body=_("Order placed On Hold due to %s. Approval request has been created.") % reason_text,
                        subtype_xmlid="mail.mt_note",
                    )
        if hold_reason:
            return True
        res = super(SaleOrder, self).action_confirm()
        if 'boe_number' in self.env['stock.picking']._fields:
            for order in self:
                if order.boe_number:
                    for pick in order.picking_ids:
                        pick.write({
                            'boe_number': order.boe_number,
                        })
        return res

    def _create_approval_request(self):
        """Create an approval request for the sale order"""
        self.ensure_one()

        # Get the predefined approval category
        # category = self.env.ref("sale_extended_ept.approval_category_sale_order_credit_hold")
        category = self.env['approval.category'].search([
            ('approval_type', '=', 'sales_credit_req'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not category:
            category = self.env['approval.category'].sudo().create({
                'name': 'Sale Order Credit Hold',
                'approver_ids': [],
                'approval_type': 'sales_credit_req',
                'company_id': self.env.company.id,
            })
        # Create approval request
        approval_request = self.env["approval.request"].sudo().create({
            "name": f"Credit Hold Approval - {self.name}",
            "category_id": category.id,
            "request_owner_id": self.user_id.id,
            "date": fields.Date.today(),
            "amount": self.amount_total,
            "partner_id": self.partner_id.id,
            "reference": self.name,
            "sale_order_id": self.id,
            "request_status": "new",
            "is_credit_req": True,
        })
        approval_request.sudo().action_confirm()

        self.approval_request_id = approval_request.id
        return approval_request

    def action_view_approval_request(self):
        """Open the approval request form"""
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(_("No approval request found for this order."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Request"),
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_all_approvals(self):
        """Open all approval requests for this sale order"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Requests"),
            "res_model": "approval.request",
            "domain": [("sale_order_id", "=", self.id)],
            "view_mode": "list,form",
            "target": "current",
        }

    def action_resubmit_approval(self):
        """Resubmit approval request after rejection"""
        self.ensure_one()
        if self.state != "on_hold":
            raise UserError(_("Only orders on hold can resubmit approval."))

        if not self.approval_request_id:
            raise UserError(_("No approval request found for this order."))

        if self.approval_request_id.request_status != "refused":
            raise UserError(_("Only rejected approval requests can be resubmitted."))

        # Create a new approval request
        self.approval_request_id = self._create_approval_request()

        # Log the resubmission
        self.message_post(
            body=_("Approval request has been resubmitted after rejection."),
            subtype_xmlid="mail.mt_note",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _("Approval request has been resubmitted."),
                "type": "success",
            },
        }
