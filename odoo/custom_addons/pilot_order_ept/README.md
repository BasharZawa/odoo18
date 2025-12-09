# Pilot Order Management Module for Odoo 18.0

## Overview

The Pilot Order Management module provides comprehensive functionality for managing pilot orders in Odoo 18.0. Pilot
orders are trial deliveries sent to customers without immediate invoicing, requiring Sales Manager approval before
confirmation and customer approval before conversion to regular sales orders.

## Key Features

### 🚁 Pilot Order Management

- Create and manage pilot orders as trial deliveries
- Separate pilot orders from normal sales orders
- Track customer approval status
- Support for different pilot types (Trial, Sample, Test)

### ✅ Approval Workflows

- Configurable approval workflows based on tags
- Sales Manager approval requirement
- Email notifications for approval requests
- Approval tracking and history

### 🔄 Order Conversion

- Convert approved pilot orders to sales orders
- Apply standard pricing during conversion
- Automatic invoice creation option
- Maintain audit trail between orders

### 🏷️ Tag-Based Configuration

- Configurable tags for approval triggers
- Flexible workflow assignment
- Visual tagging system
- Custom approval rules per tag

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Pilot Order Management" module
4. Configure approval workflows and tags as needed
5. Assign appropriate user groups to your team members

## Configuration

### User Groups

- **Pilot Order User**: Can create and manage pilot orders
- **Pilot Order Manager**: Can approve pilot orders and manage all operations
- **Pilot Order Approver**: Can approve pilot order requests

### Approval Workflows

Configure approval workflows based on tags:

- Trial Delivery Approval
- High Value Approval
- New Customer Approval
- Urgent Approval (with auto-approve option)

### Tags

Default tags included:

- Trial Delivery (requires approval)
- High Value (requires approval)
- New Customer (requires approval)
- Sample Order (no approval required)
- Urgent (requires approval, auto-approve enabled)

## Usage

### Creating a Pilot Order

1. Navigate to Pilot Orders → Pilot Orders
2. Click "Create" to create a new pilot order
3. Fill in customer details, pilot type, and order lines
4. Add relevant tags if needed
5. Save the order

### Approval Process

1. Send quotation to customer
2. If approval is required (based on tags or pilot type), request approval
3. Sales Manager receives email notification
4. Sales Manager approves or rejects the request
5. Customer approves the pilot order
6. Convert to sales order when ready

### Converting to Sales Order

1. Ensure customer approval is received
2. Click "Convert to Sales Order"
3. Configure conversion options (pricing, invoicing, etc.)
4. Confirm conversion
5. New sales order is created with proper audit trail

## Technical Details

### Models

- `pilot.order`: Main pilot order model
- `pilot.order.line`: Pilot order line items
- `pilot.order.approval`: Approval request model
- `pilot.order.tag`: Tags for workflow configuration
- `pilot.order.approval.workflow`: Approval workflow configuration

### Dependencies

- base
- sale
- sale_management
- stock
- account
- mail
- portal

### Security

- Role-based access control
- Record-level security rules
- Approval authorization controls

## Customization

### Adding New Tags

1. Navigate to Pilot Orders → Configuration → Tags
2. Create new tags with appropriate approval requirements
3. Configure workflows to use the new tags

### Customizing Workflows

1. Navigate to Pilot Orders → Configuration → Approval Workflows
2. Create or modify workflows
3. Assign approvers and groups
4. Configure auto-approve options

### Email Templates

Email templates can be customized in Settings → Technical → Email → Templates:

- Pilot Order Quotation Template
- Approval Request Template

## Support

For support and customization requests, please contact your Odoo implementation partner.

## License

This module is licensed under LGPL-3.

## Version

Current Version: 18.0.1.0.0
