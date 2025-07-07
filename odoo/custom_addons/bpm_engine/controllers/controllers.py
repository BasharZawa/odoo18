# -*- coding: utf-8 -*-
from odoo import http
import requests


class BpmEngine(http.Controller):
    CAMUNDA_BASE_URL = "http://localhost:8080/engine-rest"  # Update with your Camunda REST API URL

    @http.route('/bpm_engine/bpm_engine', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/bpm_engine/bpm_engine/objects', auth='public')
    def list(self, **kw):
        return http.request.render('bpm_engine.listing', {
            'root': '/bpm_engine/bpm_engine',
            'objects': http.request.env['bpm_engine.bpm_engine'].search([]),
        })

    @http.route('/bpm_engine/bpm_engine/objects/<model("bpm_engine.bpm_engine"):obj>', auth='public')
    def object(self, obj, **kw):
        return http.request.render('bpm_engine.object', {
            'object': obj
        })

    @http.route('/bpm_engine/deploy', type='json', auth='public', methods=['POST'])
    def deploy_bpmn(self, **kwargs):
        """Deploy a BPMN diagram to the Camunda engine."""
        bpmn_xml = kwargs.get('bpmn_xml')
        if not bpmn_xml:
            return {"error": "No BPMN XML provided"}

        files = {
            'deployment-name': (None, 'bpmn_deployment'),
            'file': ('diagram.bpmn', bpmn_xml, 'text/xml')
        }

        response = requests.post(f"{self.CAMUNDA_BASE_URL}/deployment/create", files=files)
        return response.json()

    @http.route('/bpm_engine/start_process', type='json', auth='public', methods=['POST'])
    def start_process(self, **kwargs):
        """Start a process instance in the Camunda engine."""
        process_key = kwargs.get('process_key')
        variables = kwargs.get('variables', {})

        if not process_key:
            return {"error": "No process key provided"}

        payload = {
            "variables": {key: {"value": value} for key, value in variables.items()}
        }

        response = requests.post(f"{self.CAMUNDA_BASE_URL}/process-definition/key/{process_key}/start", json=payload)
        return response.json()

