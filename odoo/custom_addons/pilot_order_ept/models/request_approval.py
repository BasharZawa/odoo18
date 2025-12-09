from odoo import api, fields, models, api, _
from odoo.exceptions import ValidationError


class ApprovalRequestEPT(models.Model):
    _inherit = 'approval.request'

    is_pilot_order_req = fields.Boolean(string="Pilot Order Request", copy=False)
    is_freight_req = fields.Boolean(string="Freight Request", copy=False)

    def action_approve(self, approver=None):
        """Override approve action to automatically confirm the sale order"""
        result = super(ApprovalRequestEPT, self).action_approve(approver=approver)
        # Check if this approval is for a sale order
        for req in self:
            req = req.sudo()
            existing_request = req.search([
                ('request_owner_id', '=', req.sale_order_id.user_id.id),
                ('category_id', '=', req.category_id.id),
                ('request_status', 'in', ['new', 'pending'])
            ])
            pilot_order_req = existing_request.filtered(
                lambda r: r.is_pilot_order_req and r.reference == f'sale.order.pilot_order,{req.sale_order_id.id}')
            freight_req = existing_request.filtered(
                lambda r: r.is_freight_req and r.reference == f'sale.order.freight,{req.sale_order_id.id}')
            # For Pilot Order Approval
            if (req.is_pilot_order_req and len(pilot_order_req) < 1 and
                    req.sale_order_id and req.sale_order_id.state == 'on_hold' and req.request_status == 'approved'):
                pilot_order_tag = self.env.ref('pilot_order_ept.pilot_tag_high_value') or False
                if not pilot_order_tag:
                    pilot_order_tag = self.env['crm.tag'].sudo().create(
                        {'name': 'High Value Pilot Order', 'color': 1, 'is_pilot_approval': True})
                if pilot_order_tag and pilot_order_tag not in req.sale_order_id.tag_ids:
                    req.sale_order_id.tag_ids = [(4, pilot_order_tag.id)]
                req.sale_order_id.write(
                    {'state': 'draft', 'pilot_approval_state': 'approved',
                     'pilot_approval_date': fields.Datetime.now(),
                     'pilot_approved_by': self.env.user.id})
                req.sale_order_id.with_context(bypass_pilot_order_check=True).action_confirm()
            # For Freight Approval
            if req.is_freight_req and len(freight_req) < 1 and req.sale_order_id and req.sale_order_id.state not in (
                    'sale', 'cancel') and req.request_status == 'approved':
                req._apply_approved_modifications(req.sale_order_id)
        return result

    @staticmethod
    def _apply_approved_modifications(orders=False):
        """Apply approved pending freight/tax changes"""
        if not orders:
            return True

        for order in orders:
            if not order.pending_modifications:
                continue
            for ch in order.pending_modifications:
                to_be_added = to_be_removed = order.env['account.tax']
                line = order.order_line.browse(ch['line_id'])
                if not line.exists():
                    continue
                ch_type = ch['type']
                if ch_type == 'freight_change':
                    # Handle freight price changes
                    line.price_unit = ch['new_price']

                else:  # Assuming 3 represents tax operations
                    # Handle tax modifications
                    tax_data = ch.get('new_tax_ids')
                    if not tax_data or not isinstance(tax_data, list):
                        continue
                    for item in tax_data:
                        if item[0] == 3:
                            to_be_removed |= line.tax_id.browse(item[1])
                        else:
                            to_be_added |= line.tax_id.browse(item[1])
                    updated_tax = (line.tax_id | to_be_added) - to_be_removed
                    if updated_tax:
                        line.write({'tax_id': [(6, 0, updated_tax.ids)]})
                    else:
                        line.write({'tax_id': [(5, 0, 0)]})  # Clear all taxes if none remain

            # Clear pending modifications after processing
            order.pending_modifications = []

        return True


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    approval_type = fields.Selection(selection_add=[('freight_tax_req', 'Freight & Tax Request'), ('pilot_order_req', 'Pilot Order Request')])
