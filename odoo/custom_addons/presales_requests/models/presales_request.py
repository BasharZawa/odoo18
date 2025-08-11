from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class PresalesRequest(models.Model):
    _name = 'presales.request'
    _description = 'Presales Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    opportunity_id = fields.Many2one('crm.lead', required=True, tracking=True)
    salesperson_id = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)
    assigned_to = fields.Many2one('res.users', tracking=True)
    state = fields.Selection([
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('amendment', 'Amendment'),
        ('completed', 'Completed'),
    ], default='requested', tracking=True)
    request_details = fields.Text(tracking=True)
    manager_comment = fields.Text()
    completion_notes = fields.Text()
    salesperson_feedback = fields.Text()
    deadline = fields.Datetime(string='SLA Deadline', tracking=True)
    timesheet_ids = fields.One2many('account.analytic.line', 'presales_request_id', string='Timesheets')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model_create_multi
    def create(self, vals_list):
        # Create records using the parent method
        records = super(PresalesRequest, self).create(vals_list)
        # Get the presales manager from roles
        presales_manager_group = self.env.ref('presales_requests.group_presales_manager')
        for record in records:
            record.assigned_to = presales_manager_group.users[:1]
            if record.assigned_to:
                record.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=record.assigned_to.id,  # Fixed: was self.assigned_to
                    summary="Review Presales Request",
                    note="Please review and approve or ignore the presales request."
                )
        return records


    def action_approve(self):
        #check if the presales manager is set as assigned_to
        presales_manager_group = self.env.ref('presales_requests.group_presales_manager')
        presales_manager_user = presales_manager_group.users[:1]
        presales_employee_group = self.env.ref('presales_requests.group_presales_employee')

        if self.assigned_to is presales_manager_user or self.assigned_to not in presales_employee_group.users:
            raise ValidationError("You must assign a presales employee from the presales team.")
        
        self.write({
            'state': 'approved',
        })

        #create an activity for the assigned presales employee
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.assigned_to.id,
            summary="Presales Request Assigned",
            note=f"You have been assigned to presales request: {self.name}."
        )

        # Mark previous manager's activity as done
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == presales_manager_user and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )

        activities.action_feedback(feedback="Presales request approved and assigned.")


        self.message_post(body="Presales request approved.")
   
        return True

    def action_reject(self):
        self.write({'state': 'rejected'})
        self.message_post(body="Presales request rejected.")
        presales_manager_group = self.env.ref('presales_requests.group_presales_manager')
        presales_manager_user = presales_manager_group.users[:1]

        #on manager rejection, mark all activities as done
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == presales_manager_user and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )
        activities.action_feedback(feedback="Presales request rejected.")
        
        return True

    def action_start(self):
        self.write({'state': 'in_progress'})
        self.message_post(body="Presales work has started.")
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == self.assigned_to and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )
        activities.action_feedback(feedback="Presales work started.")

        # Create an activity for the presales employee to complete the request
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.assigned_to.id,
            summary="Complete Presales Request",
            note=f"Please complete the presales request: {self.name}."
        )
        return True

    def action_submit_review(self):
        self.write({'state': 'review'})
        self.message_post(body="Presales work submitted for review.")
        # end the activity for the presales employee
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == self.assigned_to and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )
        activities.action_feedback(feedback="Presales request completed.")
        # Create an activity for the requstor to review the request
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.salesperson_id.id,  # Assinging the requester (salesperson) to review
            summary="Review Presales Request",
            note=f"Please review the presales request: {self.name}, and if Complete, mark it as Completed, otherwise request amendment."
        )
    

    def action_request_amendment(self):
        # user should be the sales person only
        if self.env.user != self.salesperson_id:
            raise ValidationError("Only the salesperson can request an amendment.")
        
        self.write({'state': 'amendment'})
        self.message_post(body="Salesperson requested an amendment.")
        # Create an activity for the presales employee whose the request to review the amendment request
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.assigned_to.id,  # Assuming the assigned presales employee will handle the amendment
            summary="Review Amendment Request",
            note=f"Please review the amendment request for presales request: {self.name}."
        )

        # finish activity for the salesperson
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == self.salesperson_id and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )
        activities.action_feedback(feedback="Amendment requested by salesperson.")

    def action_mark_complete(self):
        if self.env.user != self.salesperson_id:
            raise ValidationError("Only the salesperson can request an amendment.")
          
        self.write({'state': 'completed'})
        self.message_post(body="Presales request marked as completed.")
        # finish activity for the salesperson
        activities = self.activity_ids.filtered(
            lambda a: a.user_id == self.salesperson_id and a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )
        activities.action_feedback(feedback="Presales request completed.")


    