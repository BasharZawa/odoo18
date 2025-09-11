# BPM Process Definition Activity Model

## Overview

The [`BpmProcessDefinitionActivity`](odoo/custom_addons/sedco_bpm_engine/models/process_definition_activity.py) model is a core component of the SEDCO BPM Engine that defines individual activities (nodes) within business process workflows. Each activity represents a specific step in a BPMN (Business Process Model and Notation) diagram and contains the configuration needed to execute that step.

## Business Purpose

### What is a Process Activity?

A process activity is a building block of business processes that represents:
- **Tasks** that need human interaction (approvals, reviews, data entry)
- **System actions** that run automatically (sending emails, creating records, calculations)
- **Decision points** that route the process based on conditions
- **Events** that wait for external triggers or timers
- **Gateways** that control process flow (parallel execution, conditional routing)

### Key Business Benefits

1. **Visual Process Design**: Activities map directly to BPMN diagram elements
2. **Role-based Assignment**: Tasks can be assigned to users, groups, or organizational roles
3. **Flexible Routing**: Support for approval workflows, parallel processing, and conditional logic
4. **Process Automation**: Mix of human tasks and automated system actions
5. **Event-driven Processing**: Integration with external systems through message events
6. **Audit Trail**: Complete tracking of process execution through activity instances

## Technical Architecture

### Model Structure

The model extends Odoo's base model with the following key characteristics:

```python
_name = "process.definition.activity"
_description = "BPM Process Definition Activity"
_order = "sequence, id"
```

### Core Fields

#### Basic Configuration
- **`definition_id`**: Links to the parent [`BpmProcessDefinition`](odoo/custom_addons/sedco_bpm_engine/models/process_definition.py)
- **`sequence`**: Determines display order in activity lists
- **`node_id`**: Unique BPMN identifier (e.g., "Task_1", "Gateway_2")
- **`name`**: Human-readable activity label
- **`type`**: Activity type selector (see Activity Types section)
- **`description`**: Optional detailed description
- **`active`**: Boolean flag for archiving activities

#### Flow Control
- **`next_activity_id`**: Default next activity for linear flows
- **`next_activity_ids`**: Multiple next activities for parallel splits
- **`next_approve_activity_id`**: Routing for approval scenarios
- **`next_reject_activity_id`**: Routing for rejection scenarios

### Activity Types

The model supports 10 different activity types through a selection field:

#### 1. Start Event (`start`)
- **Purpose**: Entry point for process instances
- **Configuration**: Single next activity
- **Business Use**: Process initiation trigger

#### 2. End Event (`end`)
- **Purpose**: Terminates process execution
- **Configuration**: No outgoing flows
- **Business Use**: Process completion

#### 3. User Task (`task`)
- **Purpose**: Human interaction required
- **Configuration**: 
  - Assignee configuration (static user, resolver function, group, or BPM role)
  - Approval routing (approve/reject paths)
- **Business Use**: Approvals, reviews, data entry, decision making

#### 4. Service Task (`sys`)
- **Purpose**: Automated system actions
- **Configuration**: Service action (dotted path to Python function)
- **Business Use**: Email notifications, record creation, calculations, integrations

#### 5. Exclusive Gateway (`if`)
- **Purpose**: Conditional routing (one path chosen)
- **Configuration**: Python expression for condition evaluation
- **Business Use**: Business rule routing (amount thresholds, status checks)

#### 6. Parallel Gateway Split (`pbranch`)
- **Purpose**: Creates multiple parallel execution paths
- **Configuration**: List of branch activities and join point
- **Business Use**: Concurrent approvals, parallel processing

#### 7. Parallel Gateway Join (`pwait`)
- **Purpose**: Synchronizes parallel paths
- **Configuration**: Next activity after synchronization
- **Business Use**: Wait for all parallel paths to complete

#### 8. Timer Event (`wtime`)
- **Purpose**: Time-based delays
- **Configuration**: Delay in days/hours/minutes/seconds
- **Business Use**: Reminder delays, SLA timers, cooling periods

#### 9. Message Event (`wevent`)
- **Purpose**: Wait for external messages/events
- **Configuration**: Event name and correlation key
- **Business Use**: External system integration, customer responses

#### 10. Conditional Event (`wcond`)
- **Purpose**: Wait for specific conditions to be met
- **Configuration**: Similar to exclusive gateway
- **Business Use**: Status monitoring, threshold watching

### Assignment Mechanisms

The model provides flexible task assignment through the `assignee_type` field:

#### Static Assignment (`static`)
- Direct assignment to a specific user
- Field: `assignee_id` (Many2one to res.users)

#### Dynamic Resolution (`resolver`)
- Python function determines assignee at runtime
- Field: `assignee_resolver` (dotted path to function)
- Security: Must be registered in [`BpmRegistry`](odoo/custom_addons/sedco_bpm_engine/models/registry.py)

#### Group Assignment (`group`)
- Assignment to user group with load balancing
- Field: `assignee_group_id` (Many2one to res.groups)

#### Role Assignment (`role`)
- Assignment to organizational BPM role
- Field: `assignee_role_id` (Many2one to [`bmp.role`](odoo/custom_addons/sedco_bpm_engine/models/bpm_role.py))

### Security and Validation

#### Whitelist Registry Integration
The model integrates with the [`BmpRegistry`](odoo/custom_addons/sedco_bpm_engine/models/registry.py) for security:

```python
@api.constrains('assignee_resolver')
def _check_assignee_resolver(self):
    # Validates that resolver functions are whitelisted
    
@api.constrains('service_action') 
def _check_service_action(self):
    # Validates that service actions are whitelisted
```

#### Node ID Uniqueness
```python
@api.constrains('node_id', 'definition_id')
def _check_unique_node_id(self):
    # Ensures node_id is unique within each process definition
```

### Key Methods

#### `get_assignee_user_id(context=None)`
Resolves the actual user ID for task assignment based on the configured assignment type:

```python
def get_assignee_user_id(self, context=None):
    """
    Resolve the assignee user ID based on the assignee type and configuration
    """
```

#### `to_json_node()`
Converts the activity to JSON format for the BPM engine execution:

```python
def to_json_node(self):
    """
    Convert this activity to JSON node format for the engine
    """
```

This method creates a standardized JSON representation that the BPM engine uses during process execution.

## Integration Points

### BPMN Editor Integration
- Activities are synchronized with the visual BPMN editor through [`BPMNEditorController`](odoo/custom_addons/sedco_bpm_engine/controllers/bpmn_editor.py)
- Changes in the visual editor update activity records
- Activity records can generate BPMN XML

### Process Execution
- Activities are instantiated as [`BpmActivityInstance`](odoo/custom_addons/sedco_bpm_engine/models/activity_instance.py) records during process execution
- The BPM engine uses the JSON representation for runtime decisions

### User Interface
- Activities are managed through dedicated views in [`process_definition_activity_views.xml`](odoo/custom_addons/sedco_bpm_engine/views/process_definition_activity_views.xml)
- Form views provide type-specific configuration pages
- List views show activity overview with drag-and-drop sequencing

## Usage Examples

### Creating a Simple Approval Flow

```python
# Start Event
start_activity = env['process.definition.activity'].create({
    'definition_id': process_def.id,
    'node_id': 'StartEvent_1',
    'name': 'Start Process',
    'type': 'start',
    'sequence': 10
})

# User Task for Manager Approval  
approval_task = env['bmp.process.definition.activity'].create({
    'definition_id': process_def.id,
    'node_id': 'Task_Approval',
    'name': 'Manager Approval Required',
    'type': 'task',
    'assignee_type': 'role',
    'assignee_role_id': manager_role.id,
    'sequence': 20
})

# End Event
end_activity = env['process.definition.activity'].create({
    'definition_id': process_def.id,
    'node_id': 'EndEvent_1', 
    'name': 'Process Complete',
    'type': 'end',
    'sequence': 30
})

# Link the flow
start_activity.next_activity_id = approval_task.id
approval_task.next_activity_id = end_activity.id
```

### Configuring a Parallel Gateway

```python
# Parallel split
split_gateway = env['process.definition.activity'].create({
    'definition_id': process_def.id,
    'node_id': 'ParallelGateway_Split',
    'name': 'Parallel Approval Split',
    'type': 'pbranch',
    'branch_activity_ids': [(6, 0, [finance_task.id, legal_task.id])],
    'join_activity_id': join_gateway.id
})
```

## File Structure

The activity model is supported by several related files:

- **Model**: [`process_definition_activity.py`](odoo/custom_addons/sedco_bpm_engine/models/process_definition_activity.py)
- **Views**: [`process_definition_activity_views.xml`](odoo/custom_addons/sedco_bpm_engine/views/process_definition_activity_views.xml)  
- **Security**: [`ir.model.access.csv`](odoo/custom_addons/sedco_bpm_engine/security/ir.model.access.csv)
- **Menu**: [`menu.xml`](odoo/custom_addons/sedco_bpm_engine/views/menu.xml)

## Related Models

- **[`process.definition`](odoo/custom_addons/sedco_bpm_engine/models/process_definition.py)**: Parent process definition
- **[`activity.instance`](odoo/custom_addons/sedco_bpm_engine/models/activity_instance.py)**: Runtime activity instances
- **[`role`](odoo/custom_addons/sedco_bpm_engine/models/bmp_role.py)**: Organizational role assignments
- **[`registry`](odoo/custom_addons/sedco_bpm_engine/models/registry.py)**: Security whitelist for functions

## Best Practices

### Business Process Design
1. **Use meaningful node IDs** that reflect the business purpose
2. **Keep activity names clear and descriptive** for business users
3. **Leverage BPM roles** instead of hard-coding user assignments
4. **Design for exception handling** with proper approval/rejection paths
5. **Consider parallel processing** for independent approval steps

### Technical Implementation
1. **Register all custom functions** in the BPM Registry for security
2. **Use proper sequencing** for logical activity ordering
3. **Validate flow connections** before activating processes  
4. **Test assignment resolution** with different user contexts
5. **Monitor activity performance** through instance tracking

This model serves as the foundation for creating sophisticated, maintainable business process workflows that can adapt to changing organizational structures while maintaining security and auditability.