# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class BmpProcessInstance(models.Model):
    _name = 'bmp.process.instance'
    _description = 'BPMN Process Instance'
    _order = 'started_at desc'
    _rec_name = 'display_name'

    process_definition_id = fields.Many2one(
        'bmp.process.definition',
        string='Process Definition',
        required=True,
        ondelete='cascade',
        help='The process definition this instance is based on'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ], string='State', default='draft', required=True, index=True)
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    started_at = fields.Datetime(
        string='Started At',
        help='When the process instance was started'
    )
    
    ended_at = fields.Datetime(
        string='Ended At',
        help='When the process instance completed, failed, or was cancelled'
    )
    
    # Related record tracking
    related_record_model = fields.Char(
        string='Related Model',
        help='Model name of the related Odoo record'
    )
    
    related_record_id = fields.Integer(
        string='Related Record ID',
        help='ID of the related Odoo record'
    )
    
    related_record_name = fields.Char(
        string='Related Record',
        compute='_compute_related_record_name'
    )
    
    # Current state tracking
    current_activity = fields.Char(
        string='Current Activity',
        help='Current activity in the process'
    )
    
    progress_percentage = fields.Float(
        string='Progress (%)',
        compute='_compute_progress',
        help='Completion percentage of the process'
    )
    
    # User tracking
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned User',
        help='User responsible for this process instance'
    )
    
    # Process data
    process_data = fields.Text(
        string='Process Data',
        help='JSON data for process variables and context'
    )
    
    error_message = fields.Text(
        string='Error Message',
        help='Error message if process failed'
    )
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    # One2many relationships
    task_instances = fields.One2many(
        'bmp.task.instance',
        'process_instance_id',
        string='Task Instances'
    )
    
    activity_logs = fields.One2many(
        'bmp.activity.log',
        'process_instance_id',
        string='Activity Logs'
    )
    
    process_variables = fields.One2many(
        'bmp.process.variable',
        'process_instance_id',
        string='Process Variables'
    )
    
    # Computed statistics
    total_tasks = fields.Integer(
        string='Total Tasks',
        compute='_compute_task_statistics'
    )
    
    completed_tasks = fields.Integer(
        string='Completed Tasks',
        compute='_compute_task_statistics'
    )
    
    active_tasks = fields.Integer(
        string='Active Tasks',
        compute='_compute_task_statistics'
    )
    
    duration = fields.Float(
        string='Duration (Hours)',
        compute='_compute_duration',
        help='Duration of the process instance in hours'
    )
    
    @api.depends('process_definition_id.name', 'id')
    def _compute_display_name(self):
        for record in self:
            if record.process_definition_id:
                record.display_name = f"{record.process_definition_id.name} #{record.id}"
            else:
                record.display_name = f"Process Instance #{record.id}"
    
    @api.depends('related_record_model', 'related_record_id')
    def _compute_related_record_name(self):
        for record in self:
            if record.related_record_model and record.related_record_id:
                try:
                    related_record = self.env[record.related_record_model].browse(record.related_record_id)
                    if related_record.exists():
                        record.related_record_name = related_record.display_name
                    else:
                        record.related_record_name = _("Record not found")
                except:
                    record.related_record_name = _("Invalid record")
            else:
                record.related_record_name = ""
    
    @api.depends('task_instances.status')
    def _compute_task_statistics(self):
        for record in self:
            tasks = record.task_instances
            record.total_tasks = len(tasks)
            record.completed_tasks = len(tasks.filtered(lambda t: t.status == 'completed'))
            record.active_tasks = len(tasks.filtered(lambda t: t.status in ['ready', 'claimed', 'in_progress']))
    
    @api.depends('total_tasks', 'completed_tasks')
    def _compute_progress(self):
        for record in self:
            if record.total_tasks > 0:
                record.progress_percentage = (record.completed_tasks / record.total_tasks) * 100
            else:
                record.progress_percentage = 0.0
    
    @api.depends('started_at', 'ended_at')
    def _compute_duration(self):
        for record in self:
            if record.started_at:
                end_time = record.ended_at or fields.Datetime.now()
                delta = end_time - record.started_at
                record.duration = delta.total_seconds() / 3600  # Convert to hours
            else:
                record.duration = 0.0
    
    def action_start(self):
        """Start the process instance"""
        if self.state != 'draft':
            raise UserError(_("Only draft process instances can be started"))
        
        self.write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
        })
        
        # Log the start action
        self._log_activity('start', _("Process instance started"))
        
        # Initialize process execution
        self._initialize_process()
        
        return True
    
    def action_suspend(self):
        """Suspend the process instance"""
        if self.state != 'running':
            raise UserError(_("Only running process instances can be suspended"))
        
        self.write({'state': 'suspended'})
        self._log_activity('suspend', _("Process instance suspended"))
        return True
    
    def action_resume(self):
        """Resume the process instance"""
        if self.state != 'suspended':
            raise UserError(_("Only suspended process instances can be resumed"))
        
        self.write({'state': 'running'})
        self._log_activity('resume', _("Process instance resumed"))
        return True
    
    def action_cancel(self):
        """Cancel the process instance"""
        if self.state in ['completed', 'failed', 'cancelled']:
            raise UserError(_("Cannot cancel completed, failed, or already cancelled process"))
        
        self.write({
            'state': 'cancelled',
            'ended_at': fields.Datetime.now(),
        })
        
        # Cancel active tasks
        active_tasks = self.task_instances.filtered(lambda t: t.status in ['ready', 'claimed', 'in_progress'])
        active_tasks.write({'status': 'cancelled'})
        
        self._log_activity('cancel', _("Process instance cancelled"))
        return True
    
    def action_complete(self):
        """Mark the process instance as completed"""
        if self.state != 'running':
            raise UserError(_("Only running process instances can be completed"))
        
        self.write({
            'state': 'completed',
            'ended_at': fields.Datetime.now(),
        })
        
        self._log_activity('complete', _("Process instance completed"))
        return True
    
    def action_fail(self, error_message=None):
        """Mark the process instance as failed"""
        self.write({
            'state': 'failed',
            'ended_at': fields.Datetime.now(),
            'error_message': error_message or _("Process execution failed"),
        })
        
        self._log_activity('fail', error_message or _("Process instance failed"))
        return True
    
    def _initialize_process(self):
        """Initialize process execution by creating initial tasks"""
        try:
            # Get the execution engine
            engine = self.env['bmp.execution.engine']
            engine.initialize_process(self)
            
        except Exception as e:
            _logger.error("Failed to initialize process %s: %s", self.id, str(e))
            self.action_fail(_("Failed to initialize process: %s") % str(e))
    
    def _log_activity(self, action_type, details):
        """Log an activity for this process instance"""
        self.env['bmp.activity.log'].create({
            'process_instance_id': self.id,
            'action_type': action_type,
            'timestamp': fields.Datetime.now(),
            'actor_id': self.env.user.id,
            'details': details,
        })
    
    def set_variable(self, key, value, var_type='string'):
        """Set a process variable"""
        existing_var = self.process_variables.filtered(lambda v: v.key == key and v.scope == 'global')
        
        if existing_var:
            existing_var.write({
                'value': str(value),
                'type': var_type,
            })
        else:
            self.env['bmp.process.variable'].create({
                'process_instance_id': self.id,
                'key': key,
                'value': str(value),
                'type': var_type,
                'scope': 'global',
            })
    
    def get_variable(self, key, default=None):
        """Get a process variable value"""
        var = self.process_variables.filtered(lambda v: v.key == key and v.scope == 'global')
        if var:
            return var[0].get_typed_value()
        return default
    
    def action_view_tasks(self):
        """View all tasks of this process instance"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Tasks'),
            'res_model': 'bmp.task.instance',
            'view_mode': 'tree,form',
            'domain': [('process_instance_id', '=', self.id)],
            'context': {'default_process_instance_id': self.id},
        }
    
    def action_view_logs(self):
        """View activity logs for this process instance"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Activity Logs'),
            'res_model': 'bmp.activity.log',
            'view_mode': 'tree,form',
            'domain': [('process_instance_id', '=', self.id)],
        }