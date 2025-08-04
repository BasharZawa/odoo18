import xml.etree.ElementTree as ET
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class BPMNEngine(models.AbstractModel):
    _name = 'bpmn.engine'
    _description = 'BPMN Engine'

    @api.model
    def start_process(self, definition_id, related_model=None, related_id=None, variables=None):
        definition = self.env['bpmn.process.definition'].browse(definition_id)
        if not definition.is_active:
            raise UserError("Process definition is inactive.")
        instance = self.env['bpmn.process.instance'].create({
            'process_definition_id': definition.id,
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'related_record_model': related_model,
            'related_record_id': related_id,
        })
        root = ET.fromstring(definition.xml_data)
        start_event = next((el for el in root.iter() if el.tag.endswith('startEvent')), None)
        if not start_event:
            raise UserError("No start event found in BPMN definition!")
        self._move_token(instance, start_event, variables or {})
        return instance

    def _move_token(self, instance, current_node, variables):
        # Simplified for demo: Finds next userTask or serviceTask and creates/executes
        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}
        following = []
        for seq_flow in current_node.findall('../bpmn:sequenceFlow', ns):
            if seq_flow.get('sourceRef') == current_node.get('id'):
                target_id = seq_flow.get('targetRef')
                following.append(target_id)
        root = current_node.getroottree().getroot() if hasattr(current_node, 'getroottree') else current_node
        for target_id in following:
            target_node = next((el for el in root.iter() if el.get('id') == target_id), None)
            if not target_node:
                continue
            if target_node.tag.endswith('userTask'):
                self.env['bpmn.task.instance'].create({
                    'process_instance_id': instance.id,
                    'task_type': 'user',
                    'task_name': target_node.attrib.get('name', 'User Task'),
                    'status': 'ready',
                })
            elif target_node.tag.endswith('serviceTask'):
                # Demo: simulate service task execution
                self._execute_service_task(instance, target_node, variables)
            elif target_node.tag.endswith('endEvent'):
                instance.write({'state': 'completed', 'ended_at': fields.Datetime.now()})

    def _execute_service_task(self, instance, node, variables):
        # For real usage, implement dynamic Python code or server action
        # Here, we'll just log an action
        self.env['bpmn.activity.log'].create({
            'process_instance_id': instance.id,
            'action_type': 'service_task',
            'details': f"Executed service task: {node.attrib.get('name', '')}"
        })

    @api.model
    def complete_task(self, task_id, user_id):
        task = self.env['bpmn.task.instance'].browse(task_id)
        if task.status != 'ready':
            raise UserError("Task not ready!")
        task.write({
            'status': 'completed',
            'completed_at': fields.Datetime.now(),
            'assigned_user_id': user_id
        })
        # After completion, advance the process token
        definition = task.process_instance_id.process_definition_id
        # Parse BPMN and find next node (for demo, assume one after another)
        # TODO: Expand to real navigation logic per full BPMN spec
        # Omitted for brevity in this preview
        return True
