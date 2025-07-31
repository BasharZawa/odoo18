# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class BmpWebhookController(http.Controller):
    
    @http.route('/bmp/webhook/process/start', type='json', auth='public', csrf=False)
    def webhook_start_process(self, **kwargs):
        """Webhook endpoint to start a process"""
        try:
            # Get parameters
            process_definition_name = kwargs.get('process_definition')
            process_variables = kwargs.get('variables', {})
            related_model = kwargs.get('related_model')
            related_id = kwargs.get('related_id')
            
            if not process_definition_name:
                return {'error': 'process_definition parameter is required'}
            
            # Find process definition
            definition = request.env['bmp.process.definition'].sudo().search([
                ('name', '=', process_definition_name),
                ('is_active', '=', True)
            ], limit=1)
            
            if not definition:
                return {'error': f'Active process definition "{process_definition_name}" not found'}
            
            # Create process instance
            instance_data = {
                'process_definition_id': definition.id,
                'state': 'draft'
            }
            
            if related_model and related_id:
                instance_data.update({
                    'related_record_model': related_model,
                    'related_record_id': related_id
                })
            
            instance = request.env['bmp.process.instance'].sudo().create(instance_data)
            
            # Set process variables
            for key, value in process_variables.items():
                instance.set_variable(key, value)
            
            # Start the process
            instance.action_start()
            
            return {
                'success': True,
                'process_instance_id': instance.id,
                'message': f'Process "{process_definition_name}" started successfully'
            }
            
        except Exception as e:
            _logger.error("Error in webhook start process: %s", str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/webhook/task/complete', type='json', auth='public', csrf=False)
    def webhook_complete_task(self, **kwargs):
        """Webhook endpoint to complete a task"""
        try:
            # Get parameters
            task_id = kwargs.get('task_id')
            process_instance_id = kwargs.get('process_instance_id')
            task_name = kwargs.get('task_name')
            output_data = kwargs.get('output_data', {})
            
            # Find task
            task = None
            if task_id:
                task = request.env['bmp.task.instance'].sudo().browse(task_id)
            elif process_instance_id and task_name:
                task = request.env['bmp.task.instance'].sudo().search([
                    ('process_instance_id', '=', process_instance_id),
                    ('task_name', '=', task_name),
                    ('status', 'in', ['ready', 'claimed', 'in_progress'])
                ], limit=1)
            
            if not task or not task.exists():
                return {'error': 'Task not found'}
            
            # Complete the task
            task.action_complete(output_data)
            
            return {
                'success': True,
                'task_id': task.id,
                'message': f'Task "{task.task_name}" completed successfully'
            }
            
        except Exception as e:
            _logger.error("Error in webhook complete task: %s", str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/webhook/process/signal', type='json', auth='public', csrf=False)
    def webhook_process_signal(self, **kwargs):
        """Webhook endpoint to send a signal to a process"""
        try:
            # Get parameters
            process_instance_id = kwargs.get('process_instance_id')
            signal_name = kwargs.get('signal_name')
            signal_data = kwargs.get('signal_data', {})
            
            if not process_instance_id or not signal_name:
                return {'error': 'process_instance_id and signal_name are required'}
            
            # Find process instance
            instance = request.env['bmp.process.instance'].sudo().browse(process_instance_id)
            if not instance.exists():
                return {'error': 'Process instance not found'}
            
            # TODO: Implement signal handling
            # For now, just log the signal
            request.env['bmp.activity.log'].sudo().create({
                'process_instance_id': instance.id,
                'action_type': 'signal_received',
                'timestamp': request.env['odoo.fields'].Datetime.now(),
                'details': f'Signal "{signal_name}" received via webhook',
                'new_values': json.dumps(signal_data)
            })
            
            return {
                'success': True,
                'message': f'Signal "{signal_name}" sent to process {process_instance_id}'
            }
            
        except Exception as e:
            _logger.error("Error in webhook process signal: %s", str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/webhook/process/status', type='http', auth='public', csrf=False)
    def webhook_process_status(self, process_instance_id=None, **kwargs):
        """Webhook endpoint to get process status"""
        try:
            if not process_instance_id:
                return json.dumps({'error': 'process_instance_id parameter is required'})
            
            # Find process instance
            instance = request.env['bmp.process.instance'].sudo().browse(int(process_instance_id))
            if not instance.exists():
                return json.dumps({'error': 'Process instance not found'})
            
            # Get status information
            status_data = {
                'process_instance_id': instance.id,
                'process_name': instance.process_definition_id.name,
                'state': instance.state,
                'progress_percentage': instance.progress_percentage,
                'started_at': instance.started_at.isoformat() if instance.started_at else None,
                'ended_at': instance.ended_at.isoformat() if instance.ended_at else None,
                'duration_hours': instance.duration,
                'current_activity': instance.current_activity,
                'total_tasks': instance.total_tasks,
                'completed_tasks': instance.completed_tasks,
                'active_tasks': instance.active_tasks
            }
            
            # Get active tasks
            active_tasks = instance.task_instances.filtered(
                lambda t: t.status in ['ready', 'claimed', 'in_progress']
            )
            
            status_data['active_task_list'] = []
            for task in active_tasks:
                status_data['active_task_list'].append({
                    'task_id': task.id,
                    'task_name': task.task_name,
                    'task_type': task.task_type,
                    'status': task.status,
                    'assigned_user': task.assigned_user_id.name if task.assigned_user_id else None,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                    'is_overdue': task.is_overdue
                })
            
            response = request.make_response(
                json.dumps(status_data, indent=2),
                headers=[('Content-Type', 'application/json')]
            )
            return response
            
        except Exception as e:
            _logger.error("Error in webhook process status: %s", str(e))
            response = request.make_response(
                json.dumps({'error': str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
            return response
    
    @http.route('/bmp/webhook/integration/trigger', type='json', auth='public', csrf=False)
    def webhook_integration_trigger(self, **kwargs):
        """Webhook endpoint to trigger integration"""
        try:
            # Get parameters
            integration_name = kwargs.get('integration_name')
            model_name = kwargs.get('model_name')
            record_id = kwargs.get('record_id')
            operation = kwargs.get('operation', 'create')
            record_data = kwargs.get('record_data', {})
            
            if not integration_name:
                return {'error': 'integration_name parameter is required'}
            
            # Find integration
            integration = request.env['bmp.integration'].sudo().search([
                ('name', '=', integration_name),
                ('is_active', '=', True)
            ], limit=1)
            
            if not integration:
                return {'error': f'Active integration "{integration_name}" not found'}
            
            # Create mock record or get existing record
            if record_id and model_name:
                record = request.env[model_name].sudo().browse(record_id)
                if not record.exists():
                    return {'error': f'Record {record_id} not found in model {model_name}'}
            else:
                # Create mock record from provided data
                if not model_name:
                    model_name = integration.model_name
                
                record = type('MockRecord', (), record_data)()
                record.env = request.env.sudo()
                record.id = record_data.get('id', 999999)
                record._name = model_name
            
            # Trigger the integration
            process_instance = integration.trigger_process(record, operation)
            
            if process_instance:
                return {
                    'success': True,
                    'process_instance_id': process_instance.id,
                    'message': f'Integration "{integration_name}" triggered successfully'
                }
            else:
                return {
                    'success': False,
                    'message': f'Integration "{integration_name}" did not trigger (conditions not met)'
                }
            
        except Exception as e:
            _logger.error("Error in webhook integration trigger: %s", str(e))
            return {'error': str(e)}
    
    @http.route('/bmp/api/health', type='http', auth='public', csrf=False)
    def api_health_check(self, **kwargs):
        """Health check endpoint for the BPMN API"""
        try:
            # Basic health check
            process_count = request.env['bmp.process.definition'].sudo().search_count([])
            instance_count = request.env['bmp.process.instance'].sudo().search_count([])
            
            health_data = {
                'status': 'healthy',
                'timestamp': request.env['odoo.fields'].Datetime.now().isoformat(),
                'process_definitions': process_count,
                'process_instances': instance_count,
                'version': '1.0.0'
            }
            
            response = request.make_response(
                json.dumps(health_data, indent=2),
                headers=[('Content-Type', 'application/json')]
            )
            return response
            
        except Exception as e:
            _logger.error("Error in API health check: %s", str(e))
            response = request.make_response(
                json.dumps({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': request.env['odoo.fields'].Datetime.now().isoformat()
                }),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
            return response