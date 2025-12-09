from odoo import models, fields



class ApprovalRequestExtended(models.Model):
    _inherit = 'approval.request'

    has_supervisor = fields.Selection(related='category_id.has_supervisor', string="Has Supervisor")
    workorder_id = fields.Many2one(comodel_name='mrp.workorder', string='Manufacturing Work Order',
                                   ondelete='set null')
    timesheet_employee = fields.Many2one(comodel_name='hr.employee', string='Employee')
    timesheet_hours = fields.Float(string='Employee Timesheet Hours', default=0.0)
    timesheet_supervisor_hours = fields.Float(string='Supervisor hours')
    time_tracking_id = fields.Many2one(comodel_name='mrp.workcenter.productivity')

    def action_approve(self, approver=None):
        """
        Approve the request and update linked time-tracking duration when applicable.
        """
        res = super().action_approve(approver=approver)
        for approval in self:
            if approval.category_id == self.env.ref('mrp_extended_ept.approval_type_time_tracking'):
                time_track_rec = approval.time_tracking_id
                time_track_rec.with_context(from_approval=True).write({
                    'duration': approval.timesheet_supervisor_hours
                })
        return res
