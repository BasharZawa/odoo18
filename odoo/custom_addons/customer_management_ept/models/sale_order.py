# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Extend state field with validation_pending
    state = fields.Selection(selection_add=[
        ('validation_pending', 'Validation Pending')
    ])
    previous_state = fields.Char(string='Previous State', copy=False)

    # End Customer field
    end_customer_id = fields.Many2one(
        'res.partner',
        string='End Customer',
        help="Used for license management and service tracking"
    )

    # Approval Status
    pilot_approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status (Pilot Order)', default='draft', copy=False)

    # Schedule fields
    invoicing_schedule_ids = fields.One2many(
        'sale.order.invoicing.schedule',
        'sale_order_id',
        string='Invoicing Schedule'
    )

    recognition_schedule_ids = fields.One2many(
        'sale.order.recognition.schedule',
        'sale_order_id',
        string='Recognition Schedule'
    )

    distribution_schedule_ids = fields.One2many(
        'sale.order.distribution.schedule',
        'sale_order_id',
        string='Distribution Schedule'
    )

    # Computed fields for totals
    total_invoicing_amount = fields.Monetary(
        string='Total Invoicing Amount',
        compute='_compute_schedule_totals',
        currency_field='currency_id'
    )

    total_recognition_amount = fields.Monetary(
        string='Total Recognition Amount',
        compute='_compute_schedule_totals',
        currency_field='currency_id'
    )

    total_commission_percentage = fields.Float(
        string='Total Commission %',
        compute='_compute_schedule_totals',
        digits=(5, 2)
    )

    @api.depends('invoicing_schedule_ids.invoice_amount',
                 'recognition_schedule_ids.amount',
                 'distribution_schedule_ids.commission_percentage')
    def _compute_schedule_totals(self):
        for order in self:
            order.total_invoicing_amount = sum(order.invoicing_schedule_ids.mapped('invoice_amount'))
            order.total_recognition_amount = sum(order.recognition_schedule_ids.mapped('amount'))
            order.total_commission_percentage = sum(order.distribution_schedule_ids.mapped('commission_percentage'))

    @api.constrains('distribution_schedule_ids')
    def _check_commission_percentage_total(self):
        for order in self:
            total_percentage = sum(order.distribution_schedule_ids.mapped('commission_percentage'))
            if total_percentage > 100:
                raise UserError(
                    _('Total commission percentage cannot exceed 100%. Current total: %.2f%%') % total_percentage)

    @api.constrains('invoicing_schedule_ids')
    def _check_invoicing_amount_total(self):
        for order in self:
            total_invoicing = sum(order.invoicing_schedule_ids.mapped('invoice_amount'))
            if total_invoicing > order.amount_total:
                raise UserError(_('Total invoicing amount (%.2f) cannot exceed order total (%.2f)') % (total_invoicing,
                                                                                                       order.amount_total))

    @api.constrains('recognition_schedule_ids')
    def _check_recognition_amount_total(self):
        for order in self:
            total_recognition = sum(order.recognition_schedule_ids.mapped('amount'))
            if total_recognition > order.amount_total:
                raise UserError(
                    _('Total recognition amount (%.2f) cannot exceed order total (%.2f)') % (total_recognition,
                                                                                             order.amount_total))

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for order in self:
            if 'partner_id' in vals and order.partner_id.validation_status != 'validated':
                # Save original state before overriding
                order.previous_state = order.state
                order.state = 'validation_pending'
                order.message_post(
                    body=_(
                        'Customer %s must be validated by the Finance team before this Sales Order can proceed. '
                        'The Finance team has been notified.'
                    ) % order.partner_id.name,
                    subtype_xmlid="mail.mt_note",
                )
                order.action_request_customer_approval()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(SaleOrder, self).create(vals_list)

        for order in orders:
            if order.partner_id.validation_status != 'validated':
                # Save original state before overriding
                order.previous_state = order.state
                order.state = 'validation_pending'
                order.message_post(
                    body=_(
                        'Customer %s must be validated by the Finance team before this Sales Order can proceed. '
                        'The Finance team has been notified.'
                    ) % order.partner_id.name,
                    subtype_xmlid="mail.mt_note",
                )
                order.action_request_customer_approval()

        return orders

    def action_request_customer_approval(self):
        self.ensure_one()
        if not self:
            raise UserError(_('No sale order found.'))
        ApprovalRequest = self.env['approval.request']
        ApprovalCategory = self.env['approval.category']

        # Get or create approval category
        # category = self.env.ref(
        #     "customer_management_ept.approvals_category_customer_validate"
        # )
        category = self.env['approval.category'].search([
            ('approval_type', '=', 'customer_validation'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not category:
            category = ApprovalCategory.create({
                'name': 'Customer Validation Approval',
                'approver_ids': [],
                'approval_type' : 'customer_validation',
                'company_id' : self.env.company.id,
            })
        # Notify Sales Managers: create activity on order
        manager_group = self.env.ref('customer_management_ept.group_finance_team')
        managers = manager_group.users
        # Prepare approvers
        approver_vals = []
        for manager in managers:
            approver_vals.append((0, 0, {
                'user_id': manager.id,
                'required': 'required',
            }))
        if not approver_vals:
            manager = self.env.ref('base.user_admin') or self.env.ref('base.user_root')
            approver_vals.append((0, 0, {
                'user_id': manager.id,
                'required': 'required',
            }))
        # Check for existing request
        existing_request = ApprovalRequest.search([
            ('partner_id', '=', self.partner_id.id),
            ('request_owner_id', '=', self.user_id.id),
            ('reference', '=', f'customer.validation.approval,{self.id}')
        ], limit=1)
        if existing_request:
            return existing_request

        # Create approval request
        request = ApprovalRequest.create({
            'name': _('Customer Validation Approval for %s') % (self.partner_id.name or _('New')),
            'request_owner_id': self.user_id.id,
            'category_id': category.id,
            'partner_id': self.partner_id.id,
            'request_status': 'pending',
            'reference': f'customer.validation.approval,{self.id}',
            # 'approver_ids': approver_vals,
            'date': fields.Date.today(),
            'reason': 'Customer Is Not Validated',
            'sale_order_id': self.id,
            'is_cust_approval_req': True,
        })
        request.sudo().action_confirm()
        # Post message
        self.message_post(
            body=_(
                "The document partner is not validated. "
                "Approval request %s has been created."
            ) % request.name,
            subtype_xmlid="mail.mt_note",
        )
        return {'type': 'ir.actions.act_window_close'}
