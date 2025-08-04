# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class BmpProcessVariable(models.Model):
    _name = 'bmp.process.variable'
    _description = 'BPMN Process Variable'
    _order = 'key, scope'
    _rec_name = 'key'

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
        help='Task instance for local scope variables'
    )
    
    key = fields.Char(
        string='Variable Key',
        required=True,
        index=True,
        help='Name of the variable'
    )
    
    value = fields.Text(
        string='Value',
        help='String representation of the variable value'
    )
    
    type = fields.Selection([
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('json', 'JSON'),
        ('reference', 'Reference'),
    ], string='Type', required=True, default='string')
    
    scope = fields.Selection([
        ('global', 'Global'),
        ('local', 'Local'),
    ], string='Scope', required=True, default='global',
        help='Global variables are available throughout the process, local variables only in specific tasks')
    
    is_readonly = fields.Boolean(
        string='Read Only',
        default=False,
        help='Whether this variable can be modified'
    )
    
    description = fields.Char(
        string='Description',
        help='Description of the variable purpose'
    )
    
    # Metadata
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        readonly=True
    )
    
    updated_at = fields.Datetime(
        string='Updated At',
        default=fields.Datetime.now,
        readonly=True
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    updated_by = fields.Many2one(
        'res.users',
        string='Updated By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    # Display fields
    display_value = fields.Char(
        string='Display Value',
        compute='_compute_display_value',
        help='Human-readable representation of the value'
    )
    
    typed_value = fields.Char(
        string='Typed Value',
        compute='_compute_typed_value',
        help='Value with type information'
    )
    
    @api.depends('value', 'type')
    def _compute_display_value(self):
        for record in self:
            if not record.value:
                record.display_value = ''
                continue
                
            try:
                if record.type == 'boolean':
                    record.display_value = 'True' if record.get_typed_value() else 'False'
                elif record.type == 'json':
                    # Pretty print JSON
                    json_data = json.loads(record.value)
                    record.display_value = json.dumps(json_data, indent=2)[:100] + '...' if len(str(json_data)) > 100 else json.dumps(json_data, indent=2)
                elif record.type == 'reference':
                    # Handle Odoo record references
                    ref_data = record.get_typed_value()
                    if isinstance(ref_data, dict) and 'model' in ref_data and 'id' in ref_data:
                        try:
                            ref_record = record.env[ref_data['model']].browse(ref_data['id'])
                            record.display_value = f"{ref_data['model']}({ref_data['id']}): {ref_record.display_name}"
                        except:
                            record.display_value = f"{ref_data['model']}({ref_data['id']})"
                    else:
                        record.display_value = str(ref_data)
                else:
                    record.display_value = str(record.value)[:100]
                    if len(str(record.value)) > 100:
                        record.display_value += '...'
            except:
                record.display_value = str(record.value)[:100]
    
    @api.depends('value', 'type')
    def _compute_typed_value(self):
        for record in self:
            if record.value:
                record.typed_value = f"({record.type}) {record.display_value}"
            else:
                record.typed_value = f"({record.type}) [Empty]"
    
    def write(self, vals):
        if 'value' in vals or 'type' in vals:
            vals['updated_at'] = fields.Datetime.now()
            vals['updated_by'] = self.env.user.id
        return super().write(vals)
    
    def get_typed_value(self):
        """Get the value converted to its proper Python type"""
        if not self.value:
            return None
            
        try:
            if self.type == 'string':
                return str(self.value)
            elif self.type == 'integer':
                return int(self.value)
            elif self.type == 'float':
                return float(self.value)
            elif self.type == 'boolean':
                if isinstance(self.value, str):
                    return self.value.lower() in ('true', '1', 'yes', 'on')
                return bool(self.value)
            elif self.type == 'date':
                if isinstance(self.value, str):
                    return fields.Date.from_string(self.value)
                return self.value
            elif self.type == 'datetime':
                if isinstance(self.value, str):
                    return fields.Datetime.from_string(self.value)
                return self.value
            elif self.type == 'json':
                if isinstance(self.value, str):
                    return json.loads(self.value)
                return self.value
            elif self.type == 'reference':
                if isinstance(self.value, str):
                    return json.loads(self.value)
                return self.value
            else:
                return self.value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            _logger.warning("Error converting variable %s to type %s: %s", self.key, self.type, str(e))
            return self.value
    
    def set_typed_value(self, value):
        """Set the value from a Python object, automatically determining storage format"""
        if value is None:
            self.value = None
            return
        
        try:
            if self.type == 'string':
                self.value = str(value)
            elif self.type == 'integer':
                self.value = str(int(value))
            elif self.type == 'float':
                self.value = str(float(value))
            elif self.type == 'boolean':
                self.value = str(bool(value))
            elif self.type == 'date':
                if hasattr(value, 'strftime'):
                    self.value = value.strftime('%Y-%m-%d')
                else:
                    self.value = str(value)
            elif self.type == 'datetime':
                if hasattr(value, 'strftime'):
                    self.value = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    self.value = str(value)
            elif self.type == 'json':
                self.value = json.dumps(value)
            elif self.type == 'reference':
                if hasattr(value, '_name') and hasattr(value, 'id'):
                    # Odoo record
                    self.value = json.dumps({
                        'model': value._name,
                        'id': value.id,
                        'display_name': value.display_name
                    })
                else:
                    self.value = json.dumps(value)
            else:
                self.value = str(value)
        except Exception as e:
            _logger.error("Error setting variable %s value: %s", self.key, str(e))
            self.value = str(value)
    
    @api.model
    def set_variable(self, process_instance, key, value, var_type='string', scope='global', task_instance=None, description=None):
        """Set a process variable value"""
        domain = [
            ('process_instance_id', '=', process_instance.id),
            ('key', '=', key),
            ('scope', '=', scope),
        ]
        
        if scope == 'local' and task_instance:
            domain.append(('task_instance_id', '=', task_instance.id))
        elif scope == 'global':
            domain.append(('task_instance_id', '=', False))
        
        existing_var = self.search(domain, limit=1)
        
        values = {
            'type': var_type,
            'description': description,
        }
        
        if existing_var:
            if existing_var.is_readonly:
                raise ValidationError(_("Variable '%s' is read-only") % key)
            
            old_value = existing_var.get_typed_value()
            existing_var.set_typed_value(value)
            existing_var.write(values)
            
            # Log the change
            process_instance.env['bmp.activity.log'].log_variable_change(
                process_instance, key, old_value, value, task_instance
            )
            
            return existing_var
        else:
            values.update({
                'process_instance_id': process_instance.id,
                'task_instance_id': task_instance.id if task_instance else False,
                'key': key,
                'scope': scope,
            })
            
            new_var = self.create(values)
            new_var.set_typed_value(value)
            
            # Log the creation
            process_instance.env['bmp.activity.log'].log_variable_change(
                process_instance, key, None, value, task_instance
            )
            
            return new_var
    
    @api.model
    def get_variable(self, process_instance, key, scope='global', task_instance=None, default=None):
        """Get a process variable value"""
        domain = [
            ('process_instance_id', '=', process_instance.id),
            ('key', '=', key),
            ('scope', '=', scope),
        ]
        
        if scope == 'local' and task_instance:
            domain.append(('task_instance_id', '=', task_instance.id))
        elif scope == 'global':
            domain.append(('task_instance_id', '=', False))
        
        variable = self.search(domain, limit=1)
        
        if variable:
            return variable.get_typed_value()
        
        return default
    
    @api.model
    def get_all_variables(self, process_instance, scope='global', task_instance=None):
        """Get all variables for a process instance"""
        domain = [
            ('process_instance_id', '=', process_instance.id),
            ('scope', '=', scope),
        ]
        
        if scope == 'local' and task_instance:
            domain.append(('task_instance_id', '=', task_instance.id))
        elif scope == 'global':
            domain.append(('task_instance_id', '=', False))
        
        variables = self.search(domain)
        
        result = {}
        for var in variables:
            result[var.key] = var.get_typed_value()
        
        return result
    
    @api.constrains('key', 'process_instance_id', 'task_instance_id', 'scope')
    def _check_unique_variable(self):
        for record in self:
            domain = [
                ('process_instance_id', '=', record.process_instance_id.id),
                ('key', '=', record.key),
                ('scope', '=', record.scope),
                ('id', '!=', record.id),
            ]
            
            if record.scope == 'local':
                domain.append(('task_instance_id', '=', record.task_instance_id.id))
            else:
                domain.append(('task_instance_id', '=', False))
            
            existing = self.search(domain)
            if existing:
                raise ValidationError(_(
                    "Variable with key '%s' already exists in %s scope"
                ) % (record.key, record.scope))
    
    @api.constrains('scope', 'task_instance_id')
    def _check_scope_consistency(self):
        for record in self:
            if record.scope == 'local' and not record.task_instance_id:
                raise ValidationError(_("Local scope variables must have a task instance"))
            elif record.scope == 'global' and record.task_instance_id:
                raise ValidationError(_("Global scope variables cannot have a task instance"))