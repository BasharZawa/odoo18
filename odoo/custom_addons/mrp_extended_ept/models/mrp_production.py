from odoo import models, fields, _
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.addons.mrp.models.mrp_production import MrpProduction

class MrpProductionExtended(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done_replaced(self):
        """
        Overridden method: Custom logic for handling backorders and time tracking.
        """
        res = self.pre_button_mark_done()
        if res is not True:
            return res

        if self.env.context.get('mo_ids_to_backorder'):
            productions_to_backorder = self.browse(self.env.context['mo_ids_to_backorder'])
            productions_not_to_backorder = self - productions_to_backorder
        else:
            productions_not_to_backorder = self
            productions_to_backorder = self.env['mrp.production']
        productions_not_to_backorder = productions_not_to_backorder.with_context(
            no_procurement=True)
        self.workorder_ids.button_finish()


        if len(productions_not_to_backorder.procurement_group_id) == 1 and all(
                [mrp.backorder_sequence for mrp in productions_not_to_backorder]):
            self._create_custom_timesheet_entries(productions_not_to_backorder)

        backorders = productions_to_backorder and productions_to_backorder._split_productions()
        backorders = backorders - productions_to_backorder

        productions_not_to_backorder._post_inventory(cancel_backorder=True)
        productions_to_backorder._post_inventory(cancel_backorder=True)

        # if completed products make other confirmed/partially_available moves available, assign them
        done_move_finished_ids = (
                    productions_to_backorder.move_finished_ids | productions_not_to_backorder.move_finished_ids).filtered(
            lambda m: m.state == 'done')
        done_move_finished_ids._trigger_assign()

        # Moves without quantity done are not posted => set them as done instead of canceling. In
        # case the user edits the MO later on and sets some consumed quantity on those, we do not
        # want the move lines to be canceled.
        (productions_not_to_backorder.move_raw_ids | productions_not_to_backorder.move_finished_ids).filtered(
            lambda x: x.state not in ('done', 'cancel')).write({
            'state': 'done',
            'product_uom_qty': 0.0,
        })
        for production in self:
            production.write({
                'date_finished': fields.Datetime.now(),
                'priority': '0',
                'is_locked': True,
                'state': 'done',
            })

        # It is prudent to reserve any quantity that has become available to the backorder
        # production's move_raw_ids after the production which spawned them has been marked done.
        backorders_to_assign = backorders.filtered(
            lambda order:
            order.picking_type_id.reservation_method == 'at_confirm'
        )
        for backorder in backorders_to_assign:
            backorder.action_assign()

        report_actions = self._get_autoprint_done_report_actions()
        if self.env.context.get('skip_redirection'):
            if report_actions:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'do_multi_print',
                    'context': {},
                    'params': {
                        'reports': report_actions,
                    }
                }
            return True
        another_action = False
        if not backorders:
            if self.env.context.get('from_workorder'):
                another_action = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.production',
                    'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                    'res_id': self.id,
                    'target': 'main',
                }
            elif self.env.user.has_group('mrp.group_mrp_reception_report'):
                mos_to_show = self.filtered(
                    lambda mo: mo.picking_type_id.auto_show_reception_report)
                lines = mos_to_show.move_finished_ids.filtered(lambda
                                                                   m: m.product_id.is_storable and m.state != 'cancel' and m.picked and not m.move_dest_ids)
                if lines:
                    if any(mo.show_allocation for mo in mos_to_show):
                        another_action = mos_to_show.action_view_reception_report()
            if report_actions:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'do_multi_print',
                    'params': {
                        'reports': report_actions,
                        'anotherAction': another_action,
                    }
                }
            if another_action:
                return another_action
            return True
        context = self.env.context.copy()
        context = {k: v for k, v in context.items() if not k.startswith('default_')}
        for k, v in context.items():
            if k.startswith('skip_'):
                context[k] = False
        another_action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'context': dict(context, mo_ids_to_backorder=None)
        }
        if len(backorders) == 1:
            another_action.update({
                'views': [[False, 'form']],
                'view_mode': 'form',
                'res_id': backorders[0].id,
            })
        else:
            another_action.update({
                'name': _("Backorder MO"),
                'domain': [('id', 'in', backorders.ids)],
                'views': [[False, 'list'], [False, 'form']],
                'view_mode': 'list,form',
            })
        if report_actions:
            return {
                'type': 'ir.actions.client',
                'tag': 'do_multi_print',
                'params': {
                    'reports': report_actions,
                    'anotherAction': another_action,
                }
            }
        return another_action

    def _create_custom_timesheet_entries(self, productions_not_to_backorder):
        """
        Custom logic for handling backorders and time tracking.
        """
        base_production = productions_not_to_backorder.filtered(
            lambda mo: mo.backorder_sequence == 1)
        all_related_productions = self.env['mrp.production'].search([
            ('procurement_group_id', '=', base_production.procurement_group_id.id),
            ('state', '!=', 'cancel')])
        if base_production:
            # This condition prevents creating duplicate time entries or dividing duration further than actually needed.
            other_production = all_related_productions - base_production
            total_qty = sum([rec.product_uom_qty for rec in all_related_productions])
            vals_list = []
            for base_wo in base_production.workorder_ids:
                other_production_wos = other_production.mapped('workorder_ids').filtered(
                    lambda other_wo: other_wo.operation_id == base_wo.operation_id)
                for time_rec in base_wo.time_ids:
                    time_rec.duration = (time_rec.duration / total_qty) * base_wo.qty_produced
                    for other_wo in other_production_wos:
                        vals_list.append({
                            'workorder_id': other_wo.id,
                            'workcenter_id': other_wo.workcenter_id.id,
                            'description': _('Time Tracking: %(user)s', user=self.env.user.name),
                            'loss_id': time_rec.loss_id.id,
                            'date_start': time_rec.date_start,
                            'date_end': time_rec.date_end,
                            'duration': time_rec.duration,
                            'user_id': time_rec.user_id.id,
                            'employee_id': time_rec.employee_id.id,
                            'company_id': time_rec.company_id.id,
                        })
            vals_list and self.env['mrp.workcenter.productivity'].create(vals_list)
        return True

    MrpProduction.button_mark_done = button_mark_done_replaced
