# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class BmpSlaRule(models.Model):
    _name = 'bmp.sla.rule'
    _description = 'BPMN SLA Rule'
    _order = 'priority desc, name'

    name = fields.Char(
        string='Rule Name',
        required=True,
        help='Name of the SLA rule'
    )
    
    process_definition_id = fields.Many2one(
        'bmp.process.definition',
        string='Process Definition',
        help='Process definition this rule applies to (leave empty for all processes)'
    )
    
    task_id = fields.Char(
        string='Task ID',
        help='Specific BPMN task ID this rule applies to (leave empty for all tasks)'
    )
    
    task_type = fields.Selection([
        ('user', 'User Task'),
        ('service', 'Service Task'),
        ('manual', 'Manual Task'),
        ('script', 'Script Task'),
    ], string='Task Type', help='Type of tasks this rule applies to')
    
    # SLA timing
    duration_hours = fields.Float(
        string='Duration (Hours)',
        required=True,
        help='Maximum allowed duration in hours'
    )
    
    warning_threshold = fields.Float(
        string='Warning Threshold (%)',
        default=80.0,
        help='Percentage of duration at which to send warning (0-100)'
    )
    
    # Conditions
    condition_expression = fields.Text(
        string='Condition Expression',
        help='Python expression to evaluate if this rule applies (optional)'
    )
    
    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Rule priority (higher numbers take precedence)'
    )
    
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this SLA rule is active'
    )
    
    # Escalation settings
    escalation_enabled = fields.Boolean(
        string='Enable Escalation',
        default=True,
        help='Whether to escalate when SLA is breached'
    )
    
    escalation_user_ids = fields.Many2many(
        'res.users',
        string='Escalation Users',
        help='Users to notify when SLA is breached'
    )
    
    escalation_action = fields.Selection([
        ('notify', 'Notify Only'),
        ('reassign', 'Reassign Task'),
        ('skip', 'Skip Task'),
        ('fail', 'Fail Task'),
    ], string='Escalation Action', default='notify')
    
    reassign_to_user_id = fields.Many2one(
        'res.users',
        string='Reassign To User',
        help='User to reassign task to when escalating'
    )
    
    # Statistics
    violations_count = fields.Integer(
        string='Violations Count',
        compute='_compute_statistics',
        help='Number of SLA violations for this rule'
    )
    
    warnings_count = fields.Integer(
        string='Warnings Count',
        compute='_compute_statistics',
        help='Number of SLA warnings for this rule'
    )
    
    @api.depends('name')  # Placeholder dependency - would need actual SLA tracking records
    def _compute_statistics(self):
        # TODO: Implement actual statistics computation when SLA tracking is added
        for record in self:
            record.violations_count = 0
            record.warnings_count = 0
    
    def evaluate_condition(self, task_instance):
        """Evaluate if this SLA rule applies to the given task instance"""
        if not self.is_active:
            return False
        
        # Check process definition
        if self.process_definition_id and task_instance.process_instance_id.process_definition_id != self.process_definition_id:
            return False
        
        # Check task ID
        if self.task_id and task_instance.task_id != self.task_id:
            return False
        
        # Check task type
        if self.task_type and task_instance.task_type != self.task_type:
            return False
        
        # Evaluate custom condition
        if self.condition_expression:
            try:
                # Create safe evaluation context
                context = {
                    'task': task_instance,
                    'process': task_instance.process_instance_id,
                    'env': task_instance.env,
                    'user': task_instance.env.user,
                }
                
                result = eval(self.condition_expression, {"__builtins__": {}}, context)
                return bool(result)
            except Exception as e:
                _logger.error("Error evaluating SLA condition for rule %s: %s", self.name, str(e))
                return False
        
        return True
    
    def calculate_due_date(self, task_instance):
        """Calculate the due date for a task based on this SLA rule"""
        if not task_instance.created_at:
            return False
        
        from datetime import timedelta
        due_date = task_instance.created_at + timedelta(hours=self.duration_hours)
        return due_date
    
    def calculate_warning_date(self, task_instance):
        """Calculate the warning date for a task based on this SLA rule"""
        due_date = self.calculate_due_date(task_instance)
        if not due_date:
            return False
        
        from datetime import timedelta
        warning_hours = self.duration_hours * (self.warning_threshold / 100)
        warning_date = task_instance.created_at + timedelta(hours=warning_hours)
        return warning_date
    
    def check_sla_breach(self, task_instance):
        """Check if SLA is breached for the given task"""
        if task_instance.status in ['completed', 'cancelled', 'skipped']:
            return False
        
        due_date = self.calculate_due_date(task_instance)
        if not due_date:
            return False
        
        return fields.Datetime.now() > due_date
    
    def check_sla_warning(self, task_instance):
        """Check if SLA warning threshold is reached for the given task"""
        if task_instance.status in ['completed', 'cancelled', 'skipped']:
            return False
        
        warning_date = self.calculate_warning_date(task_instance)
        if not warning_date:
            return False
        
        return fields.Datetime.now() > warning_date
    
    def escalate_task(self, task_instance):
        """Escalate a task according to this SLA rule"""
        if not self.escalation_enabled:
            return
        
        # Log escalation
        task_instance._log_activity(
            'escalation',
            _("SLA rule '%s' triggered escalation") % self.name
        )
        
        # Notify escalation users
        if self.escalation_user_ids:
            self._send_escalation_notification(task_instance)
        
        # Perform escalation action
        if self.escalation_action == 'reassign' and self.reassign_to_user_id:
            task_instance.action_delegate(self.reassign_to_user_id.id)
        elif self.escalation_action == 'skip':
            task_instance.action_skip(_("Escalated due to SLA breach"))
        elif self.escalation_action == 'fail':
            task_instance.action_fail(_("Failed due to SLA breach"))
    
    def _send_escalation_notification(self, task_instance):
        """Send escalation notification to configured users"""
        # TODO: Implement email notification
        # This would integrate with Odoo's mail system
        pass
    
    @api.model
    def get_applicable_rules(self, task_instance):
        """Get all SLA rules applicable to a task instance"""
        all_rules = self.search([('is_active', '=', True)], order='priority desc')
        
        applicable_rules = []
        for rule in all_rules:
            if rule.evaluate_condition(task_instance):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    @api.model
    def apply_sla_to_task(self, task_instance):
        """Apply SLA rules to a task instance"""
        applicable_rules = self.get_applicable_rules(task_instance)
        
        if not applicable_rules:
            return
        
        # Use the highest priority rule
        primary_rule = applicable_rules[0]
        
        # Set due date
        due_date = primary_rule.calculate_due_date(task_instance)
        if due_date:
            task_instance.write({'due_date': due_date})
        
        # Log SLA application
        task_instance._log_activity(
            'sla_applied',
            _("SLA rule '%s' applied - Due: %s") % (primary_rule.name, due_date)
        )
    
    @api.constrains('warning_threshold')
    def _check_warning_threshold(self):
        for record in self:
            if not (0 <= record.warning_threshold <= 100):
                raise ValidationError(_("Warning threshold must be between 0 and 100"))
    
    @api.constrains('duration_hours')
    def _check_duration(self):
        for record in self:
            if record.duration_hours <= 0:
                raise ValidationError(_("Duration must be positive"))