from odoo import models, fields, api


class QualityCheckBulkWizard(models.TransientModel):
    _name = 'quality.check.bulk.wizard'
    _description = 'Quality Check Bulk Wizard'

    check_ids = fields.Many2many('quality.check', string="Checks")
    check_line_ids = fields.One2many('quality.check.bulk.wizard.line', 'wizard_id', string="Check Lines")
    action_type = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string="Action Type", required=True)
    
    failure_location_id = fields.Many2one(
        'stock.location', string="Failure Location",
        domain="[('usage', '=', 'internal')]"
    )
    failure_reason = fields.Text(string="Failure Reason")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_ids'):
            check_ids = self.env['quality.check'].browse(self.env.context.get('active_ids'))
            res['check_ids'] = [(6, 0, check_ids.ids)]
            
            # Create line records for display
            line_vals = []
            for check in check_ids:
                line_vals.append((0, 0, {
                    'check_id': check.id,
                }))
            res['check_line_ids'] = line_vals
            
            # Try to get default failure location from the first check's quality point
            if check_ids and check_ids[0].point_id.failure_location_ids:
                res['failure_location_id'] = check_ids[0].point_id.failure_location_ids[0].id
                
        if self.env.context.get('default_action_type'):
            res['action_type'] = self.env.context.get('default_action_type')
            
        return res

    def action_confirm(self):
        self.ensure_one()
        # Process only 'none' state checks to avoid re-processing finished ones
        checks_to_process = self.check_ids.filtered(lambda r: r.quality_state == 'none')
        
        if self.action_type == 'pass':
            for check in checks_to_process:
                check.do_pass()
            
        elif self.action_type == 'fail':
            # 1. Update reason on all checks first
            if self.failure_reason:
                for check in checks_to_process:
                    # Append reason to existing note or set it
                    if check.note:
                        check.note = f"{check.note}<br/>Failure Reason: {self.failure_reason}"
                    else:
                        check.note = f"Failure Reason: {self.failure_reason}"
                        
                    # Also update additional_note just in case (text field)
                    if check.additional_note:
                         check.additional_note = f"{check.additional_note}\nFailure Reason: {self.failure_reason}"
                    else:
                        check.additional_note = self.failure_reason

            # 2. Call do_fail for each check individually
            for check in checks_to_process:
                check.do_fail()
            
            # 3. Handle Stock Moves if location is selected
            if self.failure_location_id:
                for check in checks_to_process:
                    # Only if applicable (has move_line, picking, etc)
                    if check._can_move_line_to_failure_location():
                        check._move_line_to_failure_location(self.failure_location_id.id)
                        
        return {'type': 'ir.actions.act_window_close'}


class QualityCheckBulkWizardLine(models.TransientModel):
    _name = 'quality.check.bulk.wizard.line'
    _description = 'Quality Check Bulk Wizard Line'
    
    wizard_id = fields.Many2one('quality.check.bulk.wizard', string="Wizard", required=True, ondelete='cascade')
    check_id = fields.Many2one('quality.check', string="Quality Check", required=True)
    
    # Related fields for display
    name = fields.Char(related='check_id.name', string="Reference", readonly=True)
    product_id = fields.Many2one(related='check_id.product_id', string="Product", readonly=True)
    lot_id = fields.Many2one(related='check_id.lot_id', string="Lot/Serial", readonly=True)
    quality_state = fields.Selection(related='check_id.quality_state', string="Status", readonly=True)
