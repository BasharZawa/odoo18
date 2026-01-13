from odoo import models


class ProductVariantExtended(models.Model):
    """
    Add schedule action method and get base url method to for Replenishment Report
    """
    _inherit = 'stock.warehouse.orderpoint'


    def auto_email_for_replenish_review_reminder(self):
        """
        Schedular to send email for sending Replenish review reminder.
        :return: Boolean
        """
        template = self.env.ref('stock_extended_ept.email_template_replenish_review_reminder',
                                raise_if_not_found = False)
        action = self.env.ref('stock.action_orderpoint_replenish', raise_if_not_found=False)

        if template and template.email_to and action:
            if not template.email_from:
                template.email_from = self.env.user.email

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/web#action={action.id}&model=stock.replenishment&view_type=list"

            ctx = dict(self.env.context)
            ctx.update({'base_url': url})
            rpl = self.env['stock.warehouse.orderpoint'].search([], limit=1)
            if rpl:
                template.with_context(ctx).send_mail(
                    rpl.id,
                    force_send=True
                )
        return True
