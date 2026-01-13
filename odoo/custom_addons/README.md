# Odoo Custom Addons (EPT Series)

This repository contains a suite of custom Odoo addons developed to enhance various operational aspects including Sales, Manufacturing, Accounting, and Approvals. Below is a summary of each module.

## 1. Account Extended EPT (`account_extended_ept`)
**Purpose:** Customizes accounting documents and company settings.
**Key Features:**
- Adds Arabic address fields to the Company model.
- Adds a scalable header image for invoices.
- overrides the default invoice print action to use a specific custom report template (SEDCO format).

## 2. CRM Extended EPT (`crm_extended_ept`)
**Purpose:** Extends product master data for better classification.
**Key Features:**
- **New Fields:** Adds `Model Number`, `Product Line`, and `Product Nature` to Product Templates and Variants.
- **Synchronization:** Ensures data consistency between Product Templates and their Variants.

## 3. Discount Management EPT (`discount_management_ept`)
**Purpose:** Implements a hierarchical approval system for sales discounts based on Job Positions.
**Key Features:**
- **Job-Based Limits:** Defines maximum allowed discount percentages per Job Position.
- **Approval Chains:** Automatically creates a chain of approval requests (Supervisor -> Manager, etc.) if a salesperson exceeds their limit.
- **Validation:** Checks both total order discount and individual line item discounts.

## 4. MRP Extended EPT (`mrp_extended_ept`)
**Purpose:** Enhances manufacturing control, specifically for scrapping and time tracking.
**Key Features:**
- **Scrap Tolerance:** Prevents scrapping more material than produced (plus a tolerance %) without specific confirmation/wizard.
- **Work Order Costing:** Calculates average labor cost per piece.
- **Time Tracking Approval:** Requires specific approvals for modifying work center productivity durations (supervisor validation).
- **Component Availability Report:** Generates an Excel report for BOM component availability.

## 5. Pilot Order EPT (`pilot_order_ept`)
**Purpose:** Manages "Pilot Orders" (trial/pre-production orders) and strict change control.
**Key Features:**
- **Pilot Workflow:** Flag orders as "Pilot Orders" which require specific approval before confirmation.
- **Change Control:** Intercepts changes to **Taxes** or **Freight/Delivery** on existing orders.
- **Approval Trigger:** Reverts unauthorized changes to these critical fields and creates an approval request detailing the "Old Value" vs "New Value".

## 6. Sale Below Cost Approval EPT (`sale_below_cost_approval_ept`)
**Purpose:** prevents margin leakage by catching sales below cost.
**Key Features:**
- **Below Cost Check:** analyzes order lines during confirmation.
- **Approval Wizard:** If any item is being sold below cost, it blocks confirmation and opens a wizard to request special approval.

## 7. Sale Extended EPT (`sale_extended_ept`)
**Purpose:** Enforces financial security checks during sales.
**Key Features:**
- **Credit Limit:** Checks if the customer has exceeded their credit limit.
- **Overdue Invoices:** Checks if the customer has unpaid overdue invoices.
- **On Hold Status:** Automatically places orders "On Hold" and generates an approval request if checks fail.

## 8. Customer Management EPT (`customer_management_ept`)
**Purpose:** Enhances customer relationship and sales scheduling.
**Key Features:**
- **Schedules:** Manages recognition, invoicing, and distribution schedules linked to Sales Orders.
- (Further details to be documented upon deeper inspection).

## 9. Stock Extended EPT (`stock_extended_ept`)
**Purpose:** Extends inventory management capabilities.
**Key Features:**
- Likely includes enhancements to Stock Pickings, Quants, and Lot management based on file structure.
- (Further details to be documented upon deeper inspection).

## 10. Vendor Tracking EPT (`vendor_tracking_ept`)
**Purpose:** Extends vendor and purchase management.
**Key Features:**
- (Further details to be documented upon deeper inspection).

---

## Technical Note
All modules starting with `*_ept` follow a consistent pattern of using Odoo's `approval.request` mechanism to handle exceptions (Credit Limits, Discounts, Pilot Orders, etc.), ensuring a unified approval experience for the user.
