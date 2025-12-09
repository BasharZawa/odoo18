# -*- coding: utf-8 -*-
from odoo import fields, models


class JobDiscountApprover(models.Model):
    _name = 'job.discount.approver'
    _description = 'Job Discount Approver'
    _order = 'max_discount asc'

    job_id = fields.Many2one('hr.job', string='Job Position', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    max_discount = fields.Float(string='Max Discount (%)', required=True)
    priority = fields.Integer(string='Priority', default=10)
