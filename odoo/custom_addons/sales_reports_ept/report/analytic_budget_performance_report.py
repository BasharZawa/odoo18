# -*- coding: utf-8 -*-

from odoo import fields, models, tools


class AnalyticBudgetPerformanceReport(models.Model):
    _name = 'analytic.budget.performance.report'
    _description = 'Analytic Budget Performance Report'
    _auto = False

    date = fields.Date('Date', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True)
    plan_id = fields.Many2one('account.analytic.plan', 'Analytic Plan', readonly=True)
    planned_amount = fields.Float('Budgeted Amount', readonly=True)
    actual_amount = fields.Float('Actual Sales', readonly=True)
    variance = fields.Float('Variance', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        plans = project_plan + other_plans

        planned_selects = []
        actual_selects = []
        for plan in plans:
            column_name = plan._column_name()
            planned_selects.append(
                """
                SELECT
                    bl.date_from AS date,
                    bl.\"%s\" AS analytic_account_id,
                    %s AS plan_id,
                    bl.budget_amount AS planned,
                    0.0 AS actual
                FROM budget_line bl
                WHERE bl.\"%s\" IS NOT NULL
                """ % (column_name, plan.id, column_name)
            )
            actual_selects.append(
                """
                SELECT
                    aal.date AS date,
                    aal.\"%s\" AS analytic_account_id,
                    %s AS plan_id,
                    0.0 AS planned,
                    -aal.amount AS actual
                FROM account_analytic_line aal
                WHERE aal.\"%s\" IS NOT NULL
                """ % (column_name, plan.id, column_name)
            )

        combined_union_sql = "\nUNION ALL\n".join(planned_selects + actual_selects)

        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    combined.date,
                    combined.analytic_account_id,
                    combined.plan_id,
                    SUM(combined.planned) AS planned_amount,
                    SUM(combined.actual) AS actual_amount,
                    SUM(combined.planned - combined.actual) AS variance
                FROM (
                    %s
                ) AS combined
                GROUP BY
                    combined.date,
                    combined.analytic_account_id,
                    combined.plan_id
            )
            """ % (self._table, combined_union_sql)
        )
