# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderRecognitionSchedule(models.Model):
    _name = 'sale.order.recognition.schedule'
    _description = 'Sales Order Recognition Schedule'
    _order = 'recognition_date asc'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade'
    )

    recognition_date = fields.Date(
        string='Recognition Date',
        required=True,
        help="The specific date on which revenue is to be recognized"
    )

    description = fields.Char(
        string='Description',
        required=True,
        help="A brief explanation of the milestone or revenue recognition event"
    )

    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        help="The portion of the total order value to be recognized on that date"
    )

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        string='Currency',
        readonly=True
    )

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise UserError(_('Recognition Amount must be greater than zero.'))
