# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class CamundaUserTask(models.Model):
    _name = "camunda.user.task"
    _description = "Camunda User Task Representation in Odoo"
    _order = "create_time desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Task Name", required=True, readonly=True)
    camunda_task_id = fields.Char(string="Camunda Task ID", required=True, index=True, readonly=True)
    camunda_instance_id = fields.Char(string="Camunda Instance ID", required=True, index=True, readonly=True)
    camunda_definition_key = fields.Char(string="Camunda Definition Key", index=True, readonly=True)
    
    # TODO: Implement logic to find the correct link based on instance_id
    # instance_link_id = fields.Many2one("camunda.workflow.instance.link", string="Related Odoo Record Link", compute="_compute_instance_link", store=False)
    
    assignee_user_id = fields.Many2one("res.users", string="Assignee", readonly=True, index=True)
    # Storing candidate groups might be complex if mapping isn't direct
    # candidate_group_ids = fields.Many2many("res.groups", string="Candidate Groups", readonly=True)
    candidate_groups_str = fields.Char(string="Candidate Groups (Camunda)", readonly=True, help="Raw candidate group IDs from Camunda")

    create_time = fields.Datetime(string="Created in Camunda", readonly=True)
    due_date = fields.Datetime(string="Due Date", readonly=True)
    form_key = fields.Char(string="Camunda Form Key", readonly=True)
    
    # Store variables fetched from Camunda for display or use in Odoo form
    variables_json = fields.Text(string="Task Variables (JSON)", readonly=True)
    # TODO: Add computed fields to display variables nicely?

    state = fields.Selection([
        ("active", "Active"), 
        ("completed", "Completed")
    ], string="Status", default="active", required=True, index=True, readonly=True, copy=False)
    
    # Optional: Link to Odoo activity for visibility in user's chatter
    # activity_id = fields.Many2one("mail.activity", string="Related Activity")

    # Compute method for instance_link_id (example)
    # def _compute_instance_link(self):
    #     link_model = self.env["camunda.workflow.instance.link"]
    #     for task in self:
    #         link = link_model.search([("camunda_instance_id", "=", task.camunda_instance_id)], limit=1)
    #         task.instance_link_id = link.id

    # Action to complete the task
    def action_complete_task(self):
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("Task is not active."))
        
        # TODO: Potentially open a wizard to collect completion variables?
        # For now, complete with no variables.
        completion_variables = {}
        
        connector = self.env["camunda.connector.service"]
        try:
            success = connector.complete_task(self.camunda_task_id, variables=completion_variables)
            if success:
                self.write({"state": "completed"})
                _logger.info("Completed Camunda User Task %s (Odoo ID: %s)", self.camunda_task_id, self.id)
                # Optional: Post message or return notification
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Task Completed"),
                        "message": _("Task '%s' completed successfully.") % self.name,
                        "sticky": False,
                        "type": "success",
                    }
                }
            else:
                 raise UserError(_("Failed to complete task in Camunda (API call succeeded but indicated failure)."))
        except Exception as e:
            _logger.error("Failed to complete Camunda User Task %s: %s", self.camunda_task_id, e)
            raise UserError(_("Failed to complete task: %s") % e)

    # Action to fetch variables (if needed on demand)
    def action_fetch_variables(self):
        self.ensure_one()
        connector = self.env["camunda.connector.service"]
        try:
            variables = connector.get_task_variables(self.camunda_task_id)
            self.variables_json = json.dumps(variables, indent=2)
        except Exception as e:
            raise UserError(_("Failed to fetch task variables: %s") % e)


