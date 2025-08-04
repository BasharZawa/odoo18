# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json
import logging

_logger = logging.getLogger(__name__)


class BmpActivityLog(models.Model):
    _name = 'bmp.activity.log'
    _description = 'BPMN Activity Log'
    _order = 'timestamp desc'
    _rec_name = 'display_name'

    process_instance_id = fields.Many2one(
        'bmp.process.instance',
        string='Process Instance',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    task_instance_id = fields.Many2one(
        'bmp.task.instance',
        string='Task Instance',
        ondelete='cascade',
        help='Task instance related to this activity (optional)'
    )
    
    action_type = fields.Selection([
        # Process actions
        ('start', 'Process Started'),
        ('complete', 'Process Completed'),
        ('fail', 'Process Failed'),
        ('cancel', 'Process Cancelled'),
        ('suspend', 'Process Suspended'),
        ('resume', 'Process Resumed'),
        
        # Task actions
        ('create_task', 'Task Created'),
        ('claim', 'Task Claimed'),
        ('start_task', 'Task Started'),
        ('complete_task', 'Task Completed'),
        ('fail_task', 'Task Failed'),
        ('skip', 'Task Skipped'),
        ('delegate', 'Task Delegated'),
        ('retry', 'Task Retried'),
        
        # Gateway actions
        ('gateway_evaluate', 'Gateway Evaluated'),
        ('gateway_split', 'Gateway Split'),
        ('gateway_merge', 'Gateway Merge'),
        
        # Event actions
        ('event_trigger', 'Event Triggered'),
        ('timer_start', 'Timer Started'),
        ('timer_trigger', 'Timer Triggered'),
        ('message_send', 'Message Sent'),
        ('message_receive', 'Message Received'),
        
        # Variable actions
        ('variable_set', 'Variable Set'),
        ('variable_get', 'Variable Retrieved'),
        
        # System actions
        ('system_error', 'System Error'),
        ('system_warning', 'System Warning'),
        ('system_info', 'System Information'),
        
        # User actions
        ('user_action', 'User Action'),
        ('assignment', 'Assignment Changed'),
        
    ], string='Action Type', required=True, index=True)
    
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    actor_id = fields.Many2one(
        'res.users',
        string='Actor',
        help='User who performed the action'
    )
    
    details = fields.Text(
        string='Details',
        help='Detailed description of the activity'
    )
    
    old_values = fields.Text(
        string='Old Values',
        help='JSON representation of old values before the action'
    )
    
    new_values = fields.Text(
        string='New Values',
        help='JSON representation of new values after the action'
    )
    
    # Additional context
    element_id = fields.Char(
        string='BPMN Element ID',
        help='ID of the BPMN element related to this activity'
    )
    
    element_name = fields.Char(
        string='BPMN Element Name',
        help='Name of the BPMN element related to this activity'
    )
    
    element_type = fields.Char(
        string='BPMN Element Type',
        help='Type of the BPMN element (task, gateway, event, etc.)'
    )
    
    # Categorization
    category = fields.Selection([
        ('process', 'Process'),
        ('task', 'Task'),
        ('gateway', 'Gateway'),
        ('event', 'Event'),
        ('variable', 'Variable'),
        ('system', 'System'),
        ('user', 'User'),
        ('assignment', 'Assignment'),
    ], string='Category', compute='_compute_category', store=True)
    
    level = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ], string='Level', default='info')
    
    # Display fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    actor_name = fields.Char(
        string='Actor Name',
        related='actor_id.name',
        store=True
    )
    
    # Search helpers
    search_text = fields.Text(
        string='Search Text',
        compute='_compute_search_text',
        store=True,
        help='Combined text for full-text search'
    )
    
    @api.depends('action_type')
    def _compute_category(self):
        action_category_map = {
            'start': 'process',
            'complete': 'process',
            'fail': 'process',
            'cancel': 'process',
            'suspend': 'process',
            'resume': 'process',
            'create_task': 'task',
            'claim': 'task',
            'start_task': 'task',
            'complete_task': 'task',
            'fail_task': 'task',
            'skip': 'task',
            'delegate': 'task',
            'retry': 'task',
            'gateway_evaluate': 'gateway',
            'gateway_split': 'gateway',
            'gateway_merge': 'gateway',
            'event_trigger': 'event',
            'timer_start': 'event',
            'timer_trigger': 'event',
            'message_send': 'event',
            'message_receive': 'event',
            'variable_set': 'variable',
            'variable_get': 'variable',
            'system_error': 'system',
            'system_warning': 'system',
            'system_info': 'system',
            'user_action': 'user',
            'assignment': 'assignment',
        }
        
        for record in self:
            record.category = action_category_map.get(record.action_type, 'system')
    
    @api.depends('action_type', 'element_name', 'timestamp')
    def _compute_display_name(self):
        for record in self:
            action_name = dict(record._fields['action_type'].selection).get(record.action_type, record.action_type)
            if record.element_name:
                record.display_name = f"{action_name} - {record.element_name}"
            else:
                record.display_name = action_name
    
    @api.depends('details', 'actor_name', 'element_name', 'old_values', 'new_values')
    def _compute_search_text(self):
        for record in self:
            text_parts = []
            if record.details:
                text_parts.append(record.details)
            if record.actor_name:
                text_parts.append(record.actor_name)
            if record.element_name:
                text_parts.append(record.element_name)
            if record.old_values:
                text_parts.append(record.old_values)
            if record.new_values:
                text_parts.append(record.new_values)
            
            record.search_text = ' '.join(text_parts)
    
    @api.model
    def log_activity(self, process_instance_id, action_type, details=None, **kwargs):
        """Convenience method to log an activity"""
        values = {
            'process_instance_id': process_instance_id,
            'action_type': action_type,
            'timestamp': fields.Datetime.now(),
            'actor_id': self.env.user.id,
            'details': details,
        }
        
        # Add optional fields from kwargs
        optional_fields = [
            'task_instance_id', 'old_values', 'new_values', 'element_id',
            'element_name', 'element_type', 'level'
        ]
        
        for field in optional_fields:
            if field in kwargs:
                values[field] = kwargs[field]
        
        # Convert dictionaries to JSON strings
        if 'old_values' in values and isinstance(values['old_values'], dict):
            values['old_values'] = json.dumps(values['old_values'])
        
        if 'new_values' in values and isinstance(values['new_values'], dict):
            values['new_values'] = json.dumps(values['new_values'])
        
        return self.create(values)
    
    @api.model
    def log_process_action(self, process_instance, action_type, details=None, **kwargs):
        """Log a process-level action"""
        return self.log_activity(
            process_instance.id,
            action_type,
            details,
            **kwargs
        )
    
    @api.model
    def log_task_action(self, task_instance, action_type, details=None, **kwargs):
        """Log a task-level action"""
        return self.log_activity(
            task_instance.process_instance_id.id,
            action_type,
            details,
            task_instance_id=task_instance.id,
            element_id=task_instance.task_id,
            element_name=task_instance.task_name,
            element_type='task',
            **kwargs
        )
    
    @api.model
    def log_system_event(self, process_instance, level, message, **kwargs):
        """Log a system event"""
        action_type_map = {
            'error': 'system_error',
            'warning': 'system_warning',
            'info': 'system_info',
        }
        
        return self.log_activity(
            process_instance.id,
            action_type_map.get(level, 'system_info'),
            message,
            level=level,
            **kwargs
        )
    
    @api.model
    def log_variable_change(self, process_instance, variable_key, old_value, new_value, task_instance=None):
        """Log a variable change"""
        old_values = {variable_key: old_value} if old_value is not None else {}
        new_values = {variable_key: new_value}
        
        kwargs = {
            'old_values': old_values,
            'new_values': new_values,
            'element_name': variable_key,
        }
        
        if task_instance:
            kwargs['task_instance_id'] = task_instance.id
        
        return self.log_activity(
            process_instance.id,
            'variable_set',
            f"Variable '{variable_key}' changed",
            **kwargs
        )
    
    def get_old_values(self):
        """Get parsed old values"""
        if self.old_values:
            try:
                return json.loads(self.old_values)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def get_new_values(self):
        """Get parsed new values"""
        if self.new_values:
            try:
                return json.loads(self.new_values)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def action_view_process(self):
        """View the related process instance"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Instance'),
            'res_model': 'bmp.process.instance',
            'res_id': self.process_instance_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_task(self):
        """View the related task instance"""
        if not self.task_instance_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task Instance'),
            'res_model': 'bmp.task.instance',
            'res_id': self.task_instance_id.id,
            'view_mode': 'form',
            'target': 'current',
        }