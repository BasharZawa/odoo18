# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    camunda_rest_url = fields.Char(
        string="Camunda REST API URL", 
        config_parameter="odoo_camunda_connector.camunda_rest_url",
        help="Base URL for the Camunda REST API (e.g., http://localhost:8080/engine-rest)"
    )
    camunda_auth_type = fields.Selection([
        ("none", "None"), 
        ("basic", "Basic Auth"), 
        ("bearer", "Bearer Token")
    ], string="Camunda Auth Type", 
       config_parameter="odoo_camunda_connector.camunda_auth_type", 
       default="none"
    )
    camunda_rest_username = fields.Char(
        string="Camunda REST Username", 
        config_parameter="odoo_camunda_connector.camunda_rest_username"
    )
    # Storing password directly in config_parameter is not ideal for production.
    # Consider using password=True on the field and managing storage more securely if needed.
    camunda_rest_password = fields.Char(
        string="Camunda REST Password", 
        config_parameter="odoo_camunda_connector.camunda_rest_password"
    )
    camunda_bearer_token = fields.Char(
        string="Camunda Bearer Token", 
        config_parameter="odoo_camunda_connector.camunda_bearer_token"
    )
    camunda_worker_id = fields.Char(
        string="Odoo Worker ID", 
        config_parameter="odoo_camunda_connector.camunda_worker_id", 
        default="odoo_worker",
        help="Identifier used when this Odoo instance polls for external tasks."
    )

    # Optional: Add a button to test the connection
    def test_camunda_connection(self):
        self.ensure_one()
        # Get the connector service (implementation needed later)
        connector = self.env["camunda.connector.service"]
        try:
            # Example: Try fetching engine info or deployments
            response = connector._send_request("GET", "/engine") 
            if response.status_code == 200:
                # Use Odoo's notification system
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Success"),
                        "message": _("Successfully connected to Camunda Engine: %s") % response.json()[0].get("name", "Default"),
                        "sticky": False,
                        "type": "success",
                    }
                }
            else:
                raise UserError(_("Connection failed. Status Code: %s\nResponse: %s") % (response.status_code, response.text))
        except Exception as e:
            raise UserError(_("Connection failed: %s") % e)


