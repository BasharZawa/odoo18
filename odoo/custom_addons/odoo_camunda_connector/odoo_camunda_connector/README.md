# Odoo 18 - Camunda Connector Module

**Version:** 18.0.1.0.0

## Overview

This Odoo module provides integration between Odoo 18 and an external Camunda BPMN engine (Platform 7 or 8 recommended). It allows users to:

*   Model BPMN 2.0 compliant processes directly within Odoo using an embedded `bpmn-js` editor.
*   Deploy these process definitions to a configured Camunda instance via its REST API.
*   Initiate Camunda process instances from Odoo (manually via definition or programmatically).
*   View and complete Camunda User Tasks assigned to them directly within the Odoo interface.
*   Enable Odoo to act as an External Task Worker, executing Odoo-specific logic for Camunda Service Tasks.

This module facilitates leveraging Camunda for robust process execution while keeping the user interface and business data management within Odoo.

## Features

*   **Embedded BPMN Modeler:** Uses `bpmn-js` for a rich visual modeling experience within Odoo workflow definition forms.
*   **Camunda Deployment:** Button to deploy/redeploy definitions to Camunda.
*   **Instance Initiation:** Button on deployed definitions to start test instances.
*   **User Task Integration:** Displays assigned Camunda User Tasks in an Odoo menu ("My Workflow Tasks") and allows completion.
*   **External Task Worker (Basic):** Includes a service and scheduled action structure to poll Camunda for external tasks based on topics (requires configuration and mapping of topics to Odoo actions).
*   **Configuration:** Odoo settings panel to configure Camunda REST API endpoint and authentication.

## Requirements

1.  **Odoo 18 Instance:** The module is designed for Odoo 18.
2.  **Running Camunda Instance:** A separate Camunda Platform 7 or 8 instance must be running and accessible via HTTP/S from the Odoo server.
3.  **Network Accessibility:** Odoo server must be able to make REST API calls to the Camunda instance URL.

## Installation

1.  Place the `odoo_camunda_connector` directory into your Odoo addons path.
2.  Restart the Odoo server.
3.  Go to Apps -> Update Apps List.
4.  Search for "Odoo Camunda Connector" and click Install.

## Configuration

1.  Navigate to **Settings -> General Settings**.
2.  Scroll down to the **Camunda Integration** section (or search for "Camunda").
3.  **Camunda REST API URL:** Enter the base URL for your Camunda engine's REST API (e.g., `http://<camunda_host>:<port>/engine-rest`).
4.  **Camunda Auth Type:** Select the authentication method used by your Camunda REST API (None, Basic Auth, Bearer Token).
5.  **Credentials:** Enter Username/Password for Basic Auth or the Token for Bearer Token if applicable.
6.  **Odoo Worker ID:** Keep or change the default ID used when Odoo polls for external tasks.
7.  **Test Connection:** Use the "Test Connection" button to verify Odoo can reach the Camunda API.
8.  **Save** the settings.

## Usage

### 1. Modeling & Deploying Workflows

*   Go to **Camunda Workflows -> Definitions -> Create**.
*   Enter a **Workflow Name**.
*   Use the **BPMN Diagram** tab to model your process using the embedded `bpmn-js` editor.
    *   **Important:** For Service Tasks intended to be handled by Odoo, configure the `Implementation` as `External` and set a `Topic` name in the Camunda properties panel within the editor. This topic name will be used by the Odoo worker.
    *   For User Tasks, use standard Camunda properties like `Assignee` (`${userId}` or specific user ID) or `Candidate Groups` to control assignment.
*   **Save** the definition.
*   Click **Deploy to Camunda**. The status should change to "Deployed", and Camunda deployment details will appear.

### 2. Starting Instances (Manual Test)

*   Open a deployed workflow definition.
*   Click **Start Test Instance**. This will initiate the workflow in Camunda with no initial variables.

### 3. Handling User Tasks

*   Go to **Camunda Workflows -> Tasks -> My Tasks**.
*   This list shows Camunda User Tasks assigned to the currently logged-in Odoo user (based on polling).
*   Open a task to view details (fetched from Camunda).
*   Click **Complete Task** to signal completion to Camunda.
    *   *Note: Currently, completing tasks does not send back any form data/variables. This requires further enhancement (e.g., using wizards or mapping Odoo fields).* 

### 4. External Task Worker (Setup Required)

*   The module includes a scheduled action (`camunda_external_task_worker_cron`) that polls Camunda for tasks based on configured topics.
*   **Activation:** By default, this scheduled action might be inactive. Go to **Settings -> Technical -> Automation -> Scheduled Actions**, find "Camunda: External Task Worker", and activate it.
*   **Topic Mapping:** You need to customize the `camunda_connector_service.py` file (specifically the `fetch_and_lock` call within the scheduled action logic, which is not fully implemented in this basic version) to:
    *   Define the list of `topics` Odoo should subscribe to.
    *   Implement the logic to execute specific Odoo actions based on the received task's topic and variables.
    *   Call `complete_external_task` or `handle_failure_external_task` accordingly.
*   This part requires Python development to map topics to your specific Odoo business logic.

## Limitations & Future Enhancements

*   **Basic External Task Worker:** Requires Python coding to map topics to Odoo actions.
*   **User Task Forms:** Does not currently support rendering Camunda embedded forms or automatically mapping variables to/from Odoo fields on task completion.
*   **Error Handling:** Basic error handling is implemented, but complex recovery scenarios might need more work.
*   **Monitoring:** Only very basic instance/task viewing is available in Odoo.
*   **Security:** Relies on configured REST API authentication; network security between Odoo and Camunda is crucial.
*   **Variable Handling:** Basic variable passing/fetching; complex object/JSON/file variable types might need specific handling.
*   **bpmn-js Properties Panel:** Does not yet include a custom properties panel for deep Odoo integration within the editor itself.

This module provides a solid foundation for Odoo-Camunda integration, focusing on the core mechanics of modeling, deployment, and task handling.

