# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockLandedCostExtend(models.Model):
    _inherit = 'stock.landed.cost'

    lc_currency_id = fields.Many2one(
        'res.currency', string="Landed Cost Currency",
        default=lambda self: self.env.company.currency_id
    )
    invoice_currency_rate = fields.Float(
        string="Invoice Currency Rate",
        digits=(12, 6),
        compute='_compute_invoice_currency_rate',
        store=True
    )
    manual_cost_total = fields.Monetary(
        string="Total",
        compute='_compute_manual_cost_total',
        currency_field='lc_currency_id',
        store=True,
    )

    @api.depends('lc_currency_id', 'date', 'company_id')
    def _compute_invoice_currency_rate(self):
        for record in self:
            if record.lc_currency_id and record.company_id:
                record.invoice_currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=record.company_id.currency_id,
                    to_currency=record.lc_currency_id,
                    company=record.company_id,
                    date=record.date or fields.Date.today(),
                )
            else:
                record.invoice_currency_rate = 1.0

    @api.depends('cost_lines.manual_added_cost', 'invoice_currency_rate')
    def _compute_manual_cost_total(self):
        for cost in self:
            cost.manual_cost_total = sum(cost.cost_lines.mapped('manual_added_cost'))

    @api.onchange('lc_currency_id', 'date')
    def _onchange_date_and_lc_currency_id(self):
        for cost in self:
            for line in cost.cost_lines:
                line.action_update_cost()


class StockLandedCostLineExtend(models.Model):
    _inherit = 'stock.landed.cost.lines'

    lc_line_currency_id = fields.Many2one(related='cost_id.lc_currency_id', string="Landed Cost Currency")
    manual_added_cost = fields.Monetary(string="Manual Cost", currency_field='lc_line_currency_id')
    is_cost_synced = fields.Boolean(string="Cost Synced", default=False)

    @api.onchange('manual_added_cost')
    def _onchange_manual_added_cost(self):
        self.is_cost_synced = False


    def action_update_cost(self):
        """
        Updates the price_unit field with the value from manual_added_cost.
        """
        for line in self:
            if line.manual_added_cost:
                conversion_rate = line.cost_id.invoice_currency_rate or 1.0
                line.price_unit = line.manual_added_cost / conversion_rate
                line.is_cost_synced = True
        return True
