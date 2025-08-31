from odoo import http
from odoo.http import request


class BPMNEditorController(http.Controller):

    @http.route('/web/bpmn_editor/<int:definition_id>', type='http', auth='user')
    def bpmn_editor(self, definition_id, **kwargs):
        """Serve the BPMN editor page"""
        definition = request.env['bpm.process.definition'].browse(definition_id)
        if not definition.exists():
            return request.not_found()
        
        return request.render('sedco_bpm_engine.bpmn_editor_page', {
            'definition': definition,
        })

    @http.route('/web/bpmn_editor/<int:definition_id>/save', type='json', auth='user')
    def save_bpmn(self, definition_id, xml_content=None, **kwargs):
        """Save BPMN XML content"""
        # For JSON routes, parameters are passed directly as function arguments
        if not xml_content:
            return {'success': False, 'error': 'xml_content parameter is required'}
        
        definition = request.env['bpm.process.definition'].browse(definition_id)
        if definition.exists():
            definition.sudo().write({'bpmn_xml': xml_content})
            return {'success': True}
        return {'success': False, 'error': 'Definition not found'}

    @http.route('/web/bpmn_editor/<int:definition_id>/compile', type='json', auth='user')
    def compile_bpmn(self, definition_id, **kwargs):
        """Compile BPMN to JSON"""
        definition = request.env['bpm.process.definition'].browse(definition_id)
        if definition.exists():
            try:
                definition.sudo().action_compile_bpmn()
                # Return the compiled JSON so the client can display or use it immediately.
                d = definition.sudo()
                return {'success': True, 'definition_json': d.definition_json}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        return {'success': False, 'error': 'Definition not found'}

    @http.route('/web/bpmn_editor_debug/<int:definition_id>', type='json', auth='user')
    def bpmn_editor_debug(self, definition_id, **kwargs):
        """Debug endpoint: return basic info about the definition without rendering templates.
        Use this to confirm the record exists and inspect stored bpmn_xml safely.
        """
        definition = request.env['bpm.process.definition'].sudo().browse(definition_id)
        if not definition.exists():
            return {'exists': False, 'error': 'Definition not found'}
        # return some safe debug info
        xml = definition.bpmn_xml or ''
        return {
            'exists': True,
            'id': definition.id,
            'name': definition.name,
            'bpmn_xml_length': len(xml),
            'bpmn_xml_preview': xml[:1000],
        }
