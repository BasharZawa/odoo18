from odoo import models, fields, api

class PresalesRequest(models.Model):
    _name = 'presales.request'
    _description = 'Prresalessss Request'

    name = fields.Char(string='Request Name', required=True)
    request_date = fields.Date(string='Request Date', default=fields.Date.today)
    description = fields.Text(string='Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')

    customer_name = fields.Char(string='Customer Name', required=True)
    customer_email = fields.Char(string='Customer Email')
    customer_phone = fields.Char(string='Customer Phone')
    project_scope = fields.Text(string='Project Scope')
    budget = fields.Float(string='Estimated Budget')
    deadline = fields.Date(string='Deadline')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Priority', default='medium')
    status = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='new')

    x_request_id = fields.Many2one('x.request', string='Related Request', readonly=True)

    @api.model
    def create(self, vals):
        # Automatically create a related XRequest instance
        x_request_vals = {
            'name': vals.get('name'),
            'description': vals.get('description'),
            'request_type': 'presales',
            'priority': vals.get('priority'),
            'requestor_id': self.env.uid
        }
        x_request = self.env['x.request'].create(x_request_vals)
        vals['x_request_id'] = x_request.id
        return super(PresalesRequest, self).create(vals)

    def action_submit(self):
        self.state = 'submitted'
        # Notify the presales department manager
        manager_group = self.env.ref('base.group_presales_manager')
        for user in manager_group.users:
            self.message_post(body=f"A new presales request '{self.name}' has been submitted.", partner_ids=[user.partner_id.id])

    def action_approve(self):
        self.state = 'approved'
        if self.x_request_id:
            self.x_request_id.action_manager_approve()

    def action_reject(self):
        self.state = 'rejected'
        if self.x_request_id:
            self.x_request_id.action_manager_reject()