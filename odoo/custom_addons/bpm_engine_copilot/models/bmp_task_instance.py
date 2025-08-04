# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class BmpTaskInstance(models.Model):
    _name = 'bmp.task.instance'
    _description = 'BPMN Task Instance'
    _order = 'created_at desc'
    _rec_name = 'task_name'

    process_instance_id = fields.Many2one(
        'bmp.process.instance',
        string='Process Instance',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    task_type = fields.Selection([
        ('user', 'User Task'),
        ('service', 'Service Task'),
        ('manual', 'Manual Task'),
        ('script', 'Script Task'),
        ('send', 'Send Task'),
        ('receive', 'Receive Task'),
        ('gateway', 'Gateway'),
        ('event', 'Event'),
    ], string='Task Type', required=True, default='user')
    
    task_name = fields.Char(
        string='Task Name',
        required=True,
        help='Name of the task from BPMN definition'
    )
    
    task_id = fields.Char(
        string='Task ID',
        required=True,
        help='Unique task identifier from BPMN definition'
    )
    
    status = fields.Selection([
        ('ready', 'Ready'),
        ('claimed', 'Claimed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('skipped', 'Skipped'),
    ], string='Status', default='ready', required=True, index=True)
    
    # Assignment fields
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned User',
        help='User assigned to this task'
    )
    
    assigned_group_id = fields.Many2one(
        'res.groups',
        string='Assigned Group',
        help='Group assigned to this task'
    )
    
    claimed_by_id = fields.Many2one(
        'res.users',
        string='Claimed By',
        help='User who claimed this task'
    )
    
    # Timing fields
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        readonly=True
    )
    
    started_at = fields.Datetime(
        string='Started At',
        help='When task execution started'
    )
    
    completed_at = fields.Datetime(
        string='Completed At',
        help='When task was completed'
    )
    
    due_date = fields.Datetime(
        string='Due Date',
        help='When this task is due'
    )
    
    # Task data and forms
    task_data = fields.Text(
        string='Task Data',
        help='JSON data for task configuration and variables'
    )
    
    form_data = fields.Text(
        string='Form Data',
        help='JSON data for dynamic form fields and values'
    )
    
    output_data = fields.Text(
        string='Output Data',
        help='JSON data for task output variables'
    )
    
    # Priority and SLA
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_overdue',
        store=True,
        help='Whether this task is overdue'
    )
    
    # Error handling
    error_message = fields.Text(
        string='Error Message',
        help='Error message if task failed'
    )
    
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Number of times this task has been retried'
    )
    
    max_retries = fields.Integer(
        string='Max Retries',
        default=3,
        help='Maximum number of retries allowed'
    )
    
    # Service task specific fields
    service_class = fields.Char(
        string='Service Class',
        help='Python class for service task execution'
    )
    
    service_method = fields.Char(
        string='Service Method',
        help='Python method for service task execution'
    )
    
    script_code = fields.Text(
        string='Script Code',
        help='Python code for script task execution'
    )
    
    # Computed fields
    duration = fields.Float(
        string='Duration (Hours)',
        compute='_compute_duration',
        help='Duration of task execution in hours'
    )
    
    can_claim = fields.Boolean(
        string='Can Claim',
        compute='_compute_can_claim',
        help='Whether current user can claim this task'
    )
    
    can_complete = fields.Boolean(
        string='Can Complete',
        compute='_compute_can_complete',
        help='Whether current user can complete this task'
    )
    
    # One2many relationships
    activity_logs = fields.One2many(
        'bmp.activity.log',
        'task_instance_id',
        string='Activity Logs'
    )
    
    task_variables = fields.One2many(
        'bmp.process.variable',
        'task_instance_id',
        string='Task Variables'
    )
    
    @api.depends('due_date', 'status')
    def _compute_overdue(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = (
                record.due_date and 
                record.due_date < now and 
                record.status not in ['completed', 'cancelled', 'failed', 'skipped']
            )
    
    @api.depends('started_at', 'completed_at')
    def _compute_duration(self):
        for record in self:
            if record.started_at:
                end_time = record.completed_at or fields.Datetime.now()
                delta = end_time - record.started_at
                record.duration = delta.total_seconds() / 3600  # Convert to hours
            else:
                record.duration = 0.0
    
    @api.depends('status', 'assigned_user_id', 'assigned_group_id')
    def _compute_can_claim(self):
        current_user = self.env.user
        for record in self:
            if record.status != 'ready':
                record.can_claim = False
            elif record.assigned_user_id:
                record.can_claim = record.assigned_user_id == current_user
            elif record.assigned_group_id:
                record.can_claim = record.assigned_group_id in current_user.groups_id
            else:
                record.can_claim = True  # Unassigned tasks can be claimed by anyone
    
    @api.depends('status', 'claimed_by_id', 'assigned_user_id')
    def _compute_can_complete(self):
        current_user = self.env.user
        for record in self:
            if record.status not in ['claimed', 'in_progress']:
                record.can_complete = False
            elif record.claimed_by_id:
                record.can_complete = record.claimed_by_id == current_user
            elif record.assigned_user_id:
                record.can_complete = record.assigned_user_id == current_user
            else:
                record.can_complete = True
    
    def action_claim(self):
        """Claim this task for the current user"""
        if not self.can_claim:
            raise UserError(_("You cannot claim this task"))
        
        if self.status != 'ready':
            raise UserError(_("Only ready tasks can be claimed"))
        
        self.write({
            'status': 'claimed',
            'claimed_by_id': self.env.user.id,
            'started_at': fields.Datetime.now(),
        })
        
        self._log_activity('claim', _("Task claimed by %s") % self.env.user.name)
        return True
    
    def action_start(self):
        """Start working on this task"""
        if self.status not in ['claimed', 'ready']:
            raise UserError(_("Only claimed or ready tasks can be started"))
        
        values = {
            'status': 'in_progress',
            'started_at': fields.Datetime.now(),
        }
        
        if self.status == 'ready':
            values['claimed_by_id'] = self.env.user.id
        
        self.write(values)
        self._log_activity('start', _("Task started by %s") % self.env.user.name)
        return True
    
    def action_complete(self, output_data=None):
        """Complete this task"""
        if not self.can_complete:
            raise UserError(_("You cannot complete this task"))
        
        if self.status not in ['claimed', 'in_progress']:
            raise UserError(_("Only claimed or in-progress tasks can be completed"))
        
        values = {
            'status': 'completed',
            'completed_at': fields.Datetime.now(),
        }
        
        if output_data:
            values['output_data'] = json.dumps(output_data)
        
        self.write(values)
        self._log_activity('complete', _("Task completed by %s") % self.env.user.name)
        
        # Continue process execution
        self._continue_process()
        
        return True
    
    def action_fail(self, error_message=None):
        """Mark this task as failed"""
        self.write({
            'status': 'failed',
            'completed_at': fields.Datetime.now(),
            'error_message': error_message or _("Task execution failed"),
        })
        
        self._log_activity('fail', error_message or _("Task failed"))
        
        # Handle retry logic
        if self.retry_count < self.max_retries:
            self._retry_task()
        else:
            # Fail the entire process if no more retries
            self.process_instance_id.action_fail(_("Task %s failed after %d retries") % (self.task_name, self.retry_count))
        
        return True
    
    def action_skip(self, reason=None):
        """Skip this task"""
        self.write({
            'status': 'skipped',
            'completed_at': fields.Datetime.now(),
        })
        
        self._log_activity('skip', reason or _("Task skipped"))
        self._continue_process()
        return True
    
    def action_delegate(self, user_id):
        """Delegate this task to another user"""
        if self.status not in ['ready', 'claimed']:
            raise UserError(_("Only ready or claimed tasks can be delegated"))
        
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise UserError(_("Invalid user for delegation"))
        
        self.write({
            'assigned_user_id': user_id,
            'status': 'ready',
            'claimed_by_id': False,
        })
        
        self._log_activity('delegate', _("Task delegated to %s") % user.name)
        return True
    
    def _retry_task(self):
        """Retry a failed task"""
        self.write({
            'status': 'ready',
            'retry_count': self.retry_count + 1,
            'error_message': False,
            'claimed_by_id': False,
            'started_at': False,
            'completed_at': False,
        })
        
        self._log_activity('retry', _("Task retry #%d") % self.retry_count)
    
    def _continue_process(self):
        """Continue process execution after task completion"""
        try:
            engine = self.env['bmp.execution.engine']
            engine.continue_process(self.process_instance_id, self)
        except Exception as e:
            _logger.error("Failed to continue process after task %s: %s", self.id, str(e))
            self.process_instance_id.action_fail(_("Failed to continue process: %s") % str(e))
    
    def _log_activity(self, action_type, details):
        """Log an activity for this task"""
        self.env['bmp.activity.log'].create({
            'process_instance_id': self.process_instance_id.id,
            'task_instance_id': self.id,
            'action_type': action_type,
            'timestamp': fields.Datetime.now(),
            'actor_id': self.env.user.id,
            'details': details,
        })
    
    def execute_service_task(self):
        """Execute a service task"""
        if self.task_type != 'service':
            raise UserError(_("This method can only be called on service tasks"))
        
        try:
            self.action_start()
            
            if self.script_code:
                # Execute Python script
                self._execute_script()
            elif self.service_class and self.service_method:
                # Execute service method
                self._execute_service_method()
            else:
                raise UserError(_("Service task has no execution configuration"))
            
            self.action_complete()
            
        except Exception as e:
            _logger.error("Service task execution failed: %s", str(e))
            self.action_fail(str(e))
    
    def _execute_script(self):
        """Execute Python script for script task"""
        # Create safe execution environment
        safe_globals = {
            'env': self.env,
            'task': self,
            'process': self.process_instance_id,
            'user': self.env.user,
            'context': self.env.context,
            'json': json,
            'logging': logging,
            '_': _,
        }
        
        # Execute the script
        exec(self.script_code, safe_globals)
    
    def _execute_service_method(self):
        """Execute service method for service task"""
        # Get the service class
        service_obj = self.env[self.service_class]
        
        # Get the method
        if not hasattr(service_obj, self.service_method):
            raise UserError(_("Service method '%s' not found in '%s'") % (self.service_method, self.service_class))
        
        method = getattr(service_obj, self.service_method)
        
        # Execute the method
        method(self)
    
    def get_form_data(self):
        """Get parsed form data"""
        if self.form_data:
            return json.loads(self.form_data)
        return {}
    
    def set_form_data(self, data):
        """Set form data"""
        self.form_data = json.dumps(data)
    
    def get_task_data(self):
        """Get parsed task data"""
        if self.task_data:
            return json.loads(self.task_data)
        return {}
    
    def set_task_data(self, data):
        """Set task data"""
        self.task_data = json.dumps(data)