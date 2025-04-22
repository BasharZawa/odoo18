# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_be_mobility_budget = fields.Boolean(string="Mobility Budget")
    l10n_be_mobility_budget_amount = fields.Monetary(
        string="Mobility Budget Amount",
        store=True,
        compute="_compute_l10n_be_mobility_budget_amount"
    )
    l10n_be_mobility_budget_amount_monthly = fields.Monetary(
        string="Mobility Budget Monthly Amount",
        compute="_compute_l10n_be_mobility_budget_amount_monthly"
    )
    l10n_be_wage_with_mobility_budget = fields.Monetary(
        tracking=True, string="Wage with Mobility Budget",
        compute="_compute_l10n_be_wage_with_mobility_budget",
        store=True
    )

    def _get_wage_to_apply(self):
        self.ensure_one()
        if self.l10n_be_mobility_budget:
            return self.l10n_be_wage_with_mobility_budget
        else:
            return super()._get_wage_to_apply()

    @api.depends('l10n_be_mobility_budget', 'wage_with_holidays')
    def _compute_l10n_be_mobility_budget_amount(self):
        mobility_budget_max = self.env['hr.rule.parameter']._get_parameter_from_code("mobility_budget_max", fields.Date.today(), raise_if_not_found=False) or 0
        for contract in self:
            if contract.l10n_be_mobility_budget:
                base = contract.wage_with_holidays
                raw_mb = base * 13.0 / 5.0
                contract.l10n_be_mobility_budget_amount = min(mobility_budget_max, raw_mb)
            else:
                contract.l10n_be_mobility_budget_amount = 0.0

    @api.depends('l10n_be_mobility_budget_amount', 'wage_with_holidays')
    def _compute_l10n_be_mobility_budget_amount_monthly(self):
        for contract in self:
            contract.l10n_be_mobility_budget_amount_monthly = contract.l10n_be_mobility_budget_amount / 12

    @api.depends('l10n_be_mobility_budget', 'l10n_be_mobility_budget_amount', 'wage_with_holidays')
    def _compute_l10n_be_wage_with_mobility_budget(self):
        for contract in self:
            if contract._is_salary_sacrifice():
                yearly_cost = contract._get_yearly_cost_from_wage_with_holidays()
                contract.l10n_be_wage_with_mobility_budget = contract._get_gross_from_employer_costs(yearly_cost - contract.l10n_be_mobility_budget_amount)
            else:
                contract.l10n_be_wage_with_mobility_budget = contract._get_gross_from_employer_costs(contract.final_yearly_costs - contract.l10n_be_mobility_budget_amount)
