from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_create_landed_costs(self):
        """
        Override to automatically select relevant stock transfers (receipts)
        when creating a Landed Cost from a Vendor Bill.
        """
        res = super(AccountMove, self).button_create_landed_costs()
        
        if not isinstance(res, dict) or not res.get('res_id'):
            return res
            
        landed_cost_id = res['res_id']
        landed_cost = self.env['stock.landed.cost'].browse(landed_cost_id)
        
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')
        
        if not purchase_orders:
            return res

        relevant_pickings = self.env['stock.picking']
        
        for po in purchase_orders:
            # If picking_type_code is not available, we can access picking_type_id.code
            candidates = po.picking_ids.filtered(
                lambda p: p.state == 'done' and 
                          (p.picking_type_code == 'incoming' or p.picking_type_id.code == 'incoming')
            )
            
            if not candidates:
                continue
            
            # We search for Landed Costs that contain any of these candidates
            linked_costs = self.env['stock.landed.cost'].search([('picking_ids', 'in', candidates.ids), ('state', '!=', 'cancel')])
            already_linked_pickings = linked_costs.mapped('picking_ids')
            
            available_candidates = candidates - already_linked_pickings
            
            if not available_candidates:
                continue
                
            latest_picking = available_candidates.sorted(
                key=lambda p: p.date_done or p.scheduled_date or p.create_date, 
                reverse=True
            )
            
            relevant_pickings |= latest_picking
            
        # Update the created Landed Cost with the identified transfers
        if relevant_pickings:
            landed_cost.write({'picking_ids': [(6, 0, relevant_pickings.ids)]})
            
        return res
