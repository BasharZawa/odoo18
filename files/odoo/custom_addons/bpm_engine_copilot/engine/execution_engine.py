# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import xml.etree.ElementTree as ET
import json
import logging

_logger = logging.getLogger(__name__)


class BmpExecutionEngine(models.TransientModel):
    _name = 'bmp.execution.engine'
    _description = 'BPMN Execution Engine'

    def initialize_process(self, process_instance):
        """Initialize a process instance and start execution"""
        try:
            # Parse the BPMN XML
            parser = BmpBpmnParser(self.env)
            process_definition = parser.parse_xml(process_instance.process_definition_id.xml_data)
            
            # Create initial tokens at start events
            start_events = process_definition.get('start_events', [])
            if not start_events:
                raise UserError(_("No start events found in process definition"))
            
            # Create tokens for each start event
            token_manager = BmpTokenManager(self.env)
            for start_event in start_events:
                token_manager.create_token(process_instance, start_event['id'], start_event)
            
            # Execute the process
            self._execute_process(process_instance, process_definition)
            
        except Exception as e:
            _logger.error("Error initializing process %s: %s", process_instance.id, str(e))
            raise UserError(_("Failed to initialize process: %s") % str(e))
    
    def continue_process(self, process_instance, completed_task=None):
        """Continue process execution after a task completion"""
        try:
            # Parse the BPMN XML
            parser = BmpBpmnParser(self.env)
            process_definition = parser.parse_xml(process_instance.process_definition_id.xml_data)
            
            # Get the next elements after the completed task
            if completed_task:
                next_elements = self._get_next_elements(process_definition, completed_task.task_id)
                
                # Create tokens for next elements
                token_manager = BmpTokenManager(self.env)
                for element in next_elements:
                    token_manager.create_token(process_instance, element['id'], element)
            
            # Continue execution
            self._execute_process(process_instance, process_definition)
            
        except Exception as e:
            _logger.error("Error continuing process %s: %s", process_instance.id, str(e))
            process_instance.action_fail(_("Failed to continue process: %s") % str(e))
    
    def _execute_process(self, process_instance, process_definition):
        """Execute the process by processing all active tokens"""
        token_manager = BmpTokenManager(self.env)
        max_iterations = 1000  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            active_tokens = token_manager.get_active_tokens(process_instance)
            if not active_tokens:
                # No more active tokens - check if process is complete
                self._check_process_completion(process_instance, process_definition)
                break
            
            tokens_processed = False
            for token in active_tokens:
                if self._process_token(process_instance, token, process_definition):
                    tokens_processed = True
            
            if not tokens_processed:
                # No tokens could be processed - process is waiting
                break
            
            iteration += 1
        
        if iteration >= max_iterations:
            _logger.warning("Process execution reached maximum iterations for instance %s", process_instance.id)
    
    def _process_token(self, process_instance, token, process_definition):
        """Process a single token"""
        element_id = token.get('element_id')
        element = self._find_element(process_definition, element_id)
        
        if not element:
            _logger.error("Element %s not found in process definition", element_id)
            return False
        
        element_type = element.get('type')
        
        try:
            if element_type == 'startEvent':
                return self._process_start_event(process_instance, token, element, process_definition)
            elif element_type == 'endEvent':
                return self._process_end_event(process_instance, token, element, process_definition)
            elif element_type in ['userTask', 'serviceTask', 'scriptTask', 'manualTask']:
                return self._process_task(process_instance, token, element, process_definition)
            elif element_type == 'exclusiveGateway':
                return self._process_exclusive_gateway(process_instance, token, element, process_definition)
            elif element_type == 'parallelGateway':
                return self._process_parallel_gateway(process_instance, token, element, process_definition)
            elif element_type == 'intermediateCatchEvent':
                return self._process_intermediate_event(process_instance, token, element, process_definition)
            else:
                _logger.warning("Unknown element type %s for element %s", element_type, element_id)
                return self._move_token_forward(process_instance, token, element, process_definition)
        
        except Exception as e:
            _logger.error("Error processing token for element %s: %s", element_id, str(e))
            return False
    
    def _process_start_event(self, process_instance, token, element, process_definition):
        """Process a start event"""
        # Log start event
        process_instance.env['bmp.activity.log'].log_activity(
            process_instance.id,
            'event_trigger',
            _("Start event '%s' triggered") % element.get('name', element['id']),
            element_id=element['id'],
            element_name=element.get('name'),
            element_type='startEvent'
        )
        
        # Move token forward
        return self._move_token_forward(process_instance, token, element, process_definition)
    
    def _process_end_event(self, process_instance, token, element, process_definition):
        """Process an end event"""
        # Log end event
        process_instance.env['bmp.activity.log'].log_activity(
            process_instance.id,
            'event_trigger',
            _("End event '%s' reached") % element.get('name', element['id']),
            element_id=element['id'],
            element_name=element.get('name'),
            element_type='endEvent'
        )
        
        # Consume the token (end events consume tokens)
        token_manager = BmpTokenManager(self.env)
        token_manager.consume_token(process_instance, token['id'])
        
        return True
    
    def _process_task(self, process_instance, token, element, process_definition):
        """Process a task element"""
        task_handler = BmpTaskHandler(self.env)
        
        # Check if task already exists for this token
        existing_task = self.env['bmp.task.instance'].search([
            ('process_instance_id', '=', process_instance.id),
            ('task_id', '=', element['id']),
            ('status', 'in', ['ready', 'claimed', 'in_progress'])
        ], limit=1)
        
        if not existing_task:
            # Create new task instance
            task_instance = task_handler.create_task_instance(process_instance, element)
            
            # Apply SLA rules
            self.env['bmp.sla.rule'].apply_sla_to_task(task_instance)
            
            # For service tasks, execute immediately
            if element.get('type') == 'serviceTask':
                task_instance.execute_service_task()
                return self._move_token_forward(process_instance, token, element, process_definition)
        
        # For user tasks and manual tasks, wait for completion
        if element.get('type') in ['userTask', 'manualTask']:
            return False  # Token waits until task is completed
        
        return True
    
    def _process_exclusive_gateway(self, process_instance, token, element, process_definition):
        """Process an exclusive gateway"""
        # Get outgoing sequence flows
        outgoing_flows = self._get_outgoing_flows(process_definition, element['id'])
        
        if not outgoing_flows:
            _logger.error("No outgoing flows found for exclusive gateway %s", element['id'])
            return False
        
        # Evaluate conditions to find the path to take
        condition_evaluator = BmpConditionEvaluator(self.env)
        selected_flow = None
        
        for flow in outgoing_flows:
            condition = flow.get('condition')
            if not condition:
                # Default flow (no condition)
                if not selected_flow:
                    selected_flow = flow
            else:
                # Evaluate condition
                if condition_evaluator.evaluate_condition(condition, process_instance):
                    selected_flow = flow
                    break
        
        if not selected_flow:
            _logger.error("No valid path found for exclusive gateway %s", element['id'])
            return False
        
        # Log gateway decision
        process_instance.env['bmp.activity.log'].log_activity(
            process_instance.id,
            'gateway_evaluate',
            _("Exclusive gateway '%s' selected path '%s'") % (element.get('name', element['id']), selected_flow.get('name', selected_flow['id'])),
            element_id=element['id'],
            element_name=element.get('name'),
            element_type='exclusiveGateway'
        )
        
        # Move token to selected target
        target_element = self._find_element(process_definition, selected_flow['target'])
        if target_element:
            token_manager = BmpTokenManager(self.env)
            token_manager.move_token(process_instance, token['id'], target_element['id'])
        
        return True
    
    def _process_parallel_gateway(self, process_instance, token, element, process_definition):
        """Process a parallel gateway"""
        outgoing_flows = self._get_outgoing_flows(process_definition, element['id'])
        incoming_flows = self._get_incoming_flows(process_definition, element['id'])
        
        if len(outgoing_flows) > 1:
            # Split gateway - create tokens for all outgoing paths
            token_manager = BmpTokenManager(self.env)
            token_manager.consume_token(process_instance, token['id'])
            
            for flow in outgoing_flows:
                target_element = self._find_element(process_definition, flow['target'])
                if target_element:
                    token_manager.create_token(process_instance, target_element['id'], target_element)
            
            # Log split
            process_instance.env['bmp.activity.log'].log_activity(
                process_instance.id,
                'gateway_split',
                _("Parallel gateway '%s' split into %d paths") % (element.get('name', element['id']), len(outgoing_flows)),
                element_id=element['id'],
                element_name=element.get('name'),
                element_type='parallelGateway'
            )
            
            return True
        
        elif len(incoming_flows) > 1:
            # Merge gateway - wait for all incoming tokens
            token_manager = BmpTokenManager(self.env)
            waiting_tokens = token_manager.get_tokens_at_element(process_instance, element['id'])
            
            if len(waiting_tokens) >= len(incoming_flows):
                # All tokens arrived - merge them
                for waiting_token in waiting_tokens:
                    token_manager.consume_token(process_instance, waiting_token['id'])
                
                # Create single token for outgoing flow
                if outgoing_flows:
                    target_element = self._find_element(process_definition, outgoing_flows[0]['target'])
                    if target_element:
                        token_manager.create_token(process_instance, target_element['id'], target_element)
                
                # Log merge
                process_instance.env['bmp.activity.log'].log_activity(
                    process_instance.id,
                    'gateway_merge',
                    _("Parallel gateway '%s' merged %d tokens") % (element.get('name', element['id']), len(waiting_tokens)),
                    element_id=element['id'],
                    element_name=element.get('name'),
                    element_type='parallelGateway'
                )
                
                return True
            else:
                # Not all tokens arrived yet - wait
                return False
        
        else:
            # Simple pass-through
            return self._move_token_forward(process_instance, token, element, process_definition)
    
    def _process_intermediate_event(self, process_instance, token, element, process_definition):
        """Process an intermediate event"""
        event_type = element.get('eventType', 'message')
        
        if event_type == 'timer':
            # Handle timer events
            return self._process_timer_event(process_instance, token, element, process_definition)
        elif event_type == 'message':
            # Handle message events
            return self._process_message_event(process_instance, token, element, process_definition)
        else:
            # Default behavior - continue immediately
            return self._move_token_forward(process_instance, token, element, process_definition)
    
    def _process_timer_event(self, process_instance, token, element, process_definition):
        """Process a timer event"""
        # TODO: Implement timer scheduling with cron jobs
        # For now, continue immediately
        return self._move_token_forward(process_instance, token, element, process_definition)
    
    def _process_message_event(self, process_instance, token, element, process_definition):
        """Process a message event"""
        # TODO: Implement message handling
        # For now, continue immediately
        return self._move_token_forward(process_instance, token, element, process_definition)
    
    def _move_token_forward(self, process_instance, token, element, process_definition):
        """Move token to the next element(s)"""
        outgoing_flows = self._get_outgoing_flows(process_definition, element['id'])
        
        if not outgoing_flows:
            # No outgoing flows - consume token
            token_manager = BmpTokenManager(self.env)
            token_manager.consume_token(process_instance, token['id'])
            return True
        
        if len(outgoing_flows) == 1:
            # Single outgoing flow - move token
            target_element = self._find_element(process_definition, outgoing_flows[0]['target'])
            if target_element:
                token_manager = BmpTokenManager(self.env)
                token_manager.move_token(process_instance, token['id'], target_element['id'])
                return True
        else:
            # Multiple outgoing flows - should not happen for most elements
            _logger.warning("Element %s has multiple outgoing flows but is not a gateway", element['id'])
            return False
        
        return False
    
    def _get_next_elements(self, process_definition, element_id):
        """Get the next elements after the given element"""
        outgoing_flows = self._get_outgoing_flows(process_definition, element_id)
        next_elements = []
        
        for flow in outgoing_flows:
            target_element = self._find_element(process_definition, flow['target'])
            if target_element:
                next_elements.append(target_element)
        
        return next_elements
    
    def _get_outgoing_flows(self, process_definition, element_id):
        """Get outgoing sequence flows for an element"""
        flows = process_definition.get('sequence_flows', [])
        return [flow for flow in flows if flow.get('source') == element_id]
    
    def _get_incoming_flows(self, process_definition, element_id):
        """Get incoming sequence flows for an element"""
        flows = process_definition.get('sequence_flows', [])
        return [flow for flow in flows if flow.get('target') == element_id]
    
    def _find_element(self, process_definition, element_id):
        """Find an element by ID in the process definition"""
        all_elements = []
        all_elements.extend(process_definition.get('start_events', []))
        all_elements.extend(process_definition.get('end_events', []))
        all_elements.extend(process_definition.get('tasks', []))
        all_elements.extend(process_definition.get('gateways', []))
        all_elements.extend(process_definition.get('events', []))
        
        for element in all_elements:
            if element.get('id') == element_id:
                return element
        
        return None
    
    def _check_process_completion(self, process_instance, process_definition):
        """Check if the process is complete"""
        token_manager = BmpTokenManager(self.env)
        active_tokens = token_manager.get_active_tokens(process_instance)
        
        if not active_tokens:
            # No active tokens and no pending tasks
            pending_tasks = self.env['bmp.task.instance'].search([
                ('process_instance_id', '=', process_instance.id),
                ('status', 'in', ['ready', 'claimed', 'in_progress'])
            ])
            
            if not pending_tasks:
                process_instance.action_complete()


class BmpBpmnParser:
    """Simple BPMN XML parser"""
    
    def __init__(self, env):
        self.env = env
    
    def parse_xml(self, xml_data):
        """Parse BPMN XML and extract process structure"""
        try:
            root = ET.fromstring(xml_data)
            process_definition = {
                'start_events': [],
                'end_events': [],
                'tasks': [],
                'gateways': [],
                'events': [],
                'sequence_flows': [],
            }
            
            # Parse elements
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]  # Remove namespace
                
                if tag == 'startEvent':
                    process_definition['start_events'].append({
                        'id': elem.get('id'),
                        'name': elem.get('name', ''),
                        'type': 'startEvent',
                    })
                elif tag == 'endEvent':
                    process_definition['end_events'].append({
                        'id': elem.get('id'),
                        'name': elem.get('name', ''),
                        'type': 'endEvent',
                    })
                elif tag in ['userTask', 'serviceTask', 'scriptTask', 'manualTask']:
                    process_definition['tasks'].append({
                        'id': elem.get('id'),
                        'name': elem.get('name', ''),
                        'type': tag,
                    })
                elif tag in ['exclusiveGateway', 'parallelGateway']:
                    process_definition['gateways'].append({
                        'id': elem.get('id'),
                        'name': elem.get('name', ''),
                        'type': tag,
                    })
                elif tag == 'sequenceFlow':
                    flow = {
                        'id': elem.get('id'),
                        'name': elem.get('name', ''),
                        'source': elem.get('sourceRef'),
                        'target': elem.get('targetRef'),
                    }
                    
                    # Check for condition
                    condition_elem = elem.find('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}conditionExpression')
                    if condition_elem is not None:
                        flow['condition'] = condition_elem.text
                    
                    process_definition['sequence_flows'].append(flow)
            
            return process_definition
            
        except ET.ParseError as e:
            raise ValidationError(_("Invalid BPMN XML: %s") % str(e))


class BmpTokenManager:
    """Token management for process execution"""
    
    def __init__(self, env):
        self.env = env
    
    def create_token(self, process_instance, element_id, element_data):
        """Create a new token at the specified element"""
        # For now, store tokens in process instance data
        # In a full implementation, this would be a separate model
        token_data = {
            'id': f"token_{element_id}_{fields.Datetime.now().timestamp()}",
            'element_id': element_id,
            'element_data': element_data,
            'created_at': fields.Datetime.now(),
        }
        
        # Store in process data for now
        current_data = json.loads(process_instance.process_data or '{}')
        tokens = current_data.get('tokens', [])
        tokens.append(token_data)
        current_data['tokens'] = tokens
        process_instance.process_data = json.dumps(current_data)
        
        return token_data
    
    def get_active_tokens(self, process_instance):
        """Get all active tokens for a process instance"""
        current_data = json.loads(process_instance.process_data or '{}')
        return current_data.get('tokens', [])
    
    def get_tokens_at_element(self, process_instance, element_id):
        """Get all tokens at a specific element"""
        tokens = self.get_active_tokens(process_instance)
        return [token for token in tokens if token.get('element_id') == element_id]
    
    def consume_token(self, process_instance, token_id):
        """Remove a token from the process"""
        current_data = json.loads(process_instance.process_data or '{}')
        tokens = current_data.get('tokens', [])
        tokens = [token for token in tokens if token.get('id') != token_id]
        current_data['tokens'] = tokens
        process_instance.process_data = json.dumps(current_data)
    
    def move_token(self, process_instance, token_id, new_element_id):
        """Move a token to a new element"""
        current_data = json.loads(process_instance.process_data or '{}')
        tokens = current_data.get('tokens', [])
        
        for token in tokens:
            if token.get('id') == token_id:
                token['element_id'] = new_element_id
                break
        
        current_data['tokens'] = tokens
        process_instance.process_data = json.dumps(current_data)


class BmpTaskHandler:
    """Task handling for process execution"""
    
    def __init__(self, env):
        self.env = env
    
    def create_task_instance(self, process_instance, element):
        """Create a task instance from a BPMN element"""
        task_data = {
            'process_instance_id': process_instance.id,
            'task_type': self._map_task_type(element['type']),
            'task_name': element.get('name', element['id']),
            'task_id': element['id'],
            'status': 'ready',
        }
        
        return self.env['bmp.task.instance'].create(task_data)
    
    def _map_task_type(self, bpmn_type):
        """Map BPMN task type to internal task type"""
        mapping = {
            'userTask': 'user',
            'serviceTask': 'service',
            'scriptTask': 'script',
            'manualTask': 'manual',
        }
        return mapping.get(bpmn_type, 'user')


class BmpConditionEvaluator:
    """Condition evaluation for gateways and flows"""
    
    def __init__(self, env):
        self.env = env
    
    def evaluate_condition(self, condition, process_instance):
        """Evaluate a condition expression"""
        try:
            # Create safe evaluation context
            context = {
                'process': process_instance,
                'variables': process_instance.get_all_variables(),
                'env': self.env,
                'user': self.env.user,
            }
            
            # For now, support simple Python expressions
            result = eval(condition, {"__builtins__": {}}, context)
            return bool(result)
            
        except Exception as e:
            _logger.error("Error evaluating condition '%s': %s", condition, str(e))
            return False