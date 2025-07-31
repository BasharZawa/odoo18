# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class BmpIntegration(models.Model):
    _name = 'bmp.integration'
    _description = 'BPMN Odoo Model Integration'
    _order = 'name'

    name = fields.Char(
        string='Integration Name',
        required=True,
        help='Name of the integration configuration'
    )
    
    model_name = fields.Char(
        string='Model Name',
        required=True,
        help='Technical name of the Odoo model (e.g., crm.lead)'
    )
    
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        compute='_compute_model_id',
        store=True,
        help='Odoo model object'
    )
    
    process_definition_id = fields.Many2one(
        'bmp.process.definition',
        string='Process Definition',
        required=True,
        help='Process to trigger when model events occur'
    )
    
    # Trigger configuration
    trigger_on_create = fields.Boolean(
        string='Trigger on Create',
        default=True,
        help='Trigger process when a new record is created'
    )
    
    trigger_on_write = fields.Boolean(
        string='Trigger on Write',
        default=False,
        help='Trigger process when a record is updated'
    )
    
    trigger_on_unlink = fields.Boolean(
        string='Trigger on Delete',
        default=False,
        help='Trigger process when a record is deleted'
    )
    
    # Conditions
    trigger_condition = fields.Text(
        string='Trigger Condition',
        help='Python expression to evaluate if process should be triggered'
    )
    
    field_filters = fields.Text(
        string='Field Filters',
        help='JSON configuration for field-based filters'
    )
    
    # Data mapping
    variable_mapping = fields.Text(
        string='Variable Mapping',
        help='JSON mapping of Odoo fields to process variables'
    )
    
    # State
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this integration is active'
    )
    
    # Statistics
    trigger_count = fields.Integer(
        string='Trigger Count',
        default=0,
        help='Number of times this integration has been triggered'
    )
    
    last_triggered = fields.Datetime(
        string='Last Triggered',
        help='When this integration was last triggered'
    )
    
    # Configuration
    auto_start = fields.Boolean(
        string='Auto Start Process',
        default=True,
        help='Automatically start the process instance after creation'
    )
    
    single_instance = fields.Boolean(
        string='Single Instance per Record',
        default=True,
        help='Only allow one process instance per record'
    )
    
    @api.depends('model_name')
    def _compute_model_id(self):
        for record in self:
            if record.model_name:
                model = self.env['ir.model'].search([('model', '=', record.model_name)], limit=1)
                record.model_id = model.id if model else False
            else:
                record.model_id = False
    
    def evaluate_trigger_condition(self, record, operation='create'):
        """Evaluate if the trigger condition is met"""
        if not self.trigger_condition:
            return True
        
        try:
            # Create safe evaluation context
            context = {
                'record': record,
                'operation': operation,
                'env': record.env,
                'user': record.env.user,
                'fields': record.env[self.model_name]._fields,
            }
            
            result = eval(self.trigger_condition, {"__builtins__": {}}, context)
            return bool(result)
        except Exception as e:
            _logger.error("Error evaluating trigger condition for integration %s: %s", self.name, str(e))
            return False
    
    def check_field_filters(self, record, old_values=None):
        """Check if field filters are satisfied"""
        if not self.field_filters:
            return True
        
        try:
            filters = json.loads(self.field_filters)
            
            for field_name, conditions in filters.items():
                field_value = getattr(record, field_name, None)
                
                # Check various filter conditions
                if 'equals' in conditions and field_value != conditions['equals']:
                    return False
                
                if 'in' in conditions and field_value not in conditions['in']:
                    return False
                
                if 'changed' in conditions and conditions['changed']:
                    if not old_values or field_name not in old_values:
                        return False
                    if old_values[field_name] == field_value:
                        return False
                
                # Add more filter types as needed
            
            return True
            
        except (json.JSONDecodeError, AttributeError) as e:
            _logger.error("Error checking field filters for integration %s: %s", self.name, str(e))
            return True  # Default to allowing trigger if filter parsing fails
    
    def get_variable_mapping(self, record):
        """Get process variables from record based on variable mapping"""
        if not self.variable_mapping:
            return {}
        
        try:
            mapping = json.loads(self.variable_mapping)
            variables = {}
            
            for var_name, field_config in mapping.items():
                if isinstance(field_config, str):
                    # Simple field mapping
                    field_value = getattr(record, field_config, None)
                    variables[var_name] = field_value
                elif isinstance(field_config, dict):
                    # Complex mapping with type and transformation
                    field_name = field_config.get('field')
                    var_type = field_config.get('type', 'string')
                    transform = field_config.get('transform')
                    
                    if field_name:
                        field_value = getattr(record, field_name, None)
                        
                        # Apply transformation if specified
                        if transform and field_value:
                            if transform == 'display_name' and hasattr(field_value, 'display_name'):
                                field_value = field_value.display_name
                            elif transform == 'id' and hasattr(field_value, 'id'):
                                field_value = field_value.id
                            # Add more transformations as needed
                        
                        variables[var_name] = {
                            'value': field_value,
                            'type': var_type
                        }
            
            return variables
            
        except (json.JSONDecodeError, AttributeError) as e:
            _logger.error("Error mapping variables for integration %s: %s", self.name, str(e))
            return {}
    
    def trigger_process(self, record, operation='create', old_values=None):
        """Trigger the process for the given record"""
        if not self.is_active:
            return False
        
        # Check if we should trigger based on operation
        if operation == 'create' and not self.trigger_on_create:
            return False
        elif operation == 'write' and not self.trigger_on_write:
            return False
        elif operation == 'unlink' and not self.trigger_on_unlink:
            return False
        
        # Evaluate trigger condition
        if not self.evaluate_trigger_condition(record, operation):
            return False
        
        # Check field filters
        if not self.check_field_filters(record, old_values):
            return False
        
        # Check for existing instance if single_instance is enabled
        if self.single_instance and operation != 'unlink':
            existing_instance = self.env['bmp.process.instance'].search([
                ('process_definition_id', '=', self.process_definition_id.id),
                ('related_record_model', '=', self.model_name),
                ('related_record_id', '=', record.id),
                ('state', 'in', ['draft', 'running', 'suspended'])
            ], limit=1)
            
            if existing_instance:
                _logger.info("Skipping process trigger - existing active instance found for %s %d", self.model_name, record.id)
                return False
        
        # Create process instance
        process_instance = self.env['bmp.process.instance'].create({
            'process_definition_id': self.process_definition_id.id,
            'related_record_model': self.model_name,
            'related_record_id': record.id,
            'state': 'draft',
        })
        
        # Set process variables from mapping
        variables = self.get_variable_mapping(record)
        for var_name, var_config in variables.items():
            if isinstance(var_config, dict):
                process_instance.set_variable(var_name, var_config['value'], var_config['type'])
            else:
                process_instance.set_variable(var_name, var_config)
        
        # Set additional context variables
        process_instance.set_variable('trigger_operation', operation)
        process_instance.set_variable('trigger_integration', self.name)
        process_instance.set_variable('source_record_id', record.id)
        process_instance.set_variable('source_model', self.model_name)
        
        # Auto-start if configured
        if self.auto_start:
            process_instance.action_start()
        
        # Update statistics
        self.write({
            'trigger_count': self.trigger_count + 1,
            'last_triggered': fields.Datetime.now(),
        })
        
        # Log the trigger
        self.env['bmp.activity.log'].log_activity(
            process_instance.id,
            'system_info',
            _("Process triggered by integration '%s' for %s %d") % (self.name, self.model_name, record.id)
        )
        
        return process_instance
    
    @api.model
    def install_model_hooks(self):
        """Install hooks on Odoo models to trigger processes"""
        integrations = self.search([('is_active', '=', True)])
        
        for integration in integrations:
            try:
                model_obj = self.env[integration.model_name]
                
                # Install create hook
                if integration.trigger_on_create:
                    self._install_create_hook(model_obj, integration)
                
                # Install write hook
                if integration.trigger_on_write:
                    self._install_write_hook(model_obj, integration)
                
                # Install unlink hook
                if integration.trigger_on_unlink:
                    self._install_unlink_hook(model_obj, integration)
                    
            except Exception as e:
                _logger.error("Error installing hooks for integration %s: %s", integration.name, str(e))
    
    def _install_create_hook(self, model_obj, integration):
        """Install create hook on model"""
        original_create = model_obj.create
        
        def hooked_create(self, vals_list):
            records = original_create(vals_list)
            for record in records:
                try:
                    integration.trigger_process(record, 'create')
                except Exception as e:
                    _logger.error("Error in create hook for %s: %s", integration.name, str(e))
            return records
        
        model_obj.create = hooked_create
    
    def _install_write_hook(self, model_obj, integration):
        """Install write hook on model"""
        original_write = model_obj.write
        
        def hooked_write(self, vals):
            old_values = {}
            for record in self:
                old_values[record.id] = {field: getattr(record, field) for field in vals.keys()}
            
            result = original_write(vals)
            
            for record in self:
                try:
                    integration.trigger_process(record, 'write', old_values.get(record.id, {}))
                except Exception as e:
                    _logger.error("Error in write hook for %s: %s", integration.name, str(e))
            
            return result
        
        model_obj.write = hooked_write
    
    def _install_unlink_hook(self, model_obj, integration):
        """Install unlink hook on model"""
        original_unlink = model_obj.unlink
        
        def hooked_unlink(self):
            records_data = [(record.id, record) for record in self]
            result = original_unlink()
            
            for record_id, record in records_data:
                try:
                    integration.trigger_process(record, 'unlink')
                except Exception as e:
                    _logger.error("Error in unlink hook for %s: %s", integration.name, str(e))
            
            return result
        
        model_obj.unlink = hooked_unlink
    
    @api.constrains('model_name')
    def _check_model_exists(self):
        for record in self:
            if record.model_name and record.model_name not in self.env:
                raise ValidationError(_("Model '%s' does not exist") % record.model_name)