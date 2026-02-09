import json
import logging
import requests
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SmartReportController(http.Controller):

    # ─────────────────────────────────────────────
    #  Main endpoint: natural language → report data
    # ─────────────────────────────────────────────
    @http.route('/smart_report/query', type='json', auth='user', methods=['POST'])
    def process_query(self, query, **kwargs):
        """
        Receives a natural language query from the frontend.
        1. Fetches model metadata from Odoo
        2. Sends query + metadata to n8n webhook (→ Claude)
        3. Executes the returned read_group params
        4. Returns data to frontend
        """
        try:
            # Step 1: Get model metadata for Claude's context
            model_info = request.env['smart.report.model.info'].sudo() \
                .get_available_models()

            # Step 2: Call n8n webhook with query + context
            ai_response = self._call_n8n(query, model_info)

            if ai_response.get('error'):
                return {'error': ai_response['error']}

            # Step 3: Execute the query on Odoo
            report_data = self._execute_report(ai_response)

            # Step 4: Return everything to frontend
            return {
                'success': True,
                'query_params': ai_response,
                'data': report_data,
            }

        except Exception as e:
            _logger.exception("Smart Report query failed")
            return {'error': str(e)}

    # ─────────────────────────────────────────────
    #  Call n8n webhook
    # ─────────────────────────────────────────────
    def _call_n8n(self, query, model_info):
        """Send the NL query + Odoo schema to n8n → Claude"""
        ICP = request.env['ir.config_parameter'].sudo()
        webhook_url = ICP.get_param('smart_report_builder.n8n_webhook_url', '')
        auth_token = ICP.get_param('smart_report_builder.n8n_auth_token', '')

        if not webhook_url:
            return {'error': 'n8n webhook URL not configured. Go to Settings → Smart Report Builder.'}

        headers = {'Content-Type': 'application/json'}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        payload = {
            'query': query,
            'today': datetime.now().strftime('%Y-%m-%d'),
            'models': model_info,
        }

        try:
            resp = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()

            # n8n may wrap response differently
            # Handle both direct and wrapped responses
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            if 'output' in result:
                result = result['output']

            # Validate required fields
            required = ['model', 'domain', 'groupby', 'measures']
            for field in required:
                if field not in result:
                    return {'error': f'AI response missing "{field}". Raw: {json.dumps(result)[:200]}'}

            return result

        except requests.exceptions.Timeout:
            return {'error': 'n8n webhook timed out (30s). Check your n8n instance.'}
        except requests.exceptions.ConnectionError:
            return {'error': 'Cannot connect to n8n. Check the webhook URL and that n8n is running.'}
        except Exception as e:
            return {'error': f'n8n call failed: {str(e)}'}

    # ─────────────────────────────────────────────
    #  Execute read_group on Odoo
    # ─────────────────────────────────────────────
    def _execute_report(self, params):
        """Execute read_group with Claude's parameters"""
        model_name = params['model']
        domain = params.get('domain', [])
        groupby = params.get('groupby', [])
        measures = params.get('measures', [])
        order = params.get('order', None)
        limit = params.get('limit', None)

        # Validate model exists
        if model_name not in request.env:
            raise ValueError(f"Model '{model_name}' not found in this Odoo instance.")

        model_obj = request.env[model_name].sudo()

        # Parse domain if it's a string
        if isinstance(domain, str):
            domain = json.loads(domain)

        # Execute read_group
        raw_results = model_obj.read_group(
            domain=domain,
            fields=measures,
            groupby=groupby,
            orderby=order,
            limit=limit,
            lazy=False,
        )

        # Clean results for JSON
        clean_results = []
        for row in raw_results:
            clean_row = {}
            for key, value in row.items():
                if key == '__domain':
                    continue
                if isinstance(value, tuple):
                    clean_row[key] = value[1] if value else 'N/A'
                elif isinstance(value, (datetime,)):
                    clean_row[key] = value.isoformat()
                else:
                    clean_row[key] = value
            # Include the count
            if '__count' in row:
                clean_row['__count'] = row['__count']
            clean_results.append(clean_row)

        return clean_results

    # ─────────────────────────────────────────────
    #  Save a report for reuse
    # ─────────────────────────────────────────────
    @http.route('/smart_report/save', type='json', auth='user', methods=['POST'])
    def save_report(self, name, query, params, **kwargs):
        """Save a report configuration for later reuse"""
        try:
            report = request.env['smart.report'].sudo().create({
                'name': name,
                'natural_query': query,
                'model_name': params.get('model', ''),
                'domain': json.dumps(params.get('domain', [])),
                'group_by': json.dumps(params.get('groupby', [])),
                'measures': json.dumps(params.get('measures', [])),
                'chart_type': params.get('chart_type', 'bar'),
                'user_id': request.env.user.id,
            })
            return {'success': True, 'report_id': report.id}
        except Exception as e:
            return {'error': str(e)}

    # ─────────────────────────────────────────────
    #  Load saved reports
    # ─────────────────────────────────────────────
    @http.route('/smart_report/saved', type='json', auth='user', methods=['POST'])
    def get_saved_reports(self, **kwargs):
        """Get all saved reports for current user"""
        reports = request.env['smart.report'].sudo().search([
            '|',
            ('user_id', '=', request.env.user.id),
            ('is_favorite', '=', True),
        ])
        return [{
            'id': r.id,
            'name': r.name,
            'natural_query': r.natural_query,
            'model_name': r.model_name,
            'chart_type': r.chart_type,
            'is_favorite': r.is_favorite,
        } for r in reports]

    # ─────────────────────────────────────────────
    #  Re-run a saved report
    # ─────────────────────────────────────────────
    @http.route('/smart_report/run_saved', type='json', auth='user', methods=['POST'])
    def run_saved_report(self, report_id, **kwargs):
        """Re-execute a saved report"""
        report = request.env['smart.report'].sudo().browse(int(report_id))
        if not report.exists():
            return {'error': 'Report not found'}

        params = {
            'model': report.model_name,
            'domain': json.loads(report.domain or '[]'),
            'groupby': json.loads(report.group_by or '[]'),
            'measures': json.loads(report.measures or '[]'),
            'chart_type': report.chart_type,
            'title': report.name,
        }

        data = self._execute_report(params)
        return {
            'success': True,
            'query_params': params,
            'data': data,
        }

    # ─────────────────────────────────────────────
    #  Fetch model schema (for debugging / dev tools)
    # ─────────────────────────────────────────────
    @http.route('/smart_report/schema', type='json', auth='user', methods=['POST'])
    def get_schema(self, **kwargs):
        """Return the model metadata (useful for debugging prompts)"""
        model_info = request.env['smart.report.model.info'].sudo() \
            .get_available_models()
        return model_info
