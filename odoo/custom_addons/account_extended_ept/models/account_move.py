# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveExtended(models.Model):
    _inherit = "account.move"


    def action_print_pdf(self):
        #Override: To make SEDCO Invoice Report as default report while printing invoice.
        self.ensure_one()
        invoice_template = self.env.ref('account_extended_ept.action_report_invoice_sedco')
        if not invoice_template or self.move_type not in ['out_invoice', 'out_receipt']:
            invoice_template = self.env['account.move.send']._get_default_pdf_report_id(self)
        report_action = invoice_template.report_action(self.id, config=False)
        return self._get_action_with_base_document_layout_configurator(report_action)
