# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderDistributionSchedule(models.Model):
    _name = 'sale.order.distribution.schedule'
    _description = 'Sales Order Distribution Schedule'
    _order = 'commission_percentage desc'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade'
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        required=True,
        help="The individual involved in the sales effort"
    )

    commission_percentage = fields.Float(
        string='Commission %',
        required=True,
        digits=(5, 2),
        help="The percentage of the total commission or credit attributed to the salesperson"
    )

    commission_amount = fields.Monetary(
        string='Commission Amount',
        compute='_compute_commission_amount',
        currency_field='currency_id',
        help="Calculated commission amount based on percentage and order total"
    )

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        string='Currency',
        readonly=True
    )

    @api.depends('commission_percentage', 'sale_order_id.amount_total')
    def _compute_commission_amount(self):
        for record in self:
            if record.sale_order_id and record.commission_percentage:
                record.commission_amount = (record.sale_order_id.amount_total * record.commission_percentage) / 100
            else:
                record.commission_amount = 0.0

    @api.constrains('commission_percentage')
    def _check_commission_percentage(self):
        for record in self:
            if record.commission_percentage < 0 or record.commission_percentage > 100:
                raise UserError(_('Commission percentage must be between 0 and 100.'))

    @api.constrains('salesperson_id', 'sale_order_id')
    def _check_unique_salesperson(self):
        for record in self:
            existing = self.search([
                ('sale_order_id', '=', record.sale_order_id.id),
                ('salesperson_id', '=', record.salesperson_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise UserError(_('Each salesperson can only be assigned once per sales order.'))
