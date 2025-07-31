# -*- coding: utf-8 -*-

import logging
from odoo import _

_logger = logging.getLogger(__name__)


class BmpTaskHandler:
    """Task Handler for BPMN Process Execution"""
    
    def __init__(self, env):
        self.env = env
    
    def create_task_instance(self, process_instance, element, token_data=None):
        """Create a task instance from a BPMN element"""
        
        task_type = self._map_bpmn_type_to_task_type(element.get('type'))
        properties = element.get('properties', {})
        
        task_data = {
            'process_instance_id': process_instance.id,
            'task_type': task_type,
            'task_name': element.get('name') or element.get('id'),
            'task_id': element.get('id'),
            'status': 'ready',
        }
        
        # Set assignment based on BPMN properties
        self._set_task_assignment(task_data, properties)
        
        # Set task-specific properties
        if task_type == 'service':
            self._set_service_task_properties(task_data, properties)
        elif task_type == 'script':
            self._set_script_task_properties(task_data, properties)
        elif task_type == 'user':
            self._set_user_task_properties(task_data, properties)
        
        # Set form data if available
        self._set_task_form_data(task_data, properties, token_data)
        
        # Create the task instance
        task_instance = self.env['bmp.task.instance'].create(task_data)
        
        # Log task creation
        self.env['bmp.activity.log'].log_task_action(
            task_instance,
            'create_task',
            _("Task '%s' created") % task_instance.task_name
        )
        
        return task_instance
    
    def _map_bpmn_type_to_task_type(self, bpmn_type):
        """Map BPMN task type to internal task type"""
        mapping = {
            'userTask': 'user',
            'serviceTask': 'service',
            'scriptTask': 'script',
            'manualTask': 'manual',
            'sendTask': 'send',
            'receiveTask': 'receive',
        }
        return mapping.get(bpmn_type, 'user')
    
    def _set_task_assignment(self, task_data, properties):
        """Set task assignment based on BPMN properties"""
        
        # Direct assignee
        assignee = properties.get('assignee')
        if assignee:
            user = self._resolve_user_expression(assignee)
            if user:
                task_data['assigned_user_id'] = user.id
        
        # Candidate users
        candidate_users = properties.get('candidate_users', [])
        if candidate_users and not task_data.get('assigned_user_id'):
            # For now, assign to first candidate user
            # In a full implementation, this would create a pool assignment
            for candidate in candidate_users:
                user = self._resolve_user_expression(candidate)
                if user:
                    task_data['assigned_user_id'] = user.id
                    break
        
        # Candidate groups
        candidate_groups = properties.get('candidate_groups', [])
        if candidate_groups and not task_data.get('assigned_user_id'):
            for group_name in candidate_groups:
                group = self._resolve_group_expression(group_name)
                if group:
                    task_data['assigned_group_id'] = group.id
                    break
    
    def _set_service_task_properties(self, task_data, properties):
        """Set service task specific properties"""
        
        # Service class
        class_name = properties.get('class')
        if class_name:
            task_data['service_class'] = class_name
        
        # Service method/expression
        expression = properties.get('expression')
        if expression:
            task_data['service_method'] = expression
        
        # Implementation
        implementation = properties.get('implementation')
        if implementation:
            # Store implementation details in task_data
            task_data['task_data'] = self._json_encode({
                'implementation': implementation
            })
    
    def _set_script_task_properties(self, task_data, properties):
        """Set script task specific properties"""
        
        script = properties.get('script', '')
        script_format = properties.get('script_format', 'python')
        
        task_data['script_code'] = script
        task_data['task_data'] = self._json_encode({
            'script_format': script_format
        })
    
    def _set_user_task_properties(self, task_data, properties):
        """Set user task specific properties"""
        
        # Form key
        form_key = properties.get('form_key')
        if form_key:
            task_data['task_data'] = self._json_encode({
                'form_key': form_key
            })
    
    def _set_task_form_data(self, task_data, properties, token_data):
        """Set form data for the task"""
        
        form_data = {}
        
        # Add form key if available
        form_key = properties.get('form_key')
        if form_key:
            form_data['form_key'] = form_key
        
        # Add token variables as form data
        if token_data and 'variables' in token_data:
            form_data.update(token_data['variables'])
        
        if form_data:
            task_data['form_data'] = self._json_encode(form_data)
    
    def _resolve_user_expression(self, expression):
        """Resolve a user expression to an actual user"""
        try:
            # Handle different expression formats
            if expression.startswith('${') and expression.endswith('}'):
                # Expression language - evaluate
                var_name = expression[2:-1]
                # For now, just check if it's a direct user reference
                if var_name == 'initiator':
                    return self.env.user
                # Could add more expression evaluation here
            
            # Try direct user lookup by login
            user = self.env['res.users'].search([('login', '=', expression)], limit=1)
            if user:
                return user
            
            # Try user lookup by name
            user = self.env['res.users'].search([('name', '=', expression)], limit=1)
            if user:
                return user
            
        except Exception as e:
            _logger.warning("Error resolving user expression '%s': %s", expression, str(e))
        
        return None
    
    def _resolve_group_expression(self, expression):
        """Resolve a group expression to an actual group"""
        try:
            # Try direct group lookup by name
            group = self.env['res.groups'].search([('name', '=', expression)], limit=1)
            if group:
                return group
            
            # Try group lookup by XML ID
            try:
                group = self.env.ref(expression)
                if group and group._name == 'res.groups':
                    return group
            except:
                pass
            
        except Exception as e:
            _logger.warning("Error resolving group expression '%s': %s", expression, str(e))
        
        return None
    
    def execute_service_task(self, task_instance):
        """Execute a service task"""
        try:
            properties = task_instance.get_task_data()
            
            if task_instance.service_class and task_instance.service_method:
                return self._execute_service_method(task_instance)
            elif task_instance.script_code:
                return self._execute_script(task_instance)
            else:
                # Check for implementation type
                implementation = properties.get('implementation')
                if implementation == 'webService':
                    return self._execute_web_service(task_instance)
                elif implementation == 'expression':
                    return self._execute_expression(task_instance)
                else:
                    _logger.warning("No execution method found for service task %s", task_instance.id)
                    return False
        
        except Exception as e:
            _logger.error("Error executing service task %s: %s", task_instance.id, str(e))
            task_instance.action_fail(str(e))
            return False
    
    def _execute_service_method(self, task_instance):
        """Execute a service method"""
        try:
            # Get the service object
            service_obj = self.env[task_instance.service_class]
            
            # Get the method
            if not hasattr(service_obj, task_instance.service_method):
                raise Exception(f"Method '{task_instance.service_method}' not found in '{task_instance.service_class}'")
            
            method = getattr(service_obj, task_instance.service_method)
            
            # Execute the method with task instance as parameter
            result = method(task_instance)
            
            # Set output data if method returns something
            if result is not None:
                task_instance.set_form_data({'result': result})
            
            return True
            
        except Exception as e:
            _logger.error("Error executing service method: %s", str(e))
            raise
    
    def _execute_script(self, task_instance):
        """Execute a script task"""
        try:
            script_code = task_instance.script_code
            if not script_code:
                return True
            
            # Create execution context
            context = {
                'task': task_instance,
                'process': task_instance.process_instance_id,
                'env': self.env,
                'user': self.env.user,
                'variables': task_instance.process_instance_id.get_all_variables(),
            }
            
            # Add safe builtins
            safe_builtins = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'print': print,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                }
            }
            
            # Execute the script
            exec(script_code, safe_builtins, context)
            
            return True
            
        except Exception as e:
            _logger.error("Error executing script: %s", str(e))
            raise
    
    def _execute_web_service(self, task_instance):
        """Execute a web service call"""
        # TODO: Implement web service execution
        _logger.info("Web service execution not yet implemented for task %s", task_instance.id)
        return True
    
    def _execute_expression(self, task_instance):
        """Execute an expression"""
        # TODO: Implement expression execution
        _logger.info("Expression execution not yet implemented for task %s", task_instance.id)
        return True
    
    def handle_user_task_completion(self, task_instance, completion_data=None):
        """Handle completion of a user task"""
        
        # Set output data from completion
        if completion_data:
            current_form_data = task_instance.get_form_data()
            current_form_data.update(completion_data)
            task_instance.set_form_data(current_form_data)
        
        # Set process variables from form data
        form_data = task_instance.get_form_data()
        for key, value in form_data.items():
            if not key.startswith('_'):  # Skip internal fields
                task_instance.process_instance_id.set_variable(key, value)
        
        # Complete the task
        return task_instance.action_complete()
    
    def handle_task_timeout(self, task_instance):
        """Handle task timeout (SLA breach)"""
        
        # Apply SLA rules
        sla_rules = self.env['bmp.sla.rule'].get_applicable_rules(task_instance)
        
        for rule in sla_rules:
            if rule.check_sla_breach(task_instance):
                rule.escalate_task(task_instance)
                break  # Only apply first matching rule
    
    def get_task_form_schema(self, task_instance):
        """Get form schema for a user task"""
        
        task_data = task_instance.get_task_data()
        form_key = task_data.get('form_key')
        
        if form_key:
            # Try to load form schema from form key
            # This could be a reference to a form definition
            return self._load_form_schema(form_key)
        
        # Return default schema
        return {
            'type': 'object',
            'properties': {
                'comment': {
                    'type': 'string',
                    'title': 'Comment',
                    'description': 'Optional comment for task completion'
                }
            }
        }
    
    def _load_form_schema(self, form_key):
        """Load form schema from form key"""
        # TODO: Implement form schema loading
        # This could load from a form definition model or external source
        return {
            'type': 'object',
            'properties': {
                'data': {
                    'type': 'string',
                    'title': 'Data',
                    'description': f'Data for form {form_key}'
                }
            }
        }
    
    def _json_encode(self, data):
        """Safely encode data to JSON"""
        try:
            import json
            return json.dumps(data)
        except (TypeError, ValueError):
            return '{}'