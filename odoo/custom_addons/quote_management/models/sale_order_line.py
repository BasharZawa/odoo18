from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.fields import Date


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    unit_cost = fields.Float(string="Unit Cost", compute='_compute_cost_fields', store=True)
    line_cost = fields.Float(string="Line Cost", compute='_compute_cost_fields', store=True)
    gp = fields.Float(string="Gross Profit", compute='_compute_cost_fields', store=True)
    gp_percent = fields.Float(string="GP%", compute='_compute_cost_fields', store=True)
    approval_required = fields.Boolean(string="Requires Approval", compute="_compute_approval_required", store=True)
    approved_by_manager = fields.Boolean(string="Approved by Manager", groups="quote_management.group_sales_manager_approval")
    product_nature = fields.Selection(
        related='product_id.product_nature',
        string='Product Nature',
        store=True,
        readonly=True
    )
    discount_amount = fields.Float(string="Discount Amount", compute='_compute_discount_amount', store=True)


    @api.depends('discount', 'price_unit', 'product_uom_qty')
    def _compute_discount_amount(self):
        for line in self:
            if line.discount:
                line.discount_amount = (line.price_unit * line.product_uom_qty) * (line.discount / 100)
            else:
                line.discount_amount = 0.0


    @api.onchange('product_id')
    def _onchange_product_id_set_product_nature_readonly(self):
        for line in self:
            if line.product_id:
                line._fields['product_nature'].readonly = True
            else:
                line._fields['product_nature'].readonly = False

    @api.depends('product_id', 'discount')
    def _compute_approval_required(self):
        for line in self:
            line.approval_required = False
            if not line.product_id or not line.order_id.user_id:
                continue
            nature = line.product_id.x_nature or ''
            profile = self.env['discount.approval.profile'].search([
                ('user_id', '=', line.order_id.user_id.id),
                ('product_nature', '=', nature)
            ], limit=1)
            if profile and line.discount > profile.max_discount:
                line.approval_required = True

    @api.depends('product_id', 'product_uom_qty', 'price_unit', 'discount', 'unit_cost')
    def _compute_cost_fields(self):
        for line in self:
            if line.product_id and line.product_id.standard_price > 0:
                cost = line.product_id.standard_price
            elif line.unit_cost > 0:
                cost = line.unit_cost
            else:
                cost = 0.0

            line.unit_cost = cost
            line.line_cost = cost * line.product_uom_qty
            price_after_discount = line.price_unit * (1 - line.discount / 100)
            revenue = price_after_discount * line.product_uom_qty
            line.gp = revenue - line.line_cost
            line.gp_percent = (line.gp / revenue * 100) if revenue else 0.0

    def write(self, vals):
        for line in self:
            if line.order_id.state == 'sent':
                raise UserError("You cannot modify lines of a quotation that has been sent.")
        records = super().write(vals)
        self._notify_approval_activity()
        return records

    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._notify_approval_activity()
        return lines

    def _notify_approval_activity(self):
        for line in self:
            if line.approval_required and not line.approved_by_manager:
                group = self.env.ref("quote_management.group_sales_manager_approval")
                users = self.env['res.users'].search([('groups_id', 'in', group.id)])
                for user in users:
                    line.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        note=f"Approval required: Discount on '{line.product_id.display_name}' exceeds limit.",
                        date_deadline=Date.today()
                    )
                    line.message_post(
                        subject="Manager Approval Needed",
                        body=f"<p>The discount on product <strong>{line.product_id.display_name}</strong> exceeds the allowed limit for the assigned user. Approval is required.</p>",
                        partner_ids=[user.partner_id.id]
                    )
