# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import json
import logging
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BmpBpmnParser:
    """BPMN 2.0 XML Parser"""
    
    def __init__(self, env):
        self.env = env
        self.namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'omgdc': 'http://www.omg.org/spec/DD/20100524/DC',
            'omgdi': 'http://www.omg.org/spec/DD/20100524/DI',
        }
    
    def parse(self, xml_data):
        """Parse BPMN XML and return process definition structure"""
        try:
            root = ET.fromstring(xml_data)
            
            # Register namespaces
            for prefix, uri in self.namespaces.items():
                ET.register_namespace(prefix, uri)
            
            process_definition = {
                'id': None,
                'name': None,
                'start_events': [],
                'end_events': [],
                'tasks': [],
                'gateways': [],
                'intermediate_events': [],
                'sequence_flows': [],
                'data_objects': [],
                'message_flows': [],
                'participants': [],
            }
            
            # Find the main process element
            process_elem = root.find('.//bpmn:process', self.namespaces)
            if process_elem is not None:
                process_definition['id'] = process_elem.get('id')
                process_definition['name'] = process_elem.get('name', process_definition['id'])
                
                # Parse process elements
                self._parse_process_elements(process_elem, process_definition)
            
            # Validate the parsed definition
            self._validate_process_definition(process_definition)
            
            return process_definition
            
        except ET.ParseError as e:
            raise ValidationError(f"Invalid XML format: {str(e)}")
        except Exception as e:
            _logger.error("Error parsing BPMN XML: %s", str(e))
            raise ValidationError(f"Error parsing BPMN XML: {str(e)}")
    
    def _parse_process_elements(self, process_elem, process_definition):
        """Parse all elements within a process"""
        
        # Parse start events
        for elem in process_elem.findall('.//bpmn:startEvent', self.namespaces):
            start_event = self._parse_start_event(elem)
            process_definition['start_events'].append(start_event)
        
        # Parse end events
        for elem in process_elem.findall('.//bpmn:endEvent', self.namespaces):
            end_event = self._parse_end_event(elem)
            process_definition['end_events'].append(end_event)
        
        # Parse tasks
        task_types = ['userTask', 'serviceTask', 'scriptTask', 'manualTask', 'sendTask', 'receiveTask']
        for task_type in task_types:
            for elem in process_elem.findall(f'.//bpmn:{task_type}', self.namespaces):
                task = self._parse_task(elem, task_type)
                process_definition['tasks'].append(task)
        
        # Parse gateways
        gateway_types = ['exclusiveGateway', 'parallelGateway', 'inclusiveGateway', 'eventBasedGateway']
        for gateway_type in gateway_types:
            for elem in process_elem.findall(f'.//bpmn:{gateway_type}', self.namespaces):
                gateway = self._parse_gateway(elem, gateway_type)
                process_definition['gateways'].append(gateway)
        
        # Parse intermediate events
        event_types = ['intermediateCatchEvent', 'intermediateThrowEvent']
        for event_type in event_types:
            for elem in process_elem.findall(f'.//bpmn:{event_type}', self.namespaces):
                event = self._parse_intermediate_event(elem, event_type)
                process_definition['intermediate_events'].append(event)
        
        # Parse sequence flows
        for elem in process_elem.findall('.//bpmn:sequenceFlow', self.namespaces):
            flow = self._parse_sequence_flow(elem)
            process_definition['sequence_flows'].append(flow)
    
    def _parse_start_event(self, elem):
        """Parse a start event element"""
        start_event = {
            'id': elem.get('id'),
            'name': elem.get('name', ''),
            'type': 'startEvent',
            'event_definitions': [],
        }
        
        # Parse event definitions (timer, message, etc.)
        for event_def_elem in elem:
            event_def = self._parse_event_definition(event_def_elem)
            if event_def:
                start_event['event_definitions'].append(event_def)
        
        return start_event
    
    def _parse_end_event(self, elem):
        """Parse an end event element"""
        end_event = {
            'id': elem.get('id'),
            'name': elem.get('name', ''),
            'type': 'endEvent',
            'event_definitions': [],
        }
        
        # Parse event definitions
        for event_def_elem in elem:
            event_def = self._parse_event_definition(event_def_elem)
            if event_def:
                end_event['event_definitions'].append(event_def)
        
        return end_event
    
    def _parse_task(self, elem, task_type):
        """Parse a task element"""
        task = {
            'id': elem.get('id'),
            'name': elem.get('name', ''),
            'type': task_type,
            'documentation': self._get_documentation(elem),
            'properties': {},
        }
        
        # Parse task-specific attributes
        if task_type == 'userTask':
            task['properties'].update(self._parse_user_task_properties(elem))
        elif task_type == 'serviceTask':
            task['properties'].update(self._parse_service_task_properties(elem))
        elif task_type == 'scriptTask':
            task['properties'].update(self._parse_script_task_properties(elem))
        
        # Parse extension elements (custom properties)
        ext_elements = elem.find('./bpmn:extensionElements', self.namespaces)
        if ext_elements is not None:
            task['properties'].update(self._parse_extension_elements(ext_elements))
        
        return task
    
    def _parse_gateway(self, elem, gateway_type):
        """Parse a gateway element"""
        gateway = {
            'id': elem.get('id'),
            'name': elem.get('name', ''),
            'type': gateway_type,
            'direction': elem.get('gatewayDirection', 'Unspecified'),
            'default_flow': elem.get('default'),
        }
        
        return gateway
    
    def _parse_intermediate_event(self, elem, event_type):
        """Parse an intermediate event element"""
        event = {
            'id': elem.get('id'),
            'name': elem.get('name', ''),
            'type': event_type,
            'event_definitions': [],
        }
        
        # Parse event definitions
        for event_def_elem in elem:
            event_def = self._parse_event_definition(event_def_elem)
            if event_def:
                event['event_definitions'].append(event_def)
        
        return event
    
    def _parse_sequence_flow(self, elem):
        """Parse a sequence flow element"""
        flow = {
            'id': elem.get('id'),
            'name': elem.get('name', ''),
            'source_ref': elem.get('sourceRef'),
            'target_ref': elem.get('targetRef'),
            'condition': None,
        }
        
        # Parse condition expression
        condition_elem = elem.find('./bpmn:conditionExpression', self.namespaces)
        if condition_elem is not None:
            flow['condition'] = {
                'type': condition_elem.get('{http://www.w3.org/2001/XMLSchema-instance}type', 'tFormalExpression'),
                'expression': condition_elem.text or '',
                'language': condition_elem.get('language', 'python'),
            }
        
        return flow
    
    def _parse_event_definition(self, elem):
        """Parse an event definition element"""
        tag = elem.tag.split('}')[-1]  # Remove namespace
        
        if tag == 'timerEventDefinition':
            return self._parse_timer_event_definition(elem)
        elif tag == 'messageEventDefinition':
            return self._parse_message_event_definition(elem)
        elif tag == 'signalEventDefinition':
            return self._parse_signal_event_definition(elem)
        elif tag == 'errorEventDefinition':
            return self._parse_error_event_definition(elem)
        elif tag == 'terminateEventDefinition':
            return {'type': 'terminate'}
        
        return None
    
    def _parse_timer_event_definition(self, elem):
        """Parse a timer event definition"""
        timer_def = {'type': 'timer'}
        
        # Parse timer expressions
        time_date = elem.find('./bpmn:timeDate', self.namespaces)
        if time_date is not None:
            timer_def['time_date'] = time_date.text
        
        time_duration = elem.find('./bpmn:timeDuration', self.namespaces)
        if time_duration is not None:
            timer_def['time_duration'] = time_duration.text
        
        time_cycle = elem.find('./bpmn:timeCycle', self.namespaces)
        if time_cycle is not None:
            timer_def['time_cycle'] = time_cycle.text
        
        return timer_def
    
    def _parse_message_event_definition(self, elem):
        """Parse a message event definition"""
        return {
            'type': 'message',
            'message_ref': elem.get('messageRef'),
        }
    
    def _parse_signal_event_definition(self, elem):
        """Parse a signal event definition"""
        return {
            'type': 'signal',
            'signal_ref': elem.get('signalRef'),
        }
    
    def _parse_error_event_definition(self, elem):
        """Parse an error event definition"""
        return {
            'type': 'error',
            'error_ref': elem.get('errorRef'),
        }
    
    def _parse_user_task_properties(self, elem):
        """Parse user task specific properties"""
        properties = {}
        
        # Parse assignment
        assignee = elem.get('assignee')
        if assignee:
            properties['assignee'] = assignee
        
        candidate_users = elem.get('candidateUsers')
        if candidate_users:
            properties['candidate_users'] = candidate_users.split(',')
        
        candidate_groups = elem.get('candidateGroups')
        if candidate_groups:
            properties['candidate_groups'] = candidate_groups.split(',')
        
        # Parse form reference
        form_key = elem.get('formKey')
        if form_key:
            properties['form_key'] = form_key
        
        return properties
    
    def _parse_service_task_properties(self, elem):
        """Parse service task specific properties"""
        properties = {}
        
        # Parse implementation
        implementation = elem.get('implementation')
        if implementation:
            properties['implementation'] = implementation
        
        # Parse class/expression
        class_name = elem.get('class')
        if class_name:
            properties['class'] = class_name
        
        expression = elem.get('expression')
        if expression:
            properties['expression'] = expression
        
        return properties
    
    def _parse_script_task_properties(self, elem):
        """Parse script task specific properties"""
        properties = {}
        
        # Parse script
        script_format = elem.get('scriptFormat', 'python')
        properties['script_format'] = script_format
        
        script_elem = elem.find('./bpmn:script', self.namespaces)
        if script_elem is not None:
            properties['script'] = script_elem.text or ''
        
        return properties
    
    def _parse_extension_elements(self, ext_elem):
        """Parse extension elements for custom properties"""
        properties = {}
        
        # This is where custom Odoo-specific properties would be parsed
        # For now, just extract any properties elements
        
        return properties
    
    def _get_documentation(self, elem):
        """Get documentation text from an element"""
        doc_elem = elem.find('./bpmn:documentation', self.namespaces)
        if doc_elem is not None:
            return doc_elem.text or ''
        return ''
    
    def _validate_process_definition(self, process_definition):
        """Validate the parsed process definition"""
        
        # Check for at least one start event
        if not process_definition['start_events']:
            raise ValidationError("Process must have at least one start event")
        
        # Check for at least one end event
        if not process_definition['end_events']:
            raise ValidationError("Process must have at least one end event")
        
        # Validate all sequence flows have valid source and target
        all_element_ids = set()
        for elements in [process_definition['start_events'], process_definition['end_events'], 
                        process_definition['tasks'], process_definition['gateways'],
                        process_definition['intermediate_events']]:
            for element in elements:
                all_element_ids.add(element['id'])
        
        for flow in process_definition['sequence_flows']:
            if flow['source_ref'] not in all_element_ids:
                raise ValidationError(f"Sequence flow {flow['id']} has invalid source reference: {flow['source_ref']}")
            if flow['target_ref'] not in all_element_ids:
                raise ValidationError(f"Sequence flow {flow['id']} has invalid target reference: {flow['target_ref']}")
        
        return True