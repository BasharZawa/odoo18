# BPMN Engine Copilot

A complete BPMN 2.0 Engine for Odoo 18 - Business Process Automation

## Features

- **Complete BPMN 2.0 Support**: Full implementation of BPMN 2.0 specification
- **Visual Process Modeling**: Integration with bpmn-js for diagram editing
- **Robust Execution Engine**: Token-based process navigation system
- **User Task Management**: Dynamic forms and assignment workflows
- **Service Task Automation**: Python code execution and service integration
- **Process Monitoring**: Real-time dashboards and analytics
- **SLA Tracking**: Configurable rules and automated escalation
- **Odoo Integration**: Seamless integration with existing Odoo models
- **Enterprise Security**: Comprehensive permissions and audit trails

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list
3. Install the "BPMN Engine Copilot" module

## Quick Start

1. Navigate to BPMN Engine > Processes > Process Definitions
2. Create a new process definition with BPMN 2.0 XML
3. Activate the process definition
4. Create a process instance and start it
5. Complete tasks as they become available

## BPMN Elements Supported

### Events
- Start Events (message, timer, signal)
- End Events (terminate, message)
- Intermediate Events (timer, message)

### Tasks
- User Tasks with forms and assignments
- Service Tasks with Python execution
- Script Tasks with secure code execution
- Manual Tasks

### Gateways
- Exclusive Gateways with conditions
- Parallel Gateways with synchronization

### Flows
- Sequence Flows with conditions
- Message Flows (planned)

## Process Variables

The engine supports typed process variables:
- String, Integer, Float, Boolean
- Date, DateTime
- JSON objects
- Odoo record references

## SLA Management

Configure SLA rules with:
- Duration limits
- Warning thresholds
- Escalation actions
- Conditional rules

## API Endpoints

### REST API
- `/bmp/api/health` - Health check
- `/bmp/webhook/process/start` - Start process via webhook
- `/bmp/webhook/task/complete` - Complete task via webhook
- `/bmp/webhook/process/status` - Get process status

### JSON-RPC
- `/bmp/dashboard/data` - Dashboard statistics
- `/bmp/process/<id>/start` - Start process instance
- `/bmp/task/<id>/claim` - Claim task
- `/bmp/task/<id>/complete` - Complete task

## Security

The module includes comprehensive security:
- User groups (User, Manager, Admin)
- Record-level access rules
- Task-level permissions
- Complete audit trail

## Configuration

### Security Groups
- **BPMN User**: Basic access to view and execute processes
- **BPMN Manager**: Create and manage processes
- **BPMN Administrator**: Full system access

### Cron Jobs
- SLA monitoring (every 15 minutes)
- Process cleanup (daily)
- Timer events (every 5 minutes)

## Integration Examples

### Trigger Process on Record Creation
```python
# Create integration configuration
integration = env['bmp.integration'].create({
    'name': 'Lead Approval Process',
    'model_name': 'crm.lead',
    'process_definition_id': process_def.id,
    'trigger_on_create': True,
    'trigger_condition': 'record.amount_total > 10000',
    'variable_mapping': json.dumps({
        'lead_name': 'name',
        'customer': 'partner_id.name',
        'amount': 'amount_total'
    })
})
```

### Service Task Example
```python
def approve_lead(self, task_instance):
    """Service task to approve a lead"""
    lead_id = task_instance.get_variable('lead_id')
    lead = self.env['crm.lead'].browse(lead_id)
    lead.write({'stage_id': approved_stage.id})
    
    # Set output variables
    task_instance.set_variable('approval_date', fields.Date.today())
    task_instance.set_variable('approved_by', self.env.user.name)
```

## License

LGPL-3

## Support

For support and documentation, visit the module repository or contact your system administrator.