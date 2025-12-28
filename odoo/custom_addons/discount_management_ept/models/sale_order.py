# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    employee_id = fields.Many2one('hr.employee', related="user_id.employee_id", string='Employee')
    discount_total_percent = fields.Float(string='Total Discount (%)', compute='_compute_discount_totals', store=False)
    discount_requires_approval = fields.Boolean(string='Requires Approval', compute='_compute_discount_requirement',
                                                store=False)

    @api.onchange('user_id')
    def _onchange_user_assign_employee(self):
        for order in self:
            if order.user_id:
                employee = self.env['hr.employee'].search([('user_id', '=', order.user_id.id)], limit=1)
                order.employee_id = employee.id
            else:
                order.employee_id = False

    def _get_allocation_for_line(self, line):
        """Get discount allocation for a specific order line"""
        self.ensure_one()

        if not (self.employee_id and self.employee_id.job_id):
            return None

        category = line.product_id.categ_id
        if not category:
            return None

        allocation = self.employee_id.job_id.allocation_ids.filtered(
            lambda a: a.category_id == category
        )
        return allocation[0] if allocation else None

    @api.depends('order_line.price_unit', 'order_line.discount', 'order_line.product_id', 'order_line.product_uom_qty')
    def _compute_discount_totals(self):
        for order in self:
            total_before_discount = 0
            total_discount_amount = 0

            for line in order.order_line.filtered(lambda l: not l.display_type and not l.is_delivery):
                is_global_discount = (
                        line.price_unit < 0
                        or (line.product_id and line.product_id == self.company_id.sale_discount_product_id)
                )
                if is_global_discount:
                    total_discount_amount += abs(line.price_total)
                    continue
                line_total = line.price_unit * line.product_uom_qty
                discount_amount = line_total * (line.discount / 100)

                total_before_discount += line_total
                total_discount_amount += discount_amount
            if total_before_discount > 0:
                order.discount_total_percent = (total_discount_amount / total_before_discount) * 100
            else:
                order.discount_total_percent = 0.0

    def _get_line_discount_limit(self, line):
        """Get maximum allowed discount percentage for a line"""
        allocation = self._get_allocation_for_line(line)
        if not allocation:
            return 0.0

        return allocation.get_max_discount_for_product_type(line.product_id.type)

    def _check_discount_violations(self):
        """Check for discount limit violations and return details"""
        violations = []

        if not (self.employee_id and
                self.employee_id.job_id and
                self.employee_id.job_id.use_discount):
            return violations

        job = self.employee_id.job_id

        # Check total discount
        if self.discount_total_percent > job.max_total_discount_percent:
            violations.append({
                'type': 'total',
                'current': self.discount_total_percent,
                'allowed': job.max_total_discount_percent
            })

        # Check line-level discounts
        order_line = self.order_line.filtered(lambda l: not l.display_type and not l.is_delivery)
        line_disc_prod = self.company_id.sale_discount_product_id
        if line_disc_prod:
            order_line = order_line.filtered(lambda l: l.product_id != line_disc_prod)
        for line in order_line:
            line_limit = self._get_line_discount_limit(line)
            if line_limit and line.discount > line_limit:
                violations.append({
                    'type': 'line',
                    'product': line.product_id.name,
                    'current': line.discount,
                    'allowed': line_limit
                })

        return violations

    def _compute_discount_requirement(self, check_mismatch=False):
        """Compute whether discount approval is required"""
        for order in self:
            violations = order._check_discount_violations()
            order.discount_requires_approval = bool(violations)

    def _get_approval_managers(self, employee):
        managers = []
        current = employee
        visited = set()
        while current and current.parent_id and current.id not in visited:
            visited.add(current.id)
            managers.append(current.parent_id)
            current = current.parent_id
        return managers

    def _ensure_approval_request(self, description):
        """Create approval request for discount violations with parent-child chain"""
        ApprovalRequest = self.env['approval.request']
        ApprovalCategory = self.env['approval.category']

        # Get or create approval category
        category = self.env['approval.category'].search(
            [('approval_type', '=', 'discount_request'), ('company_id', '=', self.env.company.id)], limit=1)
        # if not category:
        #     category = ApprovalCategory.create({
        #         'name': 'Sales Discount Approval',
        #         'approver_ids': [],
        #         'approval_type': 'discount_request',
        #         'company_id': self.env.company.id,
        #     })

        # Check for existing request (only check for the top-level request or any request linked to this SO)
        # Actually, we should probably check if there are any pending requests.
        existing_request = ApprovalRequest.search([
            ('request_owner_id', '=', self.user_id.id),
            ('reference', '=', f'sale.order,{self.id}'),
            ('request_status', 'in', ['pending', 'new'])
        ], limit=1)

        if existing_request:
            return existing_request

        # Determine required discount level
        violations = self._check_discount_violations()
        if not violations:
            return False

        max_violation = 0.0
        for v in violations:
            if v['current'] > max_violation:
                max_violation = v['current']

        # Get approvers from job position
        job = self.employee_id.job_id
        if not job or not job.discount_approver_ids:
            raise UserError(_("No discount approvers configured for job position %s") % job.name)

        # Sort approvers by max_discount ASC
        approvers = job.discount_approver_ids.sorted(key=lambda r: r.max_discount)

        # Build the chain
        chain = []
        covered = False
        for approver in approvers:
            chain.append(approver)
            if approver.max_discount >= max_violation:
                covered = True
                break

        if not covered:
            pass

        if not chain:
            raise UserError(_("Could not determine approval chain."))
        chain.reverse()

        parent_request = False
        top_request = False

        for approver in chain:
            request_vals = {
                'name': _('Discount Approval for %s (Approver: %s)') % (self.name or _('New'), approver.user_id.name),
                'request_owner_id': self.user_id.id,
                'category_id': category.id,
                'partner_id': self.partner_id.id,
                'request_status': 'pending',
                'reference': f'sale.order,{self.id}',
                'amount': self.amount_total,
                'approver_ids': [(0, 0, {
                    'user_id': approver.user_id.id,
                    'required': 'required',
                })],
                'date': fields.Date.today(),
                'reason': description,
                'sale_order_id': self.id,
                'is_disc_req': True,
            }

            if parent_request:
                request_vals['parent_request_id'] = parent_request.id

            request = ApprovalRequest.create(request_vals)
            request.sudo().action_confirm()

            if not top_request:
                top_request = request

            parent_request = request

        # Post message
        self.message_post(
            body=_(
                "Order exceeded the maximum discount allowed. "
                "Approval request chain created starting with %s."
            ) % top_request.name,
            subtype_xmlid="mail.mt_note",
        )

        return top_request

    def _get_violation_description(self):
        """Get formatted description of discount violations"""
        violations = self._check_discount_violations()
        if not violations:
            return ""

        lines = []
        for violation in violations:
            if violation['type'] == 'total':
                lines.append(
                    f"Total discount {violation['current']}% exceeds "
                    f"allowed {violation['allowed']}%"
                )
            elif violation['type'] == 'line':
                lines.append(
                    f"Product {violation['product']}: discount "
                    f"{violation['current']}% exceeds allowed "
                    f"{violation['allowed']}%"
                )

        return "\n".join(lines)

    def action_confirm(self):
        for order in self:
            category = self.env['approval.category'].search(
                [('approval_type', '=', 'discount_request'), ('company_id', '=', self.env.company.id)], limit=1)
            if category and category.create_approval_request and (order.discount_requires_approval and
                not order.env.context.get("from_disc_approval")) and not order.env.context.get("from_approval"):
                description = order._get_violation_description()
                order.write({'state': 'on_hold'})
                return order._ensure_approval_request(description)
        return super(SaleOrder, self).action_confirm()
