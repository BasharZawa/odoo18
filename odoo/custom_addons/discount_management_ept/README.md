# Discount Management EPT

Role-based discount limits, approval workflow with manager escalation, and sales order blocking until approval.

## Installation

- Add this module to your addons path.
- Update Apps list and install `Discount Management EPT`.

## Configuration

- In `Product Categories`, set `Discount Category` and thresholds (HW 20, SW 25, Service 20 by default).
- In `Job Positions`, set max discounts per category and total as per your policy (e.g., BDM 40/20/20/20, etc.).

## Usage

- Create a Sales Order; `Employee` auto-fills from the `Salesperson`'s employee.
- If line or total discount exceeds role/category thresholds, the order requires approval.
- An approval request is created under Approvals with manager chain approvers.
- A To-Do activity is scheduled to the first manager.
- Confirmation is blocked until approval; once approved, confirm as usual. Odoo will lock the order after confirmation
  per standard behavior.
