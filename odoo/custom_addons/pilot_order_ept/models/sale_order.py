from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_pilot_order = fields.Boolean(string='Pilot Order', default=False, copy=False)
    pilot_approval_required = fields.Boolean(compute='_compute_pilot_approval_required', copy=False)
    pilot_approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval State', default='draft', copy=False)
    pilot_approval_date = fields.Datetime(string='Approval Date', copy=False)
    pilot_approved_by = fields.Many2one('res.users', string='Approved By', copy=False)
    customer_confirmation = fields.Boolean(string='Customer Confirmed', default=False, copy=False)
    customer_confirmation_date = fields.Datetime(string='Customer Confirmation Date', copy=False)
    pending_modifications = fields.Json(string="Pending Modifications", readonly=True, copy=False)

    @api.depends('is_pilot_order', 'pilot_approval_state')
    def _compute_pilot_approval_required(self):
        for order in self:
            order.pilot_approval_required = (
                    order.is_pilot_order and
                    order.pilot_approval_state in ['draft', 'pending']
            )

    @api.constrains('is_pilot_order')
    def _check_pilot_order_invoicing(self):
        for order in self:
            if order.is_pilot_order and order.invoice_ids:
                raise ValidationError(_("Cannot convert to pilot order: Invoices already exist."))

    def action_confirm(self):
        """Override to enforce pilot order approval"""
        for order in self:
            approval_category = self.env['approval.category'].search([
                    ('approval_type', '=', 'pilot_order_req'), ('company_id', '=', self.env.company.id)
                    ], limit=1)
            if approval_category and approval_category.create_approval_request:
                if order.is_pilot_order and order.pilot_approval_state == 'draft' and not self.env.context.get(
                        'bypass_pilot_order_check'):
                    order.action_request_pilot_and_freight_approval()
                    return False
                if order.is_pilot_order and order.pilot_approval_state == 'pending' and not self.env.context.get(
                        'bypass_pilot_order_check'):
                    raise UserError(_("Pilot orders must be approved before confirmation."))
        return super(SaleOrder, self).action_confirm()

    def action_request_pilot_and_freight_approval(self, is_freight=False):
        """Request approval for pilot order"""
        self.ensure_one()
        manager_group = self.env.ref('sales_team.group_sale_manager')
        managers = manager_group.users
        # Prepare approvers
        approver_vals = []
        for manager in managers:
            approver_vals.append((0, 0, {
                'user_id': manager.id,
                'required': 'required',
            }))
        if not approver_vals:
            manager = self.env.ref('base.user_admin') or self.env.ref('base.user_root')
            approver_vals.append((0, 0, {
                'user_id': manager.id,
                'required': 'required',
            }))

        if is_freight:
            return self.freight_request_approval(approver_vals)
        else:
            return self.action_request_pilot_approval(approver_vals)

    def action_request_pilot_approval(self, approver_vals):
        if not self.is_pilot_order:
            raise UserError(_("This is not a pilot order."))
        # approval_category = self.env.ref('pilot_order_ept.pilot_order_approval_category')
        approval_category = self.env['approval.category'].search([
            ('approval_type', '=', 'pilot_order_req'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        # if not approval_category:
        #     approval_category = self.env['approval.category'].sudo().create({
        #         'name': 'Pilot Order Approval',
        #         'approver_ids': [],
        #         'approval_type' : 'pilot_order_req',
        #         'company_id' : self.env.company.id,
        #     })
        request_vals = {
            'name': f"Pilot Order Approval - {self.name}",
            'category_id': approval_category.id,
            'request_owner_id': self.env.user.id,
            'partner_id': self.partner_id.id,
            'sale_order_id': self.id,
            'request_status': 'new',
            'reason': "Pilot order approval request",
            'date': fields.Date.today(),
            # 'approver_ids': approver_vals,
            'is_pilot_order_req': True,
            'reference': f'sale.order.pilot,{self.id}',
        }
        approval_request = self.env['approval.request'].sudo().create(request_vals)
        approval_request.sudo().action_confirm()
        # Post message
        self.message_post(
            body=_(
                "The document has been requested for Pilot Order. "
                "Approval request %s has been created."
            ) % approval_request.name,
            subtype_xmlid="mail.mt_note",
        )
        self.pilot_approval_state = 'pending'
        self.write({'state': 'on_hold'})
        return True

    def freight_request_approval(self, approver_vals):
        """Create a formatted approval request for freight or tax adjustment"""
        self.ensure_one()
        self.discard_existing_freight_approvals()

        # approval_category = self.env.ref('pilot_order_ept.freight_approval_category')
        approval_category = self.env['approval.category'].search([
            ('approval_type', '=', 'freight_tax_req'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        # if not approval_category:
        #     approval_category = self.env['approval.category'].sudo().create({
        #         'name': 'Freight or Tax Adjustment Approval',
        #         'approver_ids': [],
        #         'approval_type': 'freight_tax_req',
        #         'company_id': self.env.company.id,
        #     })

        # Generate formatted HTML reason (includes tax names instead of IDs)
        formatted_reason = self._format_pending_modifications_html()

        request_vals = {
            'name': f"Freight or Tax Adjustment Approval - {self.name}",
            'category_id': approval_category.id,
            'request_owner_id': self.env.user.id,
            'partner_id': self.partner_id.id,
            'sale_order_id': self.id,
            'request_status': 'new',
            'reason': formatted_reason,
            'date': fields.Date.today(),
            # 'approver_ids': approver_vals,
            'is_freight_req': True,
            'reference': f'sale.order.freight,{self.id}',
        }

        approval_request = self.env['approval.request'].sudo().create(request_vals)
        approval_request.sudo().action_confirm()

        self.message_post(
            body=_(
                "The document has been requested for Freight or Tax Charges Adjustment in the Order. "
                "Approval request %s has been created."
            ) % approval_request.name,
            subtype_xmlid="mail.mt_note",
        )
        return True

    def _format_pending_modifications_html(self):
        """Format pending modifications into a clean HTML table (with tax names)."""
        if not self.pending_modifications:
            return "<p>No modifications recorded.</p>"

        html = """
        <div>
            <strong>Pending Modifications:</strong><br/><br/>
            <table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse; width:100%;">
                <thead style="background-color:#f2f2f2; text-align:left;">
                    <tr>
                        <th>Type</th>
                        <th>Product / Line</th>
                        <th>Old Value</th>
                        <th>New Value</th>
                    </tr>
                </thead>
                <tbody>
        """

        for change in self.pending_modifications:
            change_type = change.get('type', '').replace('_', ' ').title()
            line = self.env['sale.order.line'].browse(change.get('line_id', 0))
            line_name = line.display_name or f"Line ID: {change.get('line_id', '')}"

            # Initialize default values
            old_val = new_val = ''

            if change.get('type') == 'freight_change':
                old_val = f"{change.get('old_price', '')}"
                new_val = f"{change.get('new_price', '')}"

            elif change.get('type') == 'tax_changes':
                Tax = self.env['account.tax']
                new_tax_ids = [tax[1] for tax in change.get('new_tax_ids', [])]
                old_tax_names = ', '.join(Tax.browse(change.get('old_tax_ids', [])).mapped('name'))
                new_tax_names = ', '.join(Tax.browse(new_tax_ids).mapped('name'))
                old_val = old_tax_names or '-'
                new_val = new_tax_names or '-'

            else:
                old_val = str(change.get('old_value', ''))
                new_val = str(change.get('new_value', ''))

            html += f"""
                <tr>
                    <td>{change_type}</td>
                    <td>{line_name}</td>
                    <td>{old_val}</td>
                    <td>{new_val}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    def discard_existing_freight_approvals(self):
        self.ensure_one()
        existing_requests = self.env['approval.request'].search([
            ('sale_order_id', '=', self.id),
            ('is_freight_req', '=', True),
            ('request_status', 'in', ['new', 'pending'])
        ])
        for request in existing_requests:
            request.sudo().action_cancel()
            request.sudo().unlink()
        return True

    def action_customer_confirm_purchase(self):
        """Mark customer confirmation"""
        self.ensure_one()
        if not self.is_pilot_order:
            raise UserError(_("This is not a pilot order."))

        self.write({
            'customer_confirmation': True,
            'customer_confirmation_date': fields.Datetime.now(),
        })

        message = _("Customer confirmed purchase")
        self.message_post(body=message)

        return True

    def write(self, vals):
        """Override to handle pilot order restrictions"""
        if 'is_pilot_order' in vals and vals['is_pilot_order']:
            vals.update({
                'pilot_approval_state': 'draft',
                'customer_confirmation': False,
            })
        approval_category = self.env['approval.category'].search([
            ('approval_type', '=', 'freight_tax_req'), ('company_id', '=', self.env.company.id)
            ], limit=1)
        if approval_category and approval_category.create_approval_request:
            for order in self:
                proposed_changes = []
                approval_needed = False
                if 'order_line' in vals:
                    for command in vals['order_line']:

                        cmd, line_id, line_data = (
                            command[0],
                            command[1] if len(command) > 1 else False,
                            command[2] if len(command) > 2 and isinstance(command[2], dict) else {},
                        )
                        existing_line = False
                        if cmd == 1:  # Update existing
                            existing_line = order.order_line.browse(line_id)

                        elif cmd == 4:  # Link existing line
                            existing_line = order.order_line.browse(line_id)
                        if not line_data:
                            continue
                        if 'tax_id' in line_data and existing_line:
                            old_tax_ids = existing_line.tax_id.ids

                            if line_data['tax_id']:
                                approval_needed = True
                                proposed_changes.append({
                                    'type': "tax_changes",
                                    'line_id': existing_line.id,
                                    'old_tax_ids': old_tax_ids,
                                    'new_tax_ids': line_data['tax_id'],
                                })

                            # Revert change immediately
                            line_data['tax_id'] = [(6, 0, old_tax_ids)]

                        if 'price_unit' in line_data and existing_line:
                            if existing_line.is_delivery:
                                approval_needed = True
                                proposed_changes.append({
                                    'type': 'freight_change',
                                    'line_id': existing_line.id,
                                    'old_price': existing_line.price_unit,
                                    'new_price': line_data['price_unit'],
                                })
                                line_data['price_unit'] = existing_line.price_unit

                if approval_needed:
                    order.pending_modifications = proposed_changes
                    order.action_request_pilot_and_freight_approval(is_freight=True)

        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Handle pilot order creation (multi)"""
        records = super(SaleOrder, self).create(vals_list)
        for record in records:
            approval_category = self.env['approval.category'].search([
                    ('approval_type', '=', 'pilot_order_req'), ('company_id', '=', self.env.company.id)
                    ], limit=1)
            if record.is_pilot_order and approval_category and approval_category.create_approval_request:
                record.action_request_pilot_and_freight_approval()
                message = _("Pilot order created")
                record.message_post(body=message)
        return records


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('product_id')
    def _check_pilot_order_invoicing(self):
        for line in self:
            if line.order_id.is_pilot_order and line.order_id.invoice_ids:
                raise ValidationError(_("Cannot modify pilot order with existing invoices."))
