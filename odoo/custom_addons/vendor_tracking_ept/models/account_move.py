from odoo import models, fields, _
from datetime import datetime, timedelta


class AccountMove(models.Model):
    _inherit = "account.move"

    def _check_invoice_discrepancies(self):
        """Check for mismatch between Vendor Bill, PO, and GRN"""
        discrepancies = []

        for move in self:
            if move.move_type != "in_invoice" or move.state != "posted":
                continue

            purchase_orders = move.line_ids.mapped("purchase_line_id.order_id")
            pickings = purchase_orders.mapped("picking_ids").filtered(lambda p: p.state == "done")

            # Price mismatch check
            for line in move.invoice_line_ids.filtered("purchase_line_id"):
                po_line = line.purchase_line_id
                if po_line and abs(line.price_unit - po_line.price_unit) > 0.01:
                    discrepancies.append(_("Price mismatch for product %s (PO: %s, Invoice: %s)") % (
                        line.product_id.display_name, po_line.price_unit, line.price_unit
                    ))

                # Compute received qty from all done pickings for this product
                received_qty = sum(
                    ml.qty_done
                    for picking in pickings
                    for ml in picking.move_line_ids
                    if ml.product_id == line.product_id and ml.state == "done"
                )

                if abs(line.quantity - received_qty) > 0.01:
                    discrepancies.append(_("Quantity mismatch for product %s (Received: %s, Invoice: %s)") % (
                        line.product_id.display_name, received_qty, line.quantity
                    ))

            # Total mismatch check
            if purchase_orders and abs(move.amount_total - sum(purchase_orders.mapped("amount_total"))) > 0.01:
                discrepancies.append(_("Total mismatch: PO Total = %s, Bill Total = %s") % (
                    sum(purchase_orders.mapped("amount_total")), move.amount_total
                ))

        return discrepancies

    def cron_invoice_mismatch_activity(self):
        """Cron job to check Vendor Bills and create activities if mismatch found"""
        today = datetime.now().date()
        mail_activity = self.env['mail.activity']
        ir_model = self.env['ir.model']._get('account.move')

        bills = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('journal_id.is_create_schedule_activity', '=', True),
        ])

        for move in bills:
            discrepancies = move._check_invoice_discrepancies()
            if discrepancies:
                journal = move.journal_id
                summary = _("Bill Mismatch - Procurement/Accounts Alert")
                note = _(
                    "<p>Alert on bill mismatch with reference to PO, GRN, and Bill.</p>"
                    "<p><b>Details:</b></p><ul>%s</ul>"
                ) % "".join("<li>%s</li>" % d for d in discrepancies)

                # Calculate deadline date based on journal configuration
                deadline_days = journal.activity_date_deadline or 1
                date_deadline = today + timedelta(days=deadline_days)

                # Use configured responsible users from journal, fallback to procurement/account groups
                user_ids = journal.activity_user_ids.ids
                if not user_ids:
                    # Fallback to group users if no specific users configured
                    procurement_group = self.env.ref("purchase.group_purchase_user", raise_if_not_found=False)
                    accounts_group = self.env.ref("account.group_account_user", raise_if_not_found=False)

                    if procurement_group:
                        user_ids += procurement_group.users.ids
                    if accounts_group:
                        user_ids += accounts_group.users.ids

                # Use default activity type if not configured in journal
                activity_type_id = self.env.ref('mail.mail_activity_data_todo').id

                for user_id in set(user_ids):
                    # 🔹 Prevent duplicate activity
                    exists = mail_activity.search_count([
                        ('res_id', '=', move.id),
                        ('res_model_id', '=', ir_model.id),
                        ('summary', '=', summary),
                        ('user_id', '=', user_id),
                    ])
                    if exists:
                        continue

                    vals = {
                        'activity_type_id': activity_type_id,
                        'summary': summary,
                        'note': note,
                        'res_id': move.id,
                        'res_model_id': ir_model.id,
                        'user_id': user_id,
                        'date_deadline': date_deadline,
                    }
                    mail_activity.create(vals)
        return True
