# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_create_schedule_activity = fields.Boolean(string="Bill Mismatch Create Schedule activity ? ",
                                                 default=False,
                                                 help="If checked, Then it will create Schedule "
                                                      "Activity against vendor bills which is mismatch.")
    activity_user_ids = fields.Many2many(comodel_name="res.users",
                                         relation="account_journal_res_users_rel",
                                         column1="account_journal_id", column2="res_users_id",
                                         string="Responsible Users")
    activity_date_deadline = fields.Integer(string="Deadline Days", default=1,
                                            help="Its add number of  days in schedule activity deadline date ")
