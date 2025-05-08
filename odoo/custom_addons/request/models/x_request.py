from odoo import models, fields, api

class XRequest(models.Model):
    _name = 'x.request'  # Updated technical name to follow the naming convention
    _description = 'XRequest'

    name = fields.Char(string='Request Name', required=True)
    description = fields.Text(string='Description')
    request_type = fields.Selection([
        ('presales', 'Presales Request'),
        ('bpm_ticket', 'BPM Ticket')
    ], string='Request Type', required=True)
    task_id = fields.Many2one('task', string='Related Task')
    task_ids = fields.One2many('task', 'parent_task_id', string='Tasks')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('reopened', 'Reopened')
    ], default='draft', string='State')
    assigned_employee_id = fields.Many2one('res.users', string='Assigned Employee')
    requestor_id = fields.Many2one('res.users', string='Requestor')
    delivery_date = fields.Date(string='Delivery Date')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Priority')
    rating = fields.Integer(string='Rating')

    @api.model
    def create(self, vals):
        # Automatically create a related task when a request is created
        task_vals = {
            'name': f"Task for {vals.get('name')}",
            'state': 'pending'
        }
        task = self.env['task'].create(task_vals)
        vals['task_id'] = task.id
        return super(XRequest, self).create(vals)

    def _create_initial_tasks(self):
        # Example: Create parallel tasks
        task_vals = [
            {'name': f"Task 1 for {self.name}", 'parent_task_id': self.id},
            {'name': f"Task 2 for {self.name}", 'parent_task_id': self.id},
        ]
        for vals in task_vals:
            self.env['task'].create(vals)

    def _check_all_tasks_done(self):
        # Check if all tasks are completed
        return all(task.state == 'done' for task in self.task_ids)

    def _create_conditional_tasks(self):
        if self.request_type == 'presales':
            # Create a task for the presales department manager
            manager_task = self.env['task'].create({
                'name': f"Manager Approval for {self.name}",
                'parent_task_id': self.id,
                'state': 'pending',
                'assigned_to': self.env.ref('base.group_presales_manager').id  # Assign to presales manager group
            })

    def action_manager_approve(self):
        # Manager approves the request
        self.state = 'in_progress'
        # Create a task for the assigned employee
        employee_task = self.env['task'].create({
            'name': f"Set Estimated Delivery for {self.name}",
            'parent_task_id': self.id,
            'state': 'pending',
            'assigned_to': self.assigned_employee_id.id  # Assign to the selected employee
        })

    def action_manager_reject(self):
        # Manager rejects the request
        self.state = 'rejected'
        # Notify the requestor
        self.message_post(body=f"Your request '{self.name}' has been rejected.")

    def action_employee_set_delivery(self, delivery_date):
        # Employee sets the estimated delivery
        self.delivery_date = delivery_date
        if self.priority == 'high' and (delivery_date - fields.Date.today()).days > 7:
            # Raise escalation for high-priority tasks exceeding one week
            self.message_post(body=f"Escalation: High-priority request '{self.name}' has a delivery date exceeding one week.")

    def action_employee_complete_request(self):
        # Employee completes the request
        self.state = 'done'
        # Create a task for the requestor to rate the service
        self.env['task'].create({
            'name': f"Rate Service for {self.name}",
            'parent_task_id': self.id,
            'state': 'pending',
            'assigned_to': self.requestor_id.id  # Assign to the requestor
        })

    def action_requestor_rate_service(self, rating):
        # Requestor rates the service
        self.rating = rating
        if rating >= 4:
            # End process if rating is satisfactory
            self.state = 'completed'
        else:
            # Reopen the request if rating is unsatisfactory
            self.state = 'reopened'

    def action_progress(self):
        # Move to 'In Progress' if all tasks are created
        if self._check_all_tasks_done():
            self.state = 'in_progress'

    def action_done(self):
        # Move to 'Done' if all tasks are completed
        if self._check_all_tasks_done():
            self.state = 'done'