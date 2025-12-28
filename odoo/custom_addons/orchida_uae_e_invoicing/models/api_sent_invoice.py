from odoo import models, fields
from odoo.exceptions import UserError
from  ..services import helper_functions



class ApiSentInvoice(models.Model):
    _name = "api.sent.invoice"
    _description = "Invoices Sent to API"
    _order = "sent_date desc"

    move_id = fields.Many2one("account.move", string="Invoice", required=True)
    move_name = fields.Char(string="Invoice Number", related="move_id.name", store=True)
    partner_id = fields.Many2one(related="move_id.partner_id", string="Customer", store=True)
    amount_total = fields.Monetary(related="move_id.amount_total", string="Total", store=True)
    currency_id = fields.Many2one(related="move_id.currency_id", string="Currency", store=True)

    sent_date = fields.Datetime(default=fields.Datetime.now, string="Sent Date")
    success = fields.Boolean(string="Success")
    response = fields.Text(string="API Response")

    def resend_invoice_to_api(self):
        skipped = []
        sent_count = 0

        for record in self:
            if not record.move_id:
                continue

            status, info = helper_functions.check_invoice_before_resend(self.env, record.move_id)

            if status == "skip":
                skipped.append(info)
                continue

            # send invoice
            record.move_id._send_invoice_to_api(record.move_id)
            sent_count += 1

        self.env.cr.commit()

        if skipped:
            skipped_list = "\n - ".join(skipped)
            raise UserError(
                f"Some invoices were skipped (already sent successfully):\n"
                f" - {skipped_list}\n\n"
                f"Other invoices were resent : {sent_count}"
            )

        if sent_count > 0:
            action = self.env.ref('orchida_uae_e_invoicing.action_api_sent_invoice').read()[0]
            action['view_mode'] = 'tree,form'
            action['target'] = 'current'
            return action

        return True

        return True

    def resend_invoice_form_to_api(self):
        skipped_invoices = []
        sent_count = 0

        for record in self:
            if record.move_id:

                status, info = helper_functions.check_invoice_before_resend(self.env,record.move_id)

                if status == "skip":
                    skipped_invoices.append(info)
                    continue


                record.move_id._send_invoice_to_api(record.move_id)
                sent_count += 1
        if skipped_invoices:
            raise UserError(f"This invoices were not resent because they were already sent:\n")
            return True




        action = self.env.ref('orchida_uae_e_invoicing.action_api_sent_invoice').read()[0]

        action['view_mode'] = 'tree,form'
        action['target'] = 'current'

        return action

