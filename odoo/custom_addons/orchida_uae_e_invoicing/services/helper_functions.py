from odoo import models

def check_invoice_before_resend(env, move):
    last_sent = env['api.sent.invoice'].search(
        [('move_id', '=', move.id)],
        order='sent_date desc',
        limit=1
    )

    if last_sent and last_sent.success:
        return ("skip", move.name)

    return ("send", None)