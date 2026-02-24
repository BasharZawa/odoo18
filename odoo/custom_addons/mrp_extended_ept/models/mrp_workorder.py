from odoo import models, fields, api, _
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons.mrp.models.mrp_workorder import MrpWorkorder


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

    def get_duration(self):
        """
        Overridden method: For custom duration computation of workorder from timesheet duration.
        """
        duration = 0
        for time in self.time_ids:
            duration += time.duration
        return duration

    def _cal_cost_replaced(self, date=False):
        """
        Replaced method: For custom cost computation of workorder from timesheet duration and
        workcenter cost per hour.
        """
        total = 0
        for workorder in self:
            duration = 0
            for time in workorder.time_ids:
                duration += time.duration
            total += (duration / 60) * workorder.workcenter_id.costs_hour
        return total

    def _set_duration_replaced(self):
        """
        Overridden method: Custom logic for restrict creating new time entries for backorders.
        """

        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duration = sum(order.time_ids.mapped('duration'))
            new_order_duration = order.duration
            if new_order_duration == old_order_duration:
                continue

            delta_duration = new_order_duration - old_order_duration

            if delta_duration > 0:
                if order.state not in ('progress', 'done', 'cancel'):
                    order.state = 'progress'
                enddate = fields.Datetime.now()
                date_start = enddate - timedelta(seconds=_float_duration_to_second(delta_duration))
                ######### OVERRIDE START #########
                all_mrp_recs = self.env['mrp.production'].search([
                    ('procurement_group_id', '=', order.production_id.procurement_group_id.id),
                    ('state', '!=', 'cancel')
                ], order='backorder_sequence asc')
                if all([mrp.backorder_sequence for mrp in all_mrp_recs]):
                    pass
                ######### OVERRIDE END #########
                elif order.duration_expected >= new_order_duration or old_order_duration >= order.duration_expected:
                    # either only productive or only performance (i.e. reduced speed) time respectively
                    self.env['mrp.workcenter.productivity'].create(
                        order._prepare_timeline_vals(new_order_duration, date_start, enddate)
                    )
                else:
                    # split between productive and performance (i.e. reduced speed) times
                    maxdate = fields.Datetime.from_string(enddate) - relativedelta(minutes=new_order_duration - order.duration_expected)
                    self.env['mrp.workcenter.productivity'].create([
                        order._prepare_timeline_vals(order.duration_expected, date_start, maxdate),
                        order._prepare_timeline_vals(new_order_duration, maxdate, enddate)
                    ])
            else:
                duration_to_remove = abs(delta_duration)
                timelines_to_unlink = self.env['mrp.workcenter.productivity']
                for timeline in order.time_ids.sorted():
                    if duration_to_remove <= 0.0:
                        break
                    if timeline.duration <= duration_to_remove:
                        duration_to_remove -= timeline.duration
                        timelines_to_unlink |= timeline
                    else:
                        new_time_line_duration = timeline.duration - duration_to_remove
                        timeline.date_start = timeline.date_end - timedelta(seconds=_float_duration_to_second(new_time_line_duration))
                        break
                timelines_to_unlink.unlink()

    MrpWorkorder._cal_cost = _cal_cost_replaced
    MrpWorkorder._set_duration = _set_duration_replaced
