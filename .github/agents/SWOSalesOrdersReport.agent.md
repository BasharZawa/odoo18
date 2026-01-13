Sales Analysis & Sales Recognition Reporting

Objective
To design and implement two Excel-based analytical reports in Odoo—Sales Analysis: Budget vs Actual and Sales Recognition Report—to support management in tracking sales performance, budget adherence, and revenue recognition. Both reports will be accessible from the Sales Module and downloadable in Excel format based on user-selected parameters.

Common Scope & Access
Both reports will be:
Accessible from Sales → Reports
Generated based on user-selected year
Downloaded as formatted Excel files
Reports will rely on confirmed Sales Orders only
All values will be calculated including taxes

Part A: Sales Analysis – Budget vs Actual Report
Purpose
To compare Budgeted vs Actual Sales performance across Salespersons, Countries/Regions, and Product Lines, enabling variance analysis and year-over-year comparison.

1. Budget Entry Configuration
Budget data will be maintained via:
A dedicated budget entry workspace in Odoo
OR
An Excel import template
Budget Dimensions
Each budget entry will be defined by:
Year
Salesperson
Country
Product Line
(Legacy Products, CVM, Self Service, Media Analytics, Services)
Controls
Each entry represents the total annual budget value
System validation will ensure one unique record per combination of:
Year + Salesperson + Country + Product Line

2. Data Sources
Actual Sales: Confirmed Sales Orders (including taxes)
Budget Values: Budget workspace or imported Excel
Previous Year Actual: Auto-fetched from last year’s confirmed Sales Orders
Intercompany Sales:
Excluded from country totals
Displayed in a separate dedicated row

3. Report Layout : link
Columns
Actual (Selected Year)
Budget (Selected Year)
Variance (Actual – Budget)
Amount
Percentage
Previous Year Actual
Variance (Current Year – Previous Year)
Amount
Percentage
Each metric will be further split by Product Line.
YTD (Year-to-Date)
YTD totals will be shown under:
Actual
Budget
Previous Year
YTD will aggregate values across all product lines
YTD calculation formula is pending client confirmation

4. Report Structures
A. Country / Region-wise Report
Rows:
Regions (e.g., Gulf, Saudi, Levant)
Countries under each region
Separate Intercompany Sales row
B. Salesperson-wise Report
Rows:
Salesperson names
Separate Intercompany Sales row

5. Deliverables (Sales Analysis)
Excel Report: Sales Analysis – Budget vs Actual (by Country/Region)
Excel Report: Sales Analysis – Budget vs Actual (by Salesperson)
Budget Entry Workspace / Import Template
Excel output with formulas for variance and percentages

Report B: Sales Recognition Report
Purpose
To provide visibility into monthly revenue recognition for the selected year and carry-forward (C/F) recognition for future years, based on the Recognition Schedule maintained in Sales Orders.

1. Data Sources
The report will pull data from:
Sales Orders (Confirmed)
Customer Master (Sector / Industry)
Product Master (Product Line / Class)
Recognition Schedule tab in Sales Orders
2. Data Source
The report will draw data from:
Sales Orders (Confirmed Orders)
Customer Form (for Sector)
Product Form (for Product Class / Product Line)
Recognition Schedule Tab in Sales Orders (for monthly and carry-forward revenue recognition)

3. Report Layout

Columns
Column Name
Description
Order No
Sales Order Number
Customer Name
Customer linked to the sales order
Payment Status
Status of related customer payment(s)
End User
End user specified in the Sales Order
Sector
Industry field from Customer Master
Salesperson
Responsible Salesperson for the order
Country
Customer’s Country
Class of Product
Product Line(s) linked to the products in the sales order (can be one or multiple)
Order Date
Date of the Sales Order
Total
Total Sales Order value (including taxes)
Month Columns (e.g., Jan–Dec 2025)
Amounts from the recognition schedule corresponding to each month of the selected year
C/F 2026, C/F 2027, C/F 2028
Future year recognition values from the schedule based on date and amount entered by the user


4. Data Logic
Sector → Pulled from Industry field in the Customer Master (res.partner).
Class of Product → Derived from Product Line in the Product Master (product.template).
Monthly Columns (Jan–Dec) → Populated using recognition dates and amounts from the Recognition Schedule tab in each Sales Order.
C/F Columns (2026, 2027, 2028) → Populated from the same schedule for recognition dates falling in future years.
Total → Represents total Sales Order value (sum of all recognition amounts).


4. Report Access & Format
Available under Sales → Reports → Sales Recognition Report
User selects report year
System generates a structured Excel file with:
Monthly recognition
Carry-forward values
Proper headers and formatting

5. Deliverables (Sales Recognition)
Sales Recognition Report (Excel download)
Report generation action under Sales Module
Recognition Schedule dependency review / enhancement (if required)

Pending Client Input
Confirmation of YTD calculation formula for the Sales Analysis – Budget vs Actual report

