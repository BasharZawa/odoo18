# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json


class BmpTaskComplete(models.TransientModel):
    _name = 'bmp.task.complete'
    _description = 'Complete BPMN Task Wizard'

    task_instance_id = fields.Many2one(
        'bmp.task.instance',
        string='Task Instance',
        required=True,
        readonly=True
    )
    
    task_name = fields.Char(
        string='Task Name',
        related='task_instance_id.task_name',
        readonly=True
    )
    
    process_instance_id = fields.Many2one(
        'bmp.process.instance',
        string='Process Instance',
        related='task_instance_id.process_instance_id',
        readonly=True
    )
    
    completion_comment = fields.Text(
        string='Completion Comment',
        help='Optional comment about task completion'
    )
    
    output_data = fields.Text(
        string='Output Data',
        help='JSON format output data for the task'
    )
    
    # Dynamic form fields will be added based on task form schema
    
    @api.model
    def default_get(self, fields):
        """Set default values"""
        defaults = super().default_get(fields)
        
        # Get task from context
        task_id = self.env.context.get('active_id')
        if task_id:
            task = self.env['bmp.task.instance'].browse(task_id)
            if task.exists():
                defaults['task_instance_id'] = task.id
                
                # Pre-populate with existing form data
                form_data = task.get_form_data()
                if form_data:
                    defaults['output_data'] = json.dumps(form_data, indent=2)
        
        return defaults
    
    def action_complete_task(self):
        """Complete the task"""
        self.ensure_one()
        
        if not self.task_instance_id.can_complete:
            raise UserError(_("You cannot complete this task"))
        
        # Prepare output data
        output_data = {}
        
        # Add completion comment if provided
        if self.completion_comment:
            output_data['completion_comment'] = self.completion_comment
        
        # Parse and merge output data from JSON field
        if self.output_data:
            try:
                json_data = json.loads(self.output_data)
                output_data.update(json_data)
            except json.JSONDecodeError:
                raise UserError(_("Output data must be valid JSON format"))
        
        # Complete the task
        self.task_instance_id.action_complete(output_data)
        
        # Return action to view the process instance
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Instance'),
            'res_model': 'bmp.process.instance',
            'res_id': self.process_instance_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_save_and_continue(self):
        """Save output data without completing the task"""
        self.ensure_one()
        
        # Update task form data
        output_data = {}
        
        if self.completion_comment:
            output_data['completion_comment'] = self.completion_comment
        
        if self.output_data:
            try:
                json_data = json.loads(self.output_data)
                output_data.update(json_data)
            except json.JSONDecodeError:
                raise UserError(_("Output data must be valid JSON format"))
        
        # Update task form data
        current_form_data = self.task_instance_id.get_form_data()
        current_form_data.update(output_data)
        self.task_instance_id.set_form_data(current_form_data)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Saved'),
                'message': _('Task data saved successfully'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_preview_output(self):
        """Preview the output data"""
        self.ensure_one()
        
        output_data = {}
        
        if self.completion_comment:
            output_data['completion_comment'] = self.completion_comment
        
        if self.output_data:
            try:
                json_data = json.loads(self.output_data)
                output_data.update(json_data)
                preview_text = json.dumps(output_data, indent=2)
            except json.JSONDecodeError as e:
                preview_text = f"Invalid JSON: {str(e)}"
        else:
            preview_text = json.dumps(output_data, indent=2)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Output Data Preview'),
            'res_model': 'bmp.task.complete',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_text': preview_text,
                'preview_mode': True
            }
        }
    
    @api.onchange('task_instance_id')
    def _onchange_task_instance(self):
        """When task changes, load its form data"""
        if self.task_instance_id:
            form_data = self.task_instance_id.get_form_data()
            if form_data:
                self.output_data = json.dumps(form_data, indent=2)