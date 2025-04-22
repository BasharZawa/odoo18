# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'is_credit_time', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        mx_worked_days = self.filtered(lambda wd: wd.payslip_id.struct_id.country_id.code == "MX")
        for worked_days in mx_worked_days:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state not in ['draft', 'verify']:
                continue
            if not worked_days.contract_id or worked_days.code == 'OUT' or worked_days.is_credit_time:
                worked_days.amount = 0
                continue

            days_in_period = worked_days.payslip_id._rule_parameter('l10n_mx_schedule_table')[worked_days.payslip_id.contract_id.l10n_mx_schedule_pay]
            period_wage = worked_days.payslip_id.contract_id.wage * days_in_period / 30

            start_date = max(worked_days.payslip_id.date_from, worked_days.contract_id.date_start)
            end_date = min(worked_days.payslip_id.date_to, worked_days.contract_id.date_end) if worked_days.contract_id.date_end else worked_days.payslip_id.date_to
            in_contract_days = (end_date - start_date).days + 1
            actual_period_days = (worked_days.payslip_id.date_to - worked_days.payslip_id.date_from).days + 1
            salary_factor = in_contract_days / actual_period_days

            sum_worked_hours = sum(line.number_of_hours for line in worked_days.payslip_id.worked_days_line_ids if not line.is_credit_time and line.code != 'OUT')
            worked_days.amount = period_wage * salary_factor * worked_days.number_of_hours / (sum_worked_hours or 1) if worked_days.is_paid else 0
        return super(HrPayslipWorkedDays, self - mx_worked_days)._compute_amount()
