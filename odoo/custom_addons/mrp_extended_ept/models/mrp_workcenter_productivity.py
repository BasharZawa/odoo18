from odoo import models, fields, _


class WorkcenterProductivityExtended(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    has_approvals = fields.Boolean(compute="_compute_has_approvals", store=False)

    def write(self, vals):
        """
        Handle duration updates and trigger approval logic for supervisors.
        """
        if ('duration' in vals and
                self.env.user.has_group('mrp_extended_ept.timesheet_supervisor_group_user') and
                not self.env.context.get('from_approval')):
            for record in self:
                self._handle_approval_request(record, vals)
                for key in ['duration', 'date_end', 'date_start']:
                    if key in vals:
                        vals.pop(key)
        result = super(WorkcenterProductivityExtended, self).write(vals)
        return result

    def _handle_approval_request(self, record, vals):
        """
        Create or update an approval.request for the given productivity record.
        """
        # categ = self.env.ref('mrp_extended_ept.approval_type_time_tracking')
        categ = self.env['approval.category'].search([
            ('approval_type', '=', 'time_tracking_req'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not categ:
            categ = self.env['approval.category'].sudo().create({
                'name': 'Time Tracking Missmatch Approval',
                'approver_ids': [],
                'approval_type': 'time_tracking_req',
                'company_id': self.env.company.id,
            })
        exist_rec = self._get_pending_approvals(record)
        if exist_rec:
            exist_rec.write({
                'timesheet_supervisor_hours': vals.get('duration'),
                'timesheet_hours': record.duration
            })
        else:
            new_approval = self._create_approval_request(record, categ, vals)
            new_approval.action_confirm()

    def _get_pending_approvals(self, record):
        """
        Return pending approval.request records for the current user and productivity record.
        """
        return self.env['approval.request'].search([
            ('request_status', '=', 'pending'),
            ('request_owner_id', '=', self.env.user.id),
            ('time_tracking_id', '=', record.id)
        ])

    def _create_approval_request(self, record, categ, vals):
        """
        Build data dict and create a new approval.request for the time-tracking record.
        """
        data = {
            'request_owner_id': self.env.user.id,
            'category_id': categ.id,
            'workorder_id': record.workorder_id.id,
            'time_tracking_id': record.id,
            'timesheet_hours': record.duration,
            'timesheet_employee': record.employee_id.id,
            'timesheet_supervisor_hours': vals.get('duration', 0.0),
        }
        approval = self.env['approval.request'].create(data)
        return approval

    def _compute_has_approvals(self):
        """
        Compute boolean flag indicating if pending approvals exist for the record.
        """
        for record in self:
            approvals = self.env['approval.request'].search([
                ('request_owner_id', '=', self.env.user.id),
                ('time_tracking_id', '=', record.id),
                ('request_status', '=', 'pending')
            ])
            record.has_approvals = bool(approvals)

    def open_timesheet_approval_requests(self):
        """
        Return an action to open pending approval requests related to this productivity record.
        """
        approvals = self.env['approval.request'].search([
            ('request_owner_id', '=', self.env.user.id),
            ('request_status', '=', 'pending'),
            ('time_tracking_id', '=', self.id),
        ])
        action = {
            'name': _('Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'context': {'create': False},
        }
        if len(approvals) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': approvals.id,
            })
        else:
            action.update({
                'view_mode': 'list,form,kanban',
                'domain': [('id', 'in', approvals.ids)],
            })
        return action
