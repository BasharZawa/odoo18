# -*- coding: utf-8 -*-
from odoo import fields, models


class HrJob(models.Model):
    _inherit = 'hr.job'

    allocation_ids = fields.One2many('discount.allocation', 'job_id', string='Discount Allocations')
    max_total_discount_percent = fields.Float(string='Max Total Discount (%)', default=20.0)
    use_discount = fields.Boolean(string='Use Discount Allocation', default=False)
    discount_approver_ids = fields.One2many('job.discount.approver', 'job_id', string='Discount Approvers')
