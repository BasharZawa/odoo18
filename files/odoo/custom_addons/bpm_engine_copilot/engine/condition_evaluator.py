# -*- coding: utf-8 -*-

import re
import logging
from odoo import _

_logger = logging.getLogger(__name__)


class BmpConditionEvaluator:
    """Condition Evaluator for BPMN Gateways and Sequence Flows"""
    
    def __init__(self, env):
        self.env = env
    
    def evaluate_condition(self, condition_data, process_instance, task_instance=None):
        """Evaluate a condition expression"""
        
        if not condition_data:
            return True
        
        if isinstance(condition_data, str):
            # Simple string expression
            return self._evaluate_expression(condition_data, process_instance, task_instance)
        
        elif isinstance(condition_data, dict):
            # Structured condition
            condition_type = condition_data.get('type', 'tFormalExpression')
            expression = condition_data.get('expression', '')
            language = condition_data.get('language', 'python')
            
            if language == 'python':
                return self._evaluate_python_expression(expression, process_instance, task_instance)
            elif language == 'javascript':
                return self._evaluate_javascript_expression(expression, process_instance, task_instance)
            else:
                # Default to python
                return self._evaluate_python_expression(expression, process_instance, task_instance)
        
        return True
    
    def _evaluate_expression(self, expression, process_instance, task_instance=None):
        """Evaluate a simple expression string"""
        
        # Check for different expression formats
        if expression.startswith('${') and expression.endswith('}'):
            # Expression language format
            inner_expression = expression[2:-1].strip()
            return self._evaluate_python_expression(inner_expression, process_instance, task_instance)
        
        elif expression.startswith('#{') and expression.endswith('}'):
            # Alternative expression language format
            inner_expression = expression[2:-1].strip()
            return self._evaluate_python_expression(inner_expression, process_instance, task_instance)
        
        else:
            # Direct python expression
            return self._evaluate_python_expression(expression, process_instance, task_instance)
    
    def _evaluate_python_expression(self, expression, process_instance, task_instance=None):
        """Evaluate a Python expression"""
        
        try:
            if not expression or expression.strip() == '':
                return True
            
            # Create evaluation context
            context = self._create_evaluation_context(process_instance, task_instance)
            
            # Preprocess the expression
            processed_expression = self._preprocess_expression(expression, context)
            
            # Evaluate the expression
            result = eval(processed_expression, {"__builtins__": self._get_safe_builtins()}, context)
            
            # Convert result to boolean
            return bool(result)
            
        except Exception as e:
            _logger.error("Error evaluating Python expression '%s': %s", expression, str(e))
            return False
    
    def _evaluate_javascript_expression(self, expression, process_instance, task_instance=None):
        """Evaluate a JavaScript expression (converted to Python)"""
        
        try:
            # Convert common JavaScript patterns to Python
            python_expression = self._convert_javascript_to_python(expression)
            return self._evaluate_python_expression(python_expression, process_instance, task_instance)
            
        except Exception as e:
            _logger.error("Error evaluating JavaScript expression '%s': %s", expression, str(e))
            return False
    
    def _create_evaluation_context(self, process_instance, task_instance=None):
        """Create the evaluation context for expressions"""
        
        # Get all process variables
        variables = process_instance.get_all_variables()
        
        # Add task variables if available
        if task_instance:
            task_variables = task_instance.process_instance_id.get_all_variables(scope='local', task_instance=task_instance)
            variables.update(task_variables)
        
        # Create context
        context = {
            # Process and task objects
            'process': process_instance,
            'task': task_instance,
            'env': self.env,
            'user': self.env.user,
            
            # Variables
            'variables': variables,
            'vars': variables,  # Shorthand
            
            # Utility functions
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'any': any,
            'all': all,
        }
        
        # Add variables directly to context for easier access
        context.update(variables)
        
        # Add common helper functions
        context.update(self._get_helper_functions(process_instance, task_instance))
        
        return context
    
    def _preprocess_expression(self, expression, context):
        """Preprocess expression to handle common patterns"""
        
        # Handle variable references like $variableName or ${variableName}
        def replace_variable_ref(match):
            var_name = match.group(1) or match.group(2)
            if var_name in context:
                return f"variables.get('{var_name}')"
            return f"variables.get('{var_name}')"
        
        # Replace ${varName} and $varName patterns
        expression = re.sub(r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)', replace_variable_ref, expression)
        
        # Handle common comparison operators
        expression = expression.replace(' eq ', ' == ')
        expression = expression.replace(' ne ', ' != ')
        expression = expression.replace(' lt ', ' < ')
        expression = expression.replace(' le ', ' <= ')
        expression = expression.replace(' gt ', ' > ')
        expression = expression.replace(' ge ', ' >= ')
        expression = expression.replace(' and ', ' and ')
        expression = expression.replace(' or ', ' or ')
        expression = expression.replace(' not ', ' not ')
        
        return expression
    
    def _convert_javascript_to_python(self, js_expression):
        """Convert basic JavaScript expressions to Python"""
        
        # Handle JavaScript operators
        python_expr = js_expression
        python_expr = python_expr.replace('===', '==')
        python_expr = python_expr.replace('!==', '!=')
        python_expr = python_expr.replace('&&', ' and ')
        python_expr = python_expr.replace('||', ' or ')
        python_expr = python_expr.replace('!', ' not ')
        
        # Handle JavaScript null/undefined
        python_expr = python_expr.replace('null', 'None')
        python_expr = python_expr.replace('undefined', 'None')
        
        # Handle JavaScript true/false
        python_expr = python_expr.replace('true', 'True')
        python_expr = python_expr.replace('false', 'False')
        
        return python_expr
    
    def _get_helper_functions(self, process_instance, task_instance=None):
        """Get helper functions for expression evaluation"""
        
        def get_variable(name, default=None):
            """Get a process variable"""
            return process_instance.get_variable(name, default)
        
        def has_variable(name):
            """Check if a variable exists"""
            return process_instance.get_variable(name) is not None
        
        def get_task_variable(name, default=None):
            """Get a task variable"""
            if task_instance:
                return task_instance.process_instance_id.get_variable(name, scope='local', task_instance=task_instance, default=default)
            return default
        
        def is_user_in_group(group_name):
            """Check if current user is in a group"""
            try:
                group = self.env.ref(group_name)
                return group in self.env.user.groups_id
            except:
                return False
        
        def has_role(role_name):
            """Check if current user has a role (alias for is_user_in_group)"""
            return is_user_in_group(role_name)
        
        def record_exists(model_name, domain):
            """Check if a record exists"""
            try:
                return bool(self.env[model_name].search(domain, limit=1))
            except:
                return False
        
        def record_count(model_name, domain):
            """Count records matching domain"""
            try:
                return self.env[model_name].search_count(domain)
            except:
                return 0
        
        def get_record_field(model_name, record_id, field_name):
            """Get a field value from a record"""
            try:
                record = self.env[model_name].browse(record_id)
                if record.exists():
                    return getattr(record, field_name, None)
            except:
                pass
            return None
        
        def now():
            """Get current datetime"""
            from odoo import fields
            return fields.Datetime.now()
        
        def today():
            """Get current date"""
            from odoo import fields
            return fields.Date.today()
        
        return {
            'get_variable': get_variable,
            'get_var': get_variable,  # Shorthand
            'has_variable': has_variable,
            'has_var': has_variable,  # Shorthand
            'get_task_variable': get_task_variable,
            'get_task_var': get_task_variable,  # Shorthand
            'is_user_in_group': is_user_in_group,
            'has_role': has_role,
            'record_exists': record_exists,
            'record_count': record_count,
            'get_record_field': get_record_field,
            'now': now,
            'today': today,
        }
    
    def _get_safe_builtins(self):
        """Get safe built-in functions for expression evaluation"""
        
        return {
            'abs': abs,
            'all': all,
            'any': any,
            'bool': bool,
            'dict': dict,
            'float': float,
            'int': int,
            'len': len,
            'list': list,
            'max': max,
            'min': min,
            'round': round,
            'str': str,
            'sum': sum,
            'tuple': tuple,
            'zip': zip,
            'enumerate': enumerate,
            'range': range,
            'sorted': sorted,
            'reversed': reversed,
        }
    
    def validate_expression(self, expression, language='python'):
        """Validate an expression without executing it"""
        
        try:
            if language == 'python':
                # Try to compile the expression
                compile(expression, '<string>', 'eval')
                return True, None
            
            elif language == 'javascript':
                # Convert to Python and validate
                python_expr = self._convert_javascript_to_python(expression)
                compile(python_expr, '<string>', 'eval')
                return True, None
            
            else:
                return False, f"Unsupported language: {language}"
                
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_expression_variables(self, expression):
        """Extract variable names used in an expression"""
        
        import ast
        
        try:
            # Parse the expression
            tree = ast.parse(expression, mode='eval')
            
            # Find all name nodes
            variables = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    variables.add(node.id)
            
            # Filter out built-in names
            builtins = set(self._get_safe_builtins().keys())
            variables = variables - builtins - {'variables', 'vars', 'process', 'task', 'env', 'user'}
            
            return list(variables)
            
        except Exception as e:
            _logger.warning("Error extracting variables from expression '%s': %s", expression, str(e))
            return []
    
    def test_expression(self, expression, test_variables=None, language='python'):
        """Test an expression with sample data"""
        
        try:
            # Create a mock process instance for testing
            test_context = {
                'variables': test_variables or {},
                'vars': test_variables or {},
                'process': None,
                'task': None,
                'env': self.env,
                'user': self.env.user,
            }
            
            # Add test variables to context
            if test_variables:
                test_context.update(test_variables)
            
            # Add helper functions
            test_context.update(self._get_helper_functions(None, None))
            
            if language == 'python':
                result = eval(expression, {"__builtins__": self._get_safe_builtins()}, test_context)
            elif language == 'javascript':
                python_expr = self._convert_javascript_to_python(expression)
                result = eval(python_expr, {"__builtins__": self._get_safe_builtins()}, test_context)
            else:
                raise ValueError(f"Unsupported language: {language}")
            
            return True, result
            
        except Exception as e:
            return False, str(e)