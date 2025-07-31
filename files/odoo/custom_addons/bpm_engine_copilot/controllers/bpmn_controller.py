# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class BmpController(http.Controller):
    
    @http.route('/bmp/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """Get dashboard data for BPMN dashboard"""
        try:
            # Get statistics
            active_processes = request.env['bmp.process.instance'].search_count([
                ('state', 'in', ['running', 'draft'])
            ])
            
            my_tasks = request.env['bmp.task.instance'].search_count([
                ('assigned_user_id', '=', request.uid),
                ('status', 'in', ['ready', 'claimed', 'in_progress'])
            ])
            
            overdue_tasks = request.env['bmp.task.instance'].search_count([
                ('is_overdue', '=', True),
                ('status', 'in', ['ready', 'claimed', 'in_progress'])
            ])
            
            # Get completed processes today
            from datetime import datetime, time
            today_start = datetime.combine(datetime.today().date(), time.min)
            completed_today = request.env['bmp.process.instance'].search_count([
                ('state', '=', 'completed'),
                ('ended_at', '>=', today_start)
            ])
            
            # Get recent activity
            recent_logs = request.env['bmp.activity.log'].search([
                ('timestamp', '>=', today_start)
            ], limit=10, order='timestamp desc')
            
            recent_activity = []
            for log in recent_logs:
                recent_activity.append({
                    'timestamp': log.timestamp.strftime('%H:%M'),
                    'action': log.display_name,
                    'actor': log.actor_name or 'System',
                    'details': log.details[:100] + '...' if len(log.details or '') > 100 else log.details
                })
            
            return {
                'active_processes': active_processes,
                'my_tasks': my_tasks,
                'overdue_tasks': overdue_tasks,
                'completed_today': completed_today,
                'recent_activity': recent_activity
            }
            
        except Exception as e:
            _logger.error("Error getting dashboard data: %s", str(e))
            return {
                'error': str(e)
            }
    
    @http.route('/bmp/process/<int:process_id>/start', type='json', auth='user')
    def start_process(self, process_id, **kwargs):
        """Start a process instance"""
        try:
            process_instance = request.env['bmp.process.instance'].browse(process_id)
            if not process_instance.exists():
                return {'error': 'Process instance not found'}
            
            if process_instance.state != 'draft':
                return {'error': 'Process instance is not in draft state'}
            
            process_instance.action_start()
            
            return {
                'success': True,
                'message': _('Process started successfully'),
                'process_id': process_id
            }
            
        except Exception as e:
            _logger.error("Error starting process %s: %s", process_id, str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/task/<int:task_id>/claim', type='json', auth='user')
    def claim_task(self, task_id, **kwargs):
        """Claim a task"""
        try:
            task = request.env['bmp.task.instance'].browse(task_id)
            if not task.exists():
                return {'error': 'Task not found'}
            
            if not task.can_claim:
                return {'error': 'You cannot claim this task'}
            
            task.action_claim()
            
            return {
                'success': True,
                'message': _('Task claimed successfully'),
                'task_id': task_id
            }
            
        except Exception as e:
            _logger.error("Error claiming task %s: %s", task_id, str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/task/<int:task_id>/complete', type='json', auth='user')
    def complete_task(self, task_id, form_data=None, **kwargs):
        """Complete a task"""
        try:
            task = request.env['bmp.task.instance'].browse(task_id)
            if not task.exists():
                return {'error': 'Task not found'}
            
            if not task.can_complete:
                return {'error': 'You cannot complete this task'}
            
            # Handle form data
            output_data = form_data or {}
            task.action_complete(output_data)
            
            return {
                'success': True,
                'message': _('Task completed successfully'),
                'task_id': task_id
            }
            
        except Exception as e:
            _logger.error("Error completing task %s: %s", task_id, str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/task/<int:task_id>/form_schema', type='json', auth='user')
    def get_task_form_schema(self, task_id, **kwargs):
        """Get form schema for a task"""
        try:
            task = request.env['bmp.task.instance'].browse(task_id)
            if not task.exists():
                return {'error': 'Task not found'}
            
            # Get form schema from task handler
            task_handler = request.env['bmp.task.handler'] 
            schema = task_handler.get_task_form_schema(task)
            
            return {
                'success': True,
                'schema': schema,
                'current_data': task.get_form_data()
            }
            
        except Exception as e:
            _logger.error("Error getting form schema for task %s: %s", task_id, str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/process/definition/<int:definition_id>/validate', type='json', auth='user')
    def validate_process_definition(self, definition_id, **kwargs):
        """Validate a process definition"""
        try:
            definition = request.env['bmp.process.definition'].browse(definition_id)
            if not definition.exists():
                return {'error': 'Process definition not found'}
            
            # Validate the BPMN XML
            definition._validate_and_parse_xml()
            
            return {
                'success': True,
                'message': _('Process definition is valid')
            }
            
        except Exception as e:
            _logger.error("Error validating process definition %s: %s", definition_id, str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/bmp/process/definition/create_from_xml', type='json', auth='user')
    def create_process_from_xml(self, name, xml_data, version='1.0', description='', **kwargs):
        """Create a process definition from BPMN XML"""
        try:
            definition = request.env['bmp.process.definition'].create({
                'name': name,
                'version': version,
                'description': description,
                'xml_data': xml_data,
                'is_active': True
            })
            
            return {
                'success': True,
                'message': _('Process definition created successfully'),
                'definition_id': definition.id
            }
            
        except Exception as e:
            _logger.error("Error creating process definition: %s", str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/integration/<int:integration_id>/test', type='json', auth='user', methods=['POST'])
    def test_integration(self, integration_id, test_data=None, **kwargs):
        """Test an integration configuration"""
        try:
            integration = request.env['bmp.integration'].browse(integration_id)
            if not integration.exists():
                return {'error': 'Integration not found'}
            
            # Create a mock record for testing
            if test_data:
                mock_record = type('MockRecord', (), test_data)()
                mock_record.env = request.env
                mock_record.id = 999999  # Fake ID
                
                # Test the integration
                result = integration.evaluate_trigger_condition(mock_record, 'create')
                
                return {
                    'success': True,
                    'result': result,
                    'message': _('Integration test completed')
                }
            else:
                return {'error': 'No test data provided'}
            
        except Exception as e:
            _logger.error("Error testing integration %s: %s", integration_id, str(e))
            return {'error': str(e)}