from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json

class ProcessDefinitionActivity(models.Model):
    _name = "process.definition.activity"
    _description = "BPM Process Definition Activity"
    _order = "sequence, id"

    # Basic fields
    definition_id = fields.Many2one("process.definition", required=True, ondelete="cascade", string="Process Definition")
    sequence = fields.Integer(default=10, help="Order of activities in the process")
    node_id = fields.Char(required=True, help="BPMN node identifier (e.g., Task_1, Gateway_1)")
    name = fields.Char(required=True, help="Activity name/label")
    
    # Activity type and configuration
    type = fields.Selection([
        ('start', 'Start Event'),
        ('end', 'End Event'),
        ('task', 'User Task'),
        ('sys', 'Service Task'),
        ('if', 'Exclusive Gateway'),
        ('pbranch', 'Parallel Gateway (Split)'),
        ('pwait', 'Parallel Gateway (Join)'),
        ('wtime', 'Timer Event'),
        ('wevent', 'Message Event'),
        ('wcond', 'Conditional Event')
    ], required=True, string="Activity Type")
    
    description = fields.Text(help="Activity description")
    active = fields.Boolean(default=True)
    
    # Flow control
    next_activity_id = fields.Many2one("process.definition.activity", string="Next Activity", 
                        )
    next_activity_ids = fields.Many2many("process.definition.activity", 
                                        relation="bpm_activity_next_rel",
                                        column1="activity_id", column2="next_activity_id",
                                        string="Next Activities (Multiple)",
                        )
    
    assignee_role_id = fields.Many2one('bpm.role', string="Assigned BPM Role")
    
    # Approval routing for user tasks
    next_approve_activity_id = fields.Many2one("process.definition.activity", 
                                              string="Next on Approve",
                                )
    next_reject_activity_id = fields.Many2one("process.definition.activity", 
                                             string="Next on Reject",
                                )
    
    # Service Task fields
    service_action = fields.Char(string="Service Action", 
                                help="Dotted path to service function (e.g., my_module.actions.send_email)")
    
    # Gateway fields
    condition_expression = fields.Text(string="Gateway Condition", 
                                      help="Python expression for exclusive gateway (e.g., ctx.get('amount', 0) > 1000)")
    true_activity_id = fields.Many2one("process.definition.activity", 
                                      string="True Branch",
                        )
    false_activity_id = fields.Many2one("process.definition.activity", 
                                       string="False Branch", 
                        )
    
    # Parallel gateway fields
    join_activity_id = fields.Many2one("process.definition.activity", 
                                      string="Join Activity",
                        )
    branch_activity_ids = fields.Many2many("process.definition.activity",
                                          relation="bpm_activity_branch_rel", 
                                          column1="split_activity_id", column2="branch_activity_id",
                                          string="Branch Activities",
                            )
    
    # Timer fields
    delay_seconds = fields.Integer(string="Delay (Seconds)", default=0)
    delay_minutes = fields.Integer(string="Delay (Minutes)", default=0)
    delay_hours = fields.Integer(string="Delay (Hours)", default=0)
    delay_days = fields.Integer(string="Delay (Days)", default=0)
    
    # Event fields
    event_name = fields.Char(string="Event Name", help="Name of the message event to wait for")
    correlation_key = fields.Char(string="Correlation Key", help="Key to correlate the event")
    
    # Advanced configuration
    custom_data = fields.Json(string="Custom Data", default=dict, 
                             help="Additional configuration data for this activity")
    
    # Computed fields
    total_delay_seconds = fields.Integer(string="Total Delay (Seconds)", compute="_compute_total_delay", store=True)
    
    form_url = fields.Char(string="Form URL", 
                          help="URL of the form to display for user tasks (can include placeholders like ${field})")


    @api.depends('delay_seconds', 'delay_minutes', 'delay_hours', 'delay_days')
    def _compute_total_delay(self):
        for activity in self:
            activity.total_delay_seconds = (
                activity.delay_seconds +
                activity.delay_minutes * 60 +
                activity.delay_hours * 3600 +
                activity.delay_days * 86400
            )
    
    @api.constrains('node_id', 'definition_id')
    def _check_unique_node_id(self):
        for activity in self:
            if self.search_count([
                ('definition_id', '=', activity.definition_id.id),
                ('node_id', '=', activity.node_id),
                ('id', '!=', activity.id)
            ]) > 0:
                raise ValidationError(_("Node ID '%s' must be unique within the process definition.") % activity.node_id)
    
    @api.constrains('service_action')
    def _check_service_action(self):
        for activity in self:
            if activity.type == 'sys' and activity.service_action:
                # Check if service action is registered in whitelist
                registry = self.env['registry'].search([
                    ('dotted_path', '=', activity.service_action), # Assuming a 'registry' model exists
                    ('kind', '=', 'system_action') # and kind field to differentiate types
                ])
                if not registry:
                    raise ValidationError(
                        _("Service action '%s' is not registered in the BPM Registry.") % 
                        activity.service_action
                    )
    
    def get_assignee_user_id(self, context=None):
        """
        Resolve the assignee user ID based on the assignee type and configuration
        """
        self.ensure_one()
        ctx = context or {}
        # Get current assignee from the BPM role
        assigned_user = self.assignee_role_id.get_current_assignee()
        return assigned_user.id if assigned_user else False
            
    
    def to_json_node(self):
        """
        Convert this activity to JSON node format for the engine
        """
        self.ensure_one()
        
        node = {
            'id': self.node_id,
            'type': self.type,
        }
        
        # Add type-specific data
        if self.type == 'start':
            node['next'] = self.next_activity_id.node_id if self.next_activity_id else None
            
        elif self.type == 'end':
            pass  # End nodes don't need additional data
            
        elif self.type == 'task':
            node.update({
                'label': self.name,
                'assignee_id': self.assignee_id.id if self.assignee_type == 'static' else None,
                'assignee_role_id': self.assignee_role_id.id if self.assignee_type == 'role' else None,
                'next': self.next_activity_id.node_id if self.next_activity_id else None,
                'next_approve': self.next_approve_activity_id.node_id if self.next_approve_activity_id else None,
                'next_reject': self.next_reject_activity_id.node_id if self.next_reject_activity_id else None,
            })
            
        elif self.type == 'sys':
            node.update({
                'action': self.service_action,
                'next': self.next_activity_id.node_id if self.next_activity_id else None,
            })
            
        elif self.type == 'if':
            node.update({
                'expression': self.condition_expression,
                'on_true': self.true_activity_id.node_id if self.true_activity_id else None,
                'on_false': self.false_activity_id.node_id if self.false_activity_id else None,
            })
            
        elif self.type == 'pbranch':
            node.update({
                'branches': [act.node_id for act in self.branch_activity_ids],
                'join': self.join_activity_id.node_id if self.join_activity_id else None,
                'next': self.next_activity_id.node_id if self.next_activity_id else None,
            })
            
        elif self.type == 'pwait':
            node['next'] = self.next_activity_id.node_id if self.next_activity_id else None
            
        elif self.type == 'wtime':
            node.update({
                'delay_seconds': self.total_delay_seconds,
                'next': self.next_activity_id.node_id if self.next_activity_id else None,
            })
            
        elif self.type == 'wevent':
            node.update({
                'event_name': self.event_name,
                'correlation_key': self.correlation_key,
                'next': self.next_activity_id.node_id if self.next_activity_id else None,
            })
        
        # Add custom data if present
        if self.custom_data:
            node.update(self.custom_data)
            
        return node
    
    @api.model
    def name_get(self):
        result = []
        for activity in self:
            name = f"[{activity.node_id}] {activity.name} ({dict(activity._fields['type'].selection)[activity.type]})"
            result.append((activity.id, name))
        return result
