# Customer Management EPT

This module provides comprehensive customer contact validation workflow with Finance team approval and advanced sales
order scheduling capabilities for Odoo 18.0.

## Features

### Customer Contact & Validation

- **Unique Customer ID**: Auto-generated unique Customer ID for contacts with type "Customer" or "Both"
- **Validation Workflow**: Finance team approval process for customer contacts
- **Field-level Access Control**: Different access rights based on validation status
- **Sales Order Blocking**: Prevents confirmation of sales orders for unvalidated customers
- **Automatic Notifications**: Finance team receives notifications for validation requests

### Sales Order Scheduling

- **End Customer Tracking**: Track end customers for license management and service tracking
- **Invoicing Schedule**: Milestone-based and periodic billing with due date tracking
- **Recognition Schedule**: Revenue recognition tracking for long-term contracts
- **Distribution Schedule**: Salesperson commission allocation with percentage tracking
- **Approval Workflow**: Sales order approval process with status tracking

### Reporting

- **Invoicing Schedule Reports**: Track invoice due dates and amounts (Tree view + XLSX export)
- **Recognition Schedule Reports**: Monitor revenue recognition milestones (Tree view + XLSX export)
- **Distribution Schedule Reports**: Salesperson-wise commission reports (Tree view + XLSX export)
- **XLSX Export**: Professional Excel reports with formatting, totals, and timestamps

## Installation

1. Copy the module to your Odoo addons directory
2. Update the app list in Odoo
3. Install the "Customer Management EPT" module

## Configuration

### User Groups

- **Finance Team**: Can validate customer contacts and manage validated customer data
- **Sales Team**: Can create and manage sales orders and schedules
- **Sales Manager**: Can approve sales orders and manage all sales operations

### Sequence Configuration

The module automatically creates a sequence for Customer ID generation with prefix "CUST" and 5-digit padding.

## Usage

### Customer Validation

1. Create a new contact with type "Customer" or "Both"
2. Customer ID is automatically generated
3. Contact remains unvalidated until Finance team approval
4. Sales orders for unvalidated customers are blocked from confirmation
5. Finance team can validate/invalidate contacts as needed

### Sales Order Scheduling

1. Create a sales order with customer and end customer details
2. Use the schedule tabs to add:
    - **Invoicing Schedule**: Set invoice dates, amounts, and milestones
    - **Recognition Schedule**: Define revenue recognition dates and amounts
    - **Distribution Schedule**: Allocate commission percentages to salespersons
3. Submit for approval if required
4. Use reports to track schedule progress

### Reports

Access schedule reports from the "Customer Management" menu:

- **Invoicing Schedule Report**: View and export invoicing schedules
- **Invoicing Schedule (XLSX)**: Export to Excel format
- **Recognition Schedule Report**: View and export recognition schedules
- **Recognition Schedule (XLSX)**: Export to Excel format
- **Distribution Schedule Report**: View and export distribution schedules
- **Distribution Schedule (XLSX)**: Export to Excel format

Each report includes:

- Professional formatting with headers and totals
- Timestamped filenames for easy organization
- Currency formatting for monetary values
- Date formatting for better readability
- Export buttons directly in tree views

## Technical Details

### Models

- `res.partner`: Extended with customer validation fields
- `sale.order`: Extended with scheduling and approval fields
- `sale.order.invoicing.schedule`: Invoicing milestone tracking
- `sale.order.recognition.schedule`: Revenue recognition tracking
- `sale.order.distribution.schedule`: Commission distribution tracking

### Key Fields Added

#### Customer (res.partner)

- `customer_id`: Unique customer identifier (read-only)
- `validation_status`: Validation status (not_validated/validated)
- `validation_date`: When customer was validated
- `validated_by`: Who validated the customer
- `validation_notes`: Notes from Finance team

#### Sales Order (sale.order)

- `end_customer_id`: End customer for license management
- `special_pricing_flag`: Indicates special pricing usage
- `approval_status`: Order approval workflow status
- `invoicing_schedule_ids`: One2many to invoicing schedule
- `recognition_schedule_ids`: One2many to recognition schedule
- `distribution_schedule_ids`: One2many to distribution schedule

#### Invoicing Schedule

- `invoice_date`: When invoice should be generated
- `due_date`: Payment due date
- `invoice_amount`: Amount to be billed
- `billing_milestone_description`: Milestone description
- `invoiced_status`: Invoiced/Not Invoiced status
- `reference_document`: Invoice reference

#### Recognition Schedule

- `recognition_date`: Revenue recognition date
- `description`: Recognition event description
- `amount`: Amount to be recognized

#### Distribution Schedule

- `salesperson_id`: Salesperson involved
- `commission_percentage`: Commission percentage
- `commission_amount`: Calculated commission amount

### Security Groups

- `group_finance_team`: Can validate customers and edit validated customer data
- `group_sales_team`: Can create and manage sales orders and schedules
- `group_sales_manager`: Can approve sales orders and manage operations

### Dependencies

- `vendor_tracking_ept`
- `sale_extended_ept`
- `report_xlsx` (for XLSX export functionality)

## Workflow

### Customer Validation Process

1. **Create Customer**: Any user can create customer contacts
2. **Auto ID Generation**: Customer ID is automatically generated
3. **Edit Freely**: Unvalidated customers can be edited by anyone
4. **Sales Order Created**: System notifies Finance team automatically
5. **Finance Validation**: Finance team validates the customer
6. **Order Confirmation**: Sales orders can now be confirmed

### Sales Order Approval Process

1. **Create Order**: Sales team creates order with schedules
2. **Submit for Approval**: Order is submitted for manager approval
3. **Manager Review**: Sales manager reviews and approves/rejects
4. **Order Processing**: Approved orders can proceed to confirmation

## Constraints & Validations

### Commission Distribution

- Total commission percentage cannot exceed 100%
- Each salesperson can only be assigned once per order

### Schedule Amounts

- Total invoicing amount cannot exceed order total
- Total recognition amount cannot exceed order total

### Customer Validation

- Customer ID is immutable once assigned
- Validated customers have restricted field editing for non-finance users

## Troubleshooting

### Common Issues

1. **Customer ID not generated**: Check if sequence exists and is properly configured
2. **Cannot validate customer**: Ensure user is in Finance Team group
3. **Sales order not blocking**: Check if customer validation workflow is properly installed
4. **Schedule totals exceed order**: Review schedule amounts and percentages

### Permissions

- Ensure Finance team users have proper access rights
- Check that mail templates are properly configured
- Verify sequence permissions
- Confirm user group assignments

## Support

For support and customization requests, contact Emipro Technologies Pvt Ltd.