from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)


class SmartReport(models.Model):
    _name = 'smart.report'
    _description = 'Smart Report'
    _order = 'write_date desc'

    name = fields.Char(string='Report Title', required=True)
    natural_query = fields.Text(string='Natural Language Query')
    model_name = fields.Char(string='Odoo Model')
    domain = fields.Text(string='Domain Filter', default='[]')
    group_by = fields.Text(string='Group By', default='[]')
    measures = fields.Text(string='Measures', default='[]')
    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('table', 'Table Only'),
    ], string='Chart Type', default='bar')
    last_result = fields.Text(string='Last Result (JSON)')
    is_favorite = fields.Boolean(string='Favorite', default=False)
    user_id = fields.Many2one('res.users', string='Created By',
                              default=lambda self: self.env.user)

    def action_run_report(self):
        """Execute the saved report and return results"""
        self.ensure_one()
        try:
            model_obj = self.env[self.model_name].sudo()
            domain = json.loads(self.domain or '[]')
            group_by = json.loads(self.group_by or '[]')
            measures = json.loads(self.measures or '[]')

            # Execute read_group
            results = model_obj.read_group(
                domain=domain,
                fields=measures,
                groupby=group_by,
                lazy=False,
            )

            # Clean up results for JSON serialization
            clean_results = []
            for row in results:
                clean_row = {}
                for key, value in row.items():
                    if key == '__domain':
                        continue
                    if isinstance(value, tuple):
                        # Many2one field: (id, name)
                        clean_row[key] = value[1] if value else 'Undefined'
                    else:
                        clean_row[key] = value
                clean_results.append(clean_row)

            self.last_result = json.dumps(clean_results)
            return clean_results

        except Exception as e:
            _logger.error(f"Smart Report execution error: {str(e)}")
            raise


class SmartReportModelInfo(models.TransientModel):
    """Helper to fetch model and field metadata for Claude context"""
    _name = 'smart.report.model.info'
    _description = 'Smart Report Model Info'

    @api.model
    def get_available_models(self):
        """Return list of commonly used models with their fields"""
        # Key business models developers typically need reports on
        target_models = [
            'sale.order', 'sale.order.line',
            'purchase.order', 'purchase.order.line',
            'account.move', 'account.move.line',
            'stock.picking', 'stock.move',
            'crm.lead',
            'project.task', 'project.project',
            'hr.employee', 'hr.leave',
            'product.product', 'product.template',
            'res.partner',
        ]

        result = {}
        for model_name in target_models:
            try:
                model_obj = self.env[model_name]
                fields_info = model_obj.fields_get(
                    attributes=['string', 'type', 'selection', 'relation']
                )

                # Filter to useful reportable fields
                useful_fields = {}
                reportable_types = [
                    'integer', 'float', 'monetary',
                    'many2one', 'selection', 'date', 'datetime',
                    'char', 'boolean',
                ]
                skip_fields = [
                    'id', 'create_uid', 'write_uid',
                    'create_date', 'write_date',
                    '__last_update', 'display_name',
                ]

                for fname, fdata in fields_info.items():
                    if (fdata['type'] in reportable_types
                            and fname not in skip_fields
                            and not fname.startswith('message_')
                            and not fname.startswith('website_')):
                        useful_fields[fname] = {
                            'label': fdata['string'],
                            'type': fdata['type'],
                        }
                        if fdata.get('selection'):
                            useful_fields[fname]['options'] = fdata['selection']
                        if fdata.get('relation'):
                            useful_fields[fname]['relation'] = fdata['relation']

                result[model_name] = {
                    'name': model_obj._description or model_name,
                    'fields': useful_fields,
                }
            except Exception:
                # Model not installed, skip
                continue

        return result
