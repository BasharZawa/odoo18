# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderInvoicingSchedule(models.Model):
    _name = 'sale.order.invoicing.schedule'
    _description = 'Sales Order Invoicing Schedule'
    _order = 'invoice_date asc'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade'
    )

    invoice_date = fields.Date(
        string='Invoice Date',
        required=True,
        help="When the invoice should be generated"
    )

    due_date = fields.Date(
        string='Due Date',
        required=True,
        help="When the payment is expected from the customer"
    )

    invoice_amount = fields.Monetary(
        string='Invoice Amount',
        required=True,
        currency_field='currency_id',
        help="The monetary value to be billed at that milestone or period"
    )

    billing_milestone_description = fields.Char(
        string='Billing Milestone Description',
        required=True,
        help="A label or reference for the phase/milestone"
    )

    invoiced_status = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('invoiced', 'Invoiced')
    ], string='Invoiced Status', default='not_invoiced', required=True)

    reference_document = fields.Char(
        string='Reference Document',
        help="Invoice number (if invoiced)"
    )

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        string='Currency',
        readonly=True
    )

    @api.constrains('invoice_date', 'due_date')
    def _check_dates(self):
        for record in self:
            if record.invoice_date and record.due_date and record.invoice_date > record.due_date:
                raise UserError(_('Invoice Date cannot be later than Due Date.'))

    @api.constrains('invoice_amount')
    def _check_amount(self):
        for record in self:
            if record.invoice_amount <= 0:
                raise UserError(_('Invoice Amount must be greater than zero.'))
