from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import html_escape


class SaleBelowCostWizard(models.TransientModel):
    _name = 'sale.below.cost.wizard'
    _description = 'Approve Selling Below Cost'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    below_lines_info = fields.Html(string='Below-Cost Lines', readonly=True)
    reason = fields.Html(string='Reason for Selling Below Cost', required=True)

    @api.model
    def default_get(self, fields_list):
        """Prepare below-cost product information in HTML table format."""
        vals = super().default_get(fields_list)
        order = self.env['sale.order'].browse(self.env.context.get('default_order_id'))

        if order:
            lines = order.order_line.filtered(lambda l: l.below_cost)
            if lines:
                # HTML table header
                table_html = self._prepare_below_cost_lines_html(lines)

                table_html += "</tbody></table>"
                vals['below_lines_info'] = table_html
                vals['order_id'] = order.id

        return vals

    # write a separate method to prepare table html for the above method
    def _prepare_below_cost_lines_html(self, lines):
        table_html = """
            <table style="width:100%; border-collapse: collapse; text-align:left;">
                <thead>
                    <tr style="background-color:#f2f2f2;">
                        <th style="border:1px solid #ddd; padding:8px;">Product Name</th>
                        <th style="border:1px solid #ddd; padding:8px;">Qty</th>
                        <th style="border:1px solid #ddd; padding:8px;">Actual Price</th>
                        <th style="border:1px solid #ddd; padding:8px;">Current Selling Price</th>
                        <th style="border:1px solid #ddd; padding:8px;">Original Cost</th>
                    </tr>
                </thead>
                <tbody>
        """

        for line in lines:
            actual_price = line.product_id.list_price
            current_price = (
                line.price_unit * (1.0 - (line.discount / 100.0))
                if line.discount else line.price_unit
            )
            original_cost = line.product_id.standard_price

            table_html += f"""
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;">{html_escape(line.product_id.display_name or '')}</td>
                    <td style="border:1px solid #ddd; padding:8px;">{line.product_uom_qty}</td>
                    <td style="border:1px solid #ddd; padding:8px;">{actual_price:.2f}</td>
                    <td style="border:1px solid #ddd; padding:8px;">{current_price:.2f}</td>
                    <td style="border:1px solid #ddd; padding:8px;">{original_cost:.2f}</td>
                </tr>
            """
        return table_html if table_html else False

    def action_request_approval(self):
        """Create an approval request for below-cost sales."""
        self.ensure_one()
        order = self.order_id
        if not order:
            raise UserError(_('No sale order found.'))

        ApprovalRequest = self.env['approval.request']
        ApprovalCategory = self.env['approval.category']

        # Get or create approval category
        # category = self.env.ref(
        #     "sale_below_cost_approval_ept.approvals_category_discrepancy_so",
        #     raise_if_not_found=False,
        # )
        category = self.env['approval.category'].search([
            ('approval_type', '=', 'below_cost_req'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not category:
            category = ApprovalCategory.create({
                'name': 'Sales Discrepancy Approval',
                'approver_ids': [],
                'approval_type': 'below_cost_req',
                'company_id': self.env.company.id,
            })
        if not order.order_line.filtered(lambda l: l.below_cost):
            return False

        order.write({'state': 'on_hold'})

        # Prepare approvers
        manager_group = self.env.ref('sales_team.group_sale_manager')
        approver_vals = [(0, 0, {'user_id': user.id, 'required': 'required'}) for user in manager_group.users]

        reason_content = (self.below_lines_info or '') + (self.reason or '')
        # Create approval request
        request = ApprovalRequest.create({
            'name': _('Sales Price Discrepancy Approval for %s') % (order.name or _('New')),
            'request_owner_id': order.user_id.id,
            'category_id': category.id,
            'partner_id': order.partner_id.id,
            'request_status': 'pending',
            'reference': f'sale.order.discrepancy,{order.id}',
            # 'approver_ids': approver_vals,
            'date': fields.Date.today(),
            'reason': reason_content,
            'sale_order_id': order.id,
            'is_discrepancy_req': True,
        })
        request.sudo().action_confirm()

        # Post message on the order
        order.message_post(
            body=_(
                "Order has some discrepancy in the price. "
                "Approval request %s has been created."
            ) % request.name,
            subtype_xmlid="mail.mt_note",
        )

        order.write({'state': 'on_hold'})
        return {'type': 'ir.actions.act_window_close'}
