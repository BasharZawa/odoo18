from odoo import models, fields, _, api


class WorkcenterProductivityExtended(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    has_approvals = fields.Boolean(compute="_compute_has_approvals", store=False)

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        """
        Prevented functionality to update duration based on start and end dates.
        """
        pass
        # for blocktime in self:
            # if blocktime.date_start and blocktime.date_end:
                # blocktime.duration = blocktime.loss_id._convert_to_duration(blocktime.date_start.replace(microsecond=0), blocktime.date_end.replace(microsecond=0), blocktime.workcenter_id)
            # else:
            #     blocktime.duration = 0.0

    @api.onchange('duration')
    def _duration_changed(self):
        """
        Prevented functionality to update start date based on duration onchange.
        """
        if not self.date_end:
            return
        # self.date_start = self.date_end - timedelta(minutes=self.duration)
        self._loss_type_change()

    @api.onchange('date_start')
    def _date_start_changed(self):
        """
        Prevented functionality to update end date based on start dates onchange.
        """
        if not self.date_start:
            return
        # self.date_end = self.date_start + timedelta(minutes=self.duration)
        self._loss_type_change()

    @api.onchange('date_end')
    def _date_end_changed(self):
        """
        Prevented functionality to update start date based on end date onchange.
        """
        if not self.date_end:
            return
        # self.date_start = self.date_end - timedelta(minutes=self.duration)
        self._loss_type_change()

    # def write(self, vals):
    #     """
    #     Handle duration updates and trigger approval logic for supervisors.
    #     """
    #     if ('duration' in vals and
    #             self.env.user.has_group('mrp_extended_ept.timesheet_supervisor_group_user') and
    #             not self.env.context.get('from_approval')):
    #         for record in self:
    #             self._handle_approval_request(record, vals)
    #             for key in ['duration', 'date_end', 'date_start']:
    #                 if key in vals:
    #                     vals.pop(key)
    #     result = super(WorkcenterProductivityExtended, self).write(vals)
    #     return result
    #
    # def _handle_approval_request(self, record, vals):
    #     """
    #     Create or update an approval.request for the given productivity record.
    #     """
    #     # categ = self.env.ref('mrp_extended_ept.approval_type_time_tracking')
    #     categ = self.env['approval.category'].search([
    #         ('approval_type', '=', 'time_tracking_req'), ('company_id', '=', self.env.company.id)
    #     ], limit=1)
    #     if not categ:
    #         categ = self.env['approval.category'].sudo().create({
    #             'name': 'Time Tracking Missmatch Approval',
    #             'approver_ids': [],
    #             'approval_type': 'time_tracking_req',
    #             'company_id': self.env.company.id,
    #         })
    #     exist_rec = self._get_pending_approvals(record)
    #     if exist_rec:
    #         exist_rec.write({
    #             'timesheet_supervisor_hours': vals.get('duration'),
    #             'timesheet_hours': record.duration
    #         })
    #     else:
    #         new_approval = self._create_approval_request(record, categ, vals)
    #         new_approval.action_confirm()
    #
    # def _get_pending_approvals(self, record):
    #     """
    #     Return pending approval.request records for the current user and productivity record.
    #     """
    #     return self.env['approval.request'].search([
    #         ('request_status', '=', 'pending'),
    #         ('request_owner_id', '=', self.env.user.id),
    #         ('time_tracking_id', '=', record.id)
    #     ])
    #
    #
    # def _compute_has_approvals(self):
    #     """
    #     Compute boolean flag indicating if pending approvals exist for the record.
    #     """
    #     for record in self:
    #         approvals = self.env['approval.request'].search([
    #             ('request_owner_id', '=', self.env.user.id),
    #             ('time_tracking_id', '=', record.id),
    #             ('request_status', '=', 'pending')
    #         ])
    #         record.has_approvals = bool(approvals)
    #
    # def open_timesheet_approval_requests(self):
    #     """
    #     Return an action to open pending approval requests related to this productivity record.
    #     """
    #     approvals = self.env['approval.request'].search([
    #         ('request_owner_id', '=', self.env.user.id),
    #         ('request_status', '=', 'pending'),
    #         ('time_tracking_id', '=', self.id),
    #     ])
    #     action = {
    #         'name': _('Approvals'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'approval.request',
    #         'context': {'create': False},
    #     }
    #     if len(approvals) == 1:
    #         action.update({
    #             'view_mode': 'form',
    #             'res_id': approvals.id,
    #         })
    #     else:
    #         action.update({
    #             'view_mode': 'list,form,kanban',
    #             'domain': [('id', 'in', approvals.ids)],
    #         })
    #     return action
