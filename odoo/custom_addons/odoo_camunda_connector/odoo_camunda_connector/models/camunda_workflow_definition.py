# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class CamundaWorkflowDefinition(models.Model):
    _name = "camunda.workflow.definition"
    _description = "Camunda Workflow Definition"
    _order = "name, id"

    name = fields.Char(string="Workflow Name", required=True, index=True)
    description = fields.Text(string="Description")
    # Use a specific field type or widget for BPMN XML later
    bpmn_xml = fields.Text(string="BPMN XML", required=True, copy=False)
    
    # Camunda Deployment Info (Readonly, populated after deployment)
    camunda_deployment_id = fields.Char(string="Camunda Deployment ID", readonly=True, index=True, copy=False)
    camunda_definition_key = fields.Char(string="Camunda Definition Key", readonly=True, index=True, copy=False, 
                                         help="Key of the main process definition deployed in Camunda.")
    camunda_definition_id = fields.Char(string="Camunda Definition ID", readonly=True, index=True, copy=False,
                                        help="Specific ID of the deployed process definition version in Camunda.")
    camunda_definition_version = fields.Integer(string="Camunda Version", readonly=True, copy=False)
    
    deployment_status = fields.Selection([
        ("new", "New"), 
        ("deployed", "Deployed"), 
        ("error", "Deployment Error")
    ], string="Deployment Status", default="new", readonly=True, copy=False, index=True)
    deployment_message = fields.Text(string="Deployment Message", readonly=True, copy=False)
    
    active = fields.Boolean(default=True, index=True)
    # instance_ids = fields.One2many("camunda.workflow.instance.link", "definition_id", string="Instances") # Link via definition_key instead?
    # instance_count = fields.Integer(compute="_compute_instance_count", string="Instance Count")

    # TODO: Compute instance count based on links or Camunda query?
    # def _compute_instance_count(self):
    #     for record in self:
    #         record.instance_count = 0 # Placeholder

    def action_deploy_to_camunda(self):
        self.ensure_one()
        if not self.bpmn_xml:
            raise UserError(_("Cannot deploy an empty BPMN diagram."))

        connector = self.env["camunda.connector.service"]
        try:
            deployment_info = connector.deploy_definition(self.name, self.bpmn_xml)
            
            # Assuming deployment_info contains keys like: id, deployedProcessDefinitions
            deployment_id = deployment_info.get("id")
            deployed_defs = deployment_info.get("deployedProcessDefinitions")
            
            if not deployment_id or not deployed_defs:
                 raise UserError(_("Deployment response from Camunda is missing expected data. Response: %s") % deployment_info)

            # Find the main process definition (often only one per deployment)
            # This might need refinement if multiple processes are in one XML
            main_def_id = list(deployed_defs.keys())[0]
            main_def_data = deployed_defs[main_def_id]

            self.write({
                "camunda_deployment_id": deployment_id,
                "camunda_definition_id": main_def_id,
                "camunda_definition_key": main_def_data.get("key"),
                "camunda_definition_version": main_def_data.get("version"),
                "deployment_status": "deployed",
                "deployment_message": _("Successfully deployed on %s") % fields.Datetime.now(),
            })
            _logger.info("Successfully deployed BPMN definition ", self.name, " to Camunda. Deployment ID: ", deployment_id)
            # Optional: Return notification
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Deployment Successful"),
                    "message": _("Workflow ") + self.name + _(" deployed to Camunda."),
                    "sticky": False,
                    "type": "success",
                }
            }

        except Exception as e:
            _logger.error("Failed to deploy BPMN definition %s to Camunda: %s", self.name, e)
            self.write({
                "deployment_status": "error",
                "deployment_message": _("Deployment failed: %s") % e,
                "camunda_deployment_id": False, # Clear old IDs on failure
                "camunda_definition_id": False,
                "camunda_definition_key": False,
                "camunda_definition_version": False,
            })
            # Re-raise for user visibility
            raise UserError(_("Failed to deploy to Camunda: %s") % e)

    # Maybe add action to start an instance for testing?
    def action_start_instance(self):
        self.ensure_one()
        if self.deployment_status != "deployed" or not self.camunda_definition_key:
            raise UserError(_("Workflow must be successfully deployed before starting an instance."))
        
        # Open a wizard to collect variables?
        # For now, start with no variables
        connector = self.env["camunda.connector.service"]
        try:
            instance_info = connector.start_instance(self.camunda_definition_key, variables={})
            instance_id = instance_info.get("id")
            _logger.info("Started Camunda instance %s for definition %s", instance_id, self.camunda_definition_key)
            # Create an instance link?
            # self.env["camunda.workflow.instance.link"].create({
            #     "camunda_instance_id": instance_id,
            #     "camunda_definition_key": self.camunda_definition_key,
            #     # Add res_model/res_id if started from a specific record
            # })
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Instance Started"),
                    "message": _("Camunda instance started (ID: %s)") % instance_id,
                    "sticky": False,
                    "type": "success",
                }
            }
        except Exception as e:
             _logger.error("Failed to start Camunda instance for definition %s: %s", self.camunda_definition_key, e)
             raise UserError(_("Failed to start Camunda instance: %s") % e)


