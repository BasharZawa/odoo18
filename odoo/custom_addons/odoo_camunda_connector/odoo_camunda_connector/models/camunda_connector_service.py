# -*- coding: utf-8 -*-

import requests
import json
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

class CamundaConnectorService(models.AbstractModel):
    _name = "camunda.connector.service"
    _description = "Camunda REST API Connector Service"

    def _get_config_param(self, param_name):
        return self.env["ir.config_parameter"].sudo().get_param(f"odoo_camunda_connector.{param_name}")

    def _get_camunda_auth(self):
        auth_type = self._get_config_param("camunda_auth_type")
        if auth_type == "basic":
            username = self._get_config_param("camunda_rest_username")
            password = self._get_config_param("camunda_rest_password")
            if not username or not password:
                raise UserError(_("Camunda Basic Authentication credentials are not configured in settings."))
            return requests.auth.HTTPBasicAuth(username, password)
        elif auth_type == "bearer":
            token = self._get_config_param("camunda_bearer_token")
            if not token:
                raise UserError(_("Camunda Bearer Token is not configured in settings."))
            return {"Authorization": f"Bearer {token}"} # Return as headers dict
        return None # No auth

    def _send_request(self, method, endpoint, params=None, json_data=None, data=None, files=None, timeout=30):
        base_url = self._get_config_param("camunda_rest_url")
        if not base_url:
            raise UserError(_("Camunda REST API URL is not configured in Odoo settings."))
        
        url = f"{base_url.rstrip("/")}/{endpoint.lstrip("/")}"
        headers = {"Accept": "application/json"}
        auth = None
        
        auth_config = self._get_camunda_auth()
        if isinstance(auth_config, dict): # Bearer token
            headers.update(auth_config)
        else: # Basic auth or None
            auth = auth_config

        if json_data and not headers.get("Content-Type"):
             headers["Content-Type"] = "application/json"
        
        _logger.debug("Sending Camunda request: %s %s", method, url)
        _logger.debug("Params: %s", params)
        _logger.debug("JSON Data: %s", json_data)
        _logger.debug("Headers: %s", headers)

        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=json_data,
                data=data,
                files=files,
                headers=headers,
                auth=auth,
                timeout=timeout
            )
            _logger.debug("Camunda response status: %s", response.status_code)
            _logger.debug("Camunda response body: %s", response.text[:500]) # Log truncated body
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            # Handle potential empty response body for certain successful requests (e.g., 204 No Content)
            if response.status_code == 204:
                return response # Return the response object directly
            return response.json()
        except requests.exceptions.Timeout as e:
            _logger.error("Camunda request timeout: %s", e)
            raise UserError(_("Connection to Camunda timed out: %s") % e)
        except requests.exceptions.ConnectionError as e:
            _logger.error("Camunda connection error: %s", e)
            raise UserError(_("Could not connect to Camunda at %s: %s") % (base_url, e))
        except requests.exceptions.HTTPError as e:
            _logger.error("Camunda HTTP error: %s", e)
            error_details = response.text
            try: # Try to parse Camunda error response
                error_json = response.json()
                error_details = f"{error_json.get(\"type\")}: {error_json.get(\"message\")}"
            except json.JSONDecodeError:
                pass # Use raw text if not JSON
            raise UserError(_("Camunda API request failed (%(status_code)s): %(error)s") % {"status_code": response.status_code, "error": error_details})
        except Exception as e:
            _logger.error("Camunda generic error: %s", e)
            raise UserError(_("An unexpected error occurred while communicating with Camunda: %s") % e)

    # --- Deployment Methods --- 
    def deploy_definition(self, deployment_name, bpmn_xml_content):
        """Deploys a BPMN definition to Camunda."""
        files = {
            "deployment-name": (None, deployment_name),
            "enable-duplicate-filtering": (None, "true"),
            f"{deployment_name}.bpmn": (f"{deployment_name}.bpmn", bpmn_xml_content, "application/xml")
        }
        # Use data=None, json=None, pass files directly
        return self._send_request("POST", "/deployment/create", files=files)

    # --- Process Instance Methods --- 
    def start_instance(self, definition_key, variables=None, business_key=None):
        """Starts a process instance by definition key."""
        payload = {}
        if variables:
            # Camunda expects variables in a specific format
            payload["variables"] = self._format_variables_for_camunda(variables)
        if business_key:
            payload["businessKey"] = str(business_key)
        
        endpoint = f"/process-definition/key/{definition_key}/start"
        return self._send_request("POST", endpoint, json_data=payload)

    # --- Task Methods --- 
    def get_tasks(self, params=None):
        """Queries for tasks based on parameters."""
        # Example params: {"assignee": "demo", "processInstanceId": "..."}
        return self._send_request("GET", "/task", params=params)

    def get_task_variables(self, task_id, variable_names=None):
        """Gets variables for a specific task."""
        params = {}
        if variable_names:
            params["variableNames"] = ",".join(variable_names)
        endpoint = f"/task/{task_id}/variables"
        return self._send_request("GET", endpoint, params=params)

    def complete_task(self, task_id, variables=None):
        """Completes a User Task."""
        payload = {}
        if variables:
            payload["variables"] = self._format_variables_for_camunda(variables)
        endpoint = f"/task/{task_id}/complete"
        # Camunda returns 204 No Content on success
        response = self._send_request("POST", endpoint, json_data=payload)
        return response.status_code == 204

    # --- External Task Methods --- 
    def fetch_and_lock(self, worker_id, topic, lock_duration=60000, max_tasks=10):
        """Fetches and locks external tasks for a specific topic."""
        payload = {
            "workerId": worker_id,
            "maxTasks": max_tasks,
            "usePriority": True, # Recommended by Camunda docs
            "topics": [
                {
                    "topicName": topic,
                    "lockDuration": lock_duration
                    # Can add variables to fetch: "variables": ["var1", "var2"]
                }
            ]
        }
        endpoint = "/external-task/fetchAndLock"
        # This request might time out if no tasks are available, handle appropriately
        try:
            # Use a longer timeout for fetchAndLock as it waits for tasks
            return self._send_request("POST", endpoint, json_data=payload, timeout=lock_duration / 1000 + 10) 
        except UserError as e:
            # Don't raise error if it's just a timeout or connection issue during polling
            if "timed out" in str(e) or "Could not connect" in str(e):
                _logger.warning("Fetch and lock for topic '%s' failed (timeout/connection): %s", topic, e)
                return [] # Return empty list, worker will retry later
            else:
                raise # Re-raise other UserErrors
        except Exception as e:
             _logger.error("Unexpected error during fetch and lock for topic ", topic, ": ", e)
             return [] # Return empty list on other errors

    def complete_external_task(self, task_id, worker_id, variables=None):
        """Completes an external task."""
        payload = {"workerId": worker_id}
        if variables:
            payload["variables"] = self._format_variables_for_camunda(variables)
        endpoint = f"/external-task/{task_id}/complete"
        response = self._send_request("POST", endpoint, json_data=payload)
        return response.status_code == 204

    def handle_failure_external_task(self, task_id, worker_id, error_message, error_details=None, retries=None, retry_timeout=None):
        """Reports a failure for an external task."""
        payload = {
            "workerId": worker_id,
            "errorMessage": str(error_message),
        }
        if error_details:
            payload["errorDetails"] = str(error_details)
        if retries is not None:
            payload["retries"] = int(retries)
        if retry_timeout is not None: # Timeout in milliseconds
            payload["retryTimeout"] = int(retry_timeout)
        
        endpoint = f"/external-task/{task_id}/failure"
        response = self._send_request("POST", endpoint, json_data=payload)
        return response.status_code == 204

    # --- Helper Methods --- 
    def _format_variables_for_camunda(self, odoo_vars):
        """Converts a Python dict to Camunda REST API variable format."""
        camunda_vars = {}
        if not isinstance(odoo_vars, dict):
            return camunda_vars # Or raise error?
        for key, value in odoo_vars.items():
            # Basic type handling, needs expansion for dates, files, json etc.
            var_type = None
            if isinstance(value, bool):
                var_type = "Boolean"
            elif isinstance(value, int):
                var_type = "Integer"
            elif isinstance(value, float):
                var_type = "Double"
            elif isinstance(value, str):
                var_type = "String"
            # Add more types: Date, File, Object, Json?
            
            if var_type:
                camunda_vars[key] = {"value": value, "type": var_type}
            else:
                # Default to String or JSON? Or raise error?
                _logger.warning("Unsupported variable type for key ", key, ": ", type(value), ". Sending as String.")
                camunda_vars[key] = {"value": str(value), "type": "String"}
        return camunda_vars


