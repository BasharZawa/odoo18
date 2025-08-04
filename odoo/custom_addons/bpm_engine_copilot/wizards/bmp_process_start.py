# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json


class BmpProcessStart(models.TransientModel):
    _name = 'bmp.process.start'
    _description = 'Start BPMN Process Wizard'

    process_definition_id = fields.Many2one(
        'bmp.process.definition',
        string='Process Definition',
        required=True,
        domain=[('is_active', '=', True)]
    )
    
    related_record_model = fields.Char(
        string='Related Model',
        help='Model name of the related record'
    )
    
    related_record_id = fields.Integer(
        string='Related Record ID',
        help='ID of the related record'
    )
    
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Assigned User',
        help='User responsible for this process'
    )
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    initial_variables = fields.Text(
        string='Initial Variables',
        help='JSON format initial variables for the process'
    )
    
    auto_start = fields.Boolean(
        string='Auto Start',
        default=True,
        help='Automatically start the process after creation'
    )
    
    @api.model
    def default_get(self, fields):
        """Set default values"""
        defaults = super().default_get(fields)
        
        # If called from a specific record, set related record info
        if self.env.context.get('active_model') and self.env.context.get('active_id'):
            defaults['related_record_model'] = self.env.context['active_model']
            defaults['related_record_id'] = self.env.context['active_id']
        
        # Set default assigned user
        defaults['assigned_user_id'] = self.env.user.id
        
        return defaults
    
    def action_start_process(self):
        """Start the process"""
        self.ensure_one()
        
        # Validate initial variables JSON
        initial_vars = {}
        if self.initial_variables:
            try:
                initial_vars = json.loads(self.initial_variables)
            except json.JSONDecodeError:
                raise UserError(_("Initial variables must be valid JSON format"))
        
        # Create process instance
        instance_data = {
            'process_definition_id': self.process_definition_id.id,
            'assigned_user_id': self.assigned_user_id.id,
            'priority': self.priority,
            'state': 'draft'
        }
        
        if self.related_record_model and self.related_record_id:
            instance_data.update({
                'related_record_model': self.related_record_model,
                'related_record_id': self.related_record_id
            })
        
        process_instance = self.env['bmp.process.instance'].create(instance_data)
        
        # Set initial variables
        for key, value in initial_vars.items():
            var_type = 'string'
            if isinstance(value, bool):
                var_type = 'boolean'
            elif isinstance(value, int):
                var_type = 'integer'
            elif isinstance(value, float):
                var_type = 'float'
            elif isinstance(value, (dict, list)):
                var_type = 'json'
                value = json.dumps(value)
            
            process_instance.set_variable(key, value, var_type)
        
        # Start the process if auto_start is enabled
        if self.auto_start:
            process_instance.action_start()
        
        # Return action to view the created process instance
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Instance'),
            'res_model': 'bmp.process.instance',
            'res_id': process_instance.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_preview_variables(self):
        """Preview the initial variables"""
        self.ensure_one()
        
        if not self.initial_variables:
            raise UserError(_("No initial variables to preview"))
        
        try:
            variables = json.loads(self.initial_variables)
            preview_text = json.dumps(variables, indent=2)
        except json.JSONDecodeError as e:
            preview_text = f"Invalid JSON: {str(e)}"
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Variables Preview'),
            'res_model': 'bmp.process.start',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_preview_text': preview_text,
                'preview_mode': True
            }
        }
    
    @api.onchange('process_definition_id')
    def _onchange_process_definition(self):
        """When process definition changes, provide sample variables"""
        if self.process_definition_id:
            # TODO: Extract variable hints from BPMN XML
            sample_vars = {
                'requester': self.env.user.name,
                'request_date': fields.Date.today().isoformat(),
                'priority': self.priority
            }
            
            self.initial_variables = json.dumps(sample_vars, indent=2)