from odoo import models, fields, api
from datetime import timedelta


class MrpWorkorderExtended(models.Model):
    _inherit = 'mrp.workorder'

    workorder_sequence = fields.Char(string='Workorder Sequence', copy=False, readonly=True,
                                     default=lambda self: self.env['ir.sequence'].next_by_code('mrp.workorder.sequence'))
    schedule_date_finished = fields.Datetime(compute='_compute_schedule_date_finished', store=False)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id",
                                  string='Currency', help="Main currency of the company.")
    avg_labor_cost = fields.Monetary(string='Avg. Labor Cost per Piece', currency_field='currency_id',
                                  compute='_compute_avg_labor_per_piece', store=True)



    @api.depends('date_start', 'duration_expected')
    def _compute_schedule_date_finished(self):
        """
        compute expected finish datetime from `date_start` and `duration_expected`
        :return: None
        """
        for rec in self:
            if rec.duration_expected and rec.date_start:
                rec.schedule_date_finished = rec.date_start + timedelta(minutes=rec.duration_expected)
            else:
                rec.schedule_date_finished = False

    @api.depends('time_ids.total_cost', 'qty_produced')
    def _compute_avg_labor_per_piece(self):
        """
        compute average labor cost per piece
        :return: None
        """
        for rec in self:
            total_labor_cost = sum(rec.time_ids.mapped('total_cost'))
            if rec.qty_producing:
                rec.avg_labor_cost = total_labor_cost / rec.qty_producing
