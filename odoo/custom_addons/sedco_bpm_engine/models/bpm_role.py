from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class BpmRole(models.Model):
    _name = "bpm.role"
    _description = "BPM Role"
    _rec_name = "name"
    _order = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, help="Role name (e.g., Manager, Team Lead, Approver)")
    code = fields.Char(required=True, help="Unique code for this role (e.g., MGR, TL, APP)")
    description = fields.Text(help="Description of this role's responsibilities")
    active = fields.Boolean(default=True)
    
    # Assignment
    user_id = fields.Many2one(
        'res.users',
        string="Assigned User",
        required=True,
        default=lambda self: self.env.user,
        domain=[('active', '=', True)],
        help="Current user assigned to this role",
        tracking=True,
    )
    backup_user_id = fields.Many2one('res.users', string="Backup User",
                                    help="Backup user who can act when main user is unavailable", tracking=True)
    
    # Department/Company context
    department_id = fields.Many2one('hr.department', string="Department",
                                   help="Department this role belongs to")
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="Company this role is valid for",
    )
    
    # Configuration
    escalation_timeout = fields.Integer(string="Escalation Timeout (Hours)", default=24,
                                       help="Hours after which tasks escalate to backup user")
    auto_assign = fields.Boolean(string="Auto Assign", default=True,
                                help="Automatically assign tasks to this role")
    
    # Statistics
    task_count = fields.Integer(string="Active Tasks", compute="_compute_task_count", store=True)
    
    # History tracking
    assignment_history_ids = fields.One2many('bpm.role.assignment.history', 'role_id', 
                                            string="Assignment History")
    
    _sql_constraints = [
        ('code_company_unique', 'unique(code, company_id)', 
         'Role code must be unique within a company.'),
        ('name_company_unique', 'unique(name, company_id)', 
         'Role name must be unique within a company.')
    ]
    
    # Compute the number of active tasks assigned to this role's current assignee.
    @api.depends('user_id')
    def _compute_task_count(self):
        for role in self:
            # For new (unsaved) records, avoid querying by a temporary/unknown id
            if not role.exists():
                role.task_count = 0
                continue

            if role.user_id:
                # Count activity instances assigned to this role that are active
                count = self.env['activity.instance'].search_count([
                    ('assignee_role_id', '=', role.id),
                    ('status', 'in', ['ready', 'waiting', 'active'])
                ])
                role.task_count = count
            else:
                role.task_count = 0
    
    # Ensure main user and backup user are not the same.
    @api.constrains('user_id', 'backup_user_id')
    def _check_users(self):
        for role in self:
            if role.user_id and role.backup_user_id and role.user_id == role.backup_user_id:
                raise ValidationError(_("Main user and backup user cannot be the same."))
    
    # Override write to track assignment history when user changes.
    def write(self, vals):
        if 'user_id' in vals:
            for role in self:
                # Skip for non-persistent records
                if not role.exists():
                    continue

                new_user_id = vals.get('user_id')
                if role.user_id and new_user_id and role.user_id.id != new_user_id:
                    # Create history record for the change
                    self.env['bpm.role.assignment.history'].create({
                        'role_id': role.id,
                        'old_user_id': role.user_id.id,
                        'new_user_id': new_user_id,
                        'change_date': fields.Datetime.now(),
                        'change_reason': 'Manual assignment change'
                    })
        return super().write(vals)
    
    # Get the current assignee for this role, considering backup if needed.
    def get_current_assignee(self, check_availability=True):
        self.ensure_one()
        
        if not check_availability:
            return self.user_id
            
        # Check if main user is available (you can extend this logic)
        # For now, always return main user, but this could check:
        # - User is active
        # - User is not on leave (if hr_holidays is installed)
        # - User has not exceeded escalation timeout
        
        if self.user_id and self.user_id.active:
            return self.user_id
        elif self.backup_user_id and self.backup_user_id.active:
            return self.backup_user_id
        else:
            return self.user_id  # Fallback to main user even if inactive
    
    # Reassign this role to a new user and update all related tasks.
    def reassign_role(self, new_user_id, reason=""):
        self.ensure_one()
        
        if not new_user_id:
            raise ValidationError(_("New user is required for role reassignment."))
            
        old_user = self.user_id
        new_user = self.env['res.users'].browse(new_user_id)
        
        # Create history record
        self.env['bpm.role.assignment.history'].create({
            'role_id': self.id,
            'old_user_id': old_user.id if old_user else False,
            'new_user_id': new_user_id,
            'change_date': fields.Datetime.now(),
            'change_reason': reason or 'Role reassignment'
        })
        
        # Update the role
        self.write({'user_id': new_user_id})
        
        # Update all pending activity instances assigned to this role
        pending_activities = self.env['activity.instance'].search([
            ('assignee_role_id', '=', self.id),
            ('status', 'in', ['ready', 'waiting'])
        ])
        
        if pending_activities:
            pending_activities.write({'assignee_id': new_user_id})
            
            # Update related mail activities
            mail_activities = self.env['mail.activity'].search([
                ('res_model', '=', 'process.instance'),
                ('res_id', 'in', pending_activities.mapped('proc_id.id')),
                ('user_id', '=', old_user.id if old_user else False)
            ])
            mail_activities.write({'user_id': new_user_id})
        
        return {
            'reassigned_activities': len(pending_activities),
            'old_user': old_user.name if old_user else 'None',
            'new_user': new_user.name
        }
    
    # Open the tasks assigned to this role.
    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Tasks - {self.name}',
            'res_model': 'activity.instance',
            'view_mode': 'tree,form',
            'domain': [('assignee_role_id', '=', self.id), ('status', 'in', ['ready', 'waiting'])],
            'context': {'default_assignee_role_id': self.id},
            'target': 'current',
        }


class BmpRoleAssignmentHistory(models.Model):
    _name = "bpm.role.assignment.history"
    _description = "BPM Role Assignment History"
    _order = "change_date desc"
    
    role_id = fields.Many2one('bpm.role', required=True, ondelete='cascade')
    old_user_id = fields.Many2one('res.users', string="Previous User")
    new_user_id = fields.Many2one('res.users', string="New User")
    change_date = fields.Datetime(required=True, default=fields.Datetime.now)
    change_reason = fields.Text(string="Reason for Change")
    created_by = fields.Many2one('res.users', string="Changed By", 
                                default=lambda self: self.env.user)
