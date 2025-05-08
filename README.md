# Odoo

[![Build Status](https://runbot.odoo.com/runbot/badge/flat/1/master.svg)](https://runbot.odoo.com/runbot)
[![Tech Doc](https://img.shields.io/badge/master-docs-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/documentation/master)
[![Help](https://img.shields.io/badge/master-help-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](https://img.shields.io/badge/master-nightly-875A7B.svg?style=flat&colorA=8F8F8F)](https://nightly.odoo.com/)

Odoo is a suite of web based open source business apps.

The main Odoo Apps include an [Open Source CRM](https://www.odoo.com/page/crm),
[Website Builder](https://www.odoo.com/app/website),
[eCommerce](https://www.odoo.com/app/ecommerce),
[Warehouse Management](https://www.odoo.com/app/inventory),
[Project Management](https://www.odoo.com/app/project),
[Billing &amp; Accounting](https://www.odoo.com/app/accounting),
[Point of Sale](https://www.odoo.com/app/point-of-sale-shop),
[Human Resources](https://www.odoo.com/app/employees),
[Marketing](https://www.odoo.com/app/social-marketing),
[Manufacturing](https://www.odoo.com/app/manufacturing),
[...](https://www.odoo.com/)

Odoo Apps can be used as stand-alone applications, but they also integrate seamlessly so you get
a full-featured [Open Source ERP](https://www.odoo.com) when you install several Apps.

## Getting started with Odoo

For a standard installation please follow the [Setup instructions](https://www.odoo.com/documentation/master/administration/install/install.html)
from the documentation.

To learn the software, we recommend the [Odoo eLearning](https://www.odoo.com/slides),
or [Scale-up, the business game](https://www.odoo.com/page/scale-up-business-game).
Developers can start with [the developer tutorials](https://www.odoo.com/documentation/master/developer/howtos.html).

## Security

If you believe you have found a security issue, check our [Responsible Disclosure page](https://www.odoo.com/security-report)
for details and get in touch with us via email.

# Request Engine Documentation

## Overview
The Request Engine is a custom module built within the Odoo framework to manage various types of requests and their associated workflows. It is designed to be extensible, allowing for the addition of new request types and workflows as needed.

## Features
- **Parent Module (`x.request`)**: Manages all types of requests and serves as the central hub for the engine.
- **Child Modules**: Includes specific request types like `PresalesRequest`.
- **Task Management**: Automatically creates and manages tasks associated with requests.
- **Extensibility**: Easily add new request types and workflows.

## Components

### 1. Models
#### `x.request`
- **Purpose**: The parent model for managing requests.
- **Fields**:
  - `name`: The name of the request.
  - `description`: A description of the request.
  - `request_type`: The type of request (e.g., `presales`, `bpm_ticket`).
  - `task_id`: A Many2one field linking to the related task.
  - `task_ids`: A One2many field for managing multiple tasks.
  - `state`: The current state of the request (`draft`, `in_progress`, `done`).

#### `task`
- **Purpose**: Represents tasks associated with requests.
- **Fields**:
  - `name`: The name of the task.
  - `state`: The current state of the task (`pending`, `in_progress`, `done`).
  - `parent_task_id`: Links to a parent task (for hierarchical tasks).
  - `child_task_ids`: Links to child tasks.
  - `condition`: A condition for creating the task.

#### `presales.request`
- **Purpose**: A child model extending `x.request` for presales-specific requests.
- **Fields**:
  - `customer_name`: The name of the customer.
  - `customer_email`: The email of the customer.
  - `customer_phone`: The phone number of the customer.
  - `project_scope`: The scope of the project.
  - `budget`: The estimated budget for the project.
  - `deadline`: The deadline for the request.
  - `priority`: The priority of the request (`low`, `medium`, `high`).
  - `status`: The status of the request (`new`, `in_progress`, `completed`).

### 2. Views
- **Form Views**: Allow users to create and edit requests and tasks.
- **List Views**: Display requests and tasks in a tabular format.
- **Menu Items**:
  - `Requests`: The main menu for managing all requests.
  - `Tasks`: A submenu for managing tasks.
  - `Presales Requests`: A submenu for managing presales-specific requests.

### 3. Workflows
- **Request Workflow**:
  1. A user creates a request.
  2. The system automatically creates associated tasks.
  3. Tasks are completed, and the request progresses through states (`draft` → `in_progress` → `done`).

- **Task Workflow**:
  1. Tasks are created automatically or manually.
  2. Tasks can have parent-child relationships for hierarchical workflows.
  3. Tasks progress through states (`pending` → `in_progress` → `done`).

### 4. Security
- Access control rules are defined in `ir.model.access.csv` to ensure proper permissions for managing requests and tasks.

## Extensibility
- **Adding New Request Types**:
  1. Create a new model extending `x.request`.
  2. Add fields specific to the new request type.
  3. Define views and menu items for the new request type.

- **Custom Workflows**:
  - Use Odoo's automation tools (e.g., server actions, scheduled actions) to define custom workflows.

## Installation
1. Place the `request` module in the `custom_addons/` directory.
2. Restart the Odoo server.
3. Update the app list and install the `Request Management` module.

## Testing
- Create a new request and verify that tasks are created automatically.
- Test the workflows for requests and tasks.
- Verify access control rules.

## Future Enhancements
- Add Gantt chart views for visualizing task dependencies.
- Integrate with other Odoo modules (e.g., CRM, Sales) for enhanced functionality.
- Add notifications and reminders for pending tasks.

---
This documentation provides an overview of the Request Engine and its components. For further details, refer to the code and comments within the module.
