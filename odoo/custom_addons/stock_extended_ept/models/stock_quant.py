# -*- coding: utf-8 -*-

from odoo import models, fields, _


class StockQuantExtend(models.Model):
    """
    Add fields for Inventory approval functionality
    """
    _inherit = 'stock.quant'

    has_approvals = fields.Boolean(compute="_compute_has_approvals", store=False)

    def write(self, values):
        """
        Inherited method in order to implement functionality related approvals
        """
        res = super().write(values)
        if ('from_approval' not in self.env.context and 'inventory_quantity' in values and
                not self.env.user.has_group('stock_extended_ept.inv_adjustment_approval_group_user')):
            for quant in self:
                self._handle_approval_request(quant)
        return res

    def _handle_approval_request(self, quant):
        """
        Manage approval requests for inventory adjustment:
        - Cancel other users' requests
        - Update current user's request
        - Create a new request if none exists
        """
        # categ = self.env.ref('stock_extended_ept.approval_type_inv_adjust_stock')
        categ = self.env['approval.category'].search([
            ('approval_type', '=', 'stock_adjustment_req'), ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not categ:
            categ = self.env['approval.category'].sudo().create({
                'name': 'Stock Adjustment Approval',
                'approver_ids': [],
                'approval_type': 'stock_adjustment_req',
                'company_id': self.env.company.id,
            })
        exist_recs = self._get_pending_approvals(quant)
        if exist_recs:
            # other_user_approvals = exist_recs.filtered(lambda r: r.request_owner_id != self.env.user)
            current_user_approvals = exist_recs.filtered(lambda r: r.request_owner_id == self.env.user)
            # if other_user_approvals:
            #     other_user_approvals.action_cancel()
            if current_user_approvals:
                current_user_approvals.write({'quantity': quant.inventory_quantity})
            else:
                self._create_approval_request(quant, categ)
        else:
            self._create_approval_request(quant, categ)

    def _get_pending_approvals(self, quant):
        """
        Search for pending approval requests for the given quant's product and location.
        """
        return self.env['approval.request'].search([
            ('request_status', '=', 'pending'),
            ('stock_quant_product_id', '=', quant.product_id.id),
            ('stock_quant_location_id', '=', quant.location_id.id)
        ])

    def _create_approval_request(self, quant, categ):
        """
        Create and confirm a new approval request for the given quant and category.
        """
        approval = self.env['approval.request'].create({
            'request_owner_id': self.env.user.id,
            'category_id': categ.id,
            'stock_quant_product_id': quant.product_id.id,
            'stock_quant_location_id': quant.location_id.id,
            'quantity': quant.inventory_quantity
        })
        approval.action_confirm()
        return approval

    def action_clear_inventory_quantity(self):
        """
        Clears inventory quantity and cancels any pending approval requests for this quant
        """
        res = super().action_clear_inventory_quantity()
        # for quant in self:
        #     approvals = self.env['approval.request'].search([
        #         ('request_status', '=', 'pending'),
        #         ('stock_quant_product_id', '=', quant.product_id.id),
        #         ('stock_quant_location_id', '=', quant.location_id.id)
        #     ])
        #     approvals.action_cancel()
        return res

    def open_adjustment_approval_requests(self):
        """
        Returns an action to open approval requests for this quant in the appropriate view
        """
        approvals = self.env['approval.request'].search([
            ('request_status', '=', 'pending'),
            ('stock_quant_product_id', '=', self.product_id.id),
            ('stock_quant_location_id', '=', self.location_id.id)
        ])
        action = {
            'name': _('Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'context': {'create': False},
        }
        if len(approvals) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': approvals.id,
            })
        else:
            action.update({
                'view_mode': 'list,form,kanban',
                'domain': [('id', 'in', approvals.ids)],
            })
        return action

    def _compute_has_approvals(self):
        """
        Computes if there are any pending approval requests for this quant and sets the has_approvals field
        """
        for rec in self:
            approvals = self.env['approval.request'].search([
                ('request_status', '=', 'pending'),
                ('stock_quant_product_id', '=', rec.product_id.id),
                ('stock_quant_location_id', '=', rec.location_id.id)
            ])
            rec.has_approvals = bool(approvals)
