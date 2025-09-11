from odoo import http, fields
from odoo.http import request
import json

class BpmApiController(http.Controller):

    @http.route('/bpm/start/<string:key>', type='json', auth='user', methods=['POST'])
    def start_process(self, key, **kwargs):
        env = request.env
        defn = env['process.definition'].sudo().search([('key','=', key), ('is_active','=', True)], order="version desc", limit=1)
        if not defn:
            return {'ok': False, 'error': 'Definition not found'}
        proc = env['process.instance'].sudo().create({
            'definition_id': defn.id,
            'business_key': kwargs.get('business_key'),
            'ctx_json': kwargs.get('ctx') or {},
        })
        ctx = proc.ctx_json or {}; ctx['proc_id'] = proc.id; proc.write({'ctx_json': ctx})
        import json as _json
        data = _json.loads(defn.definition_json or '{}')
        start = next((n for n in data.get('nodes', []) if n.get('type') == 'start'), None)
        if not start:
            return {'ok': False, 'error': 'No start node in definition'}
        request.env['activity.instance'].sudo().create({
            'proc_id': proc.id, 'node_id': start.get('id'), 'type': 'start', 'status':'ready', 'data': start
        })
        return {'ok': True, 'proc_id': proc.id}

    @http.route('/bpm/event', type='json', auth='user', methods=['POST'])
    def push_event(self, **payload):
        env = request.env
        event_name = payload.get('event_name'); correlation_key = payload.get('correlation_key')
        subs = env['event.subscription'].sudo().search([('event_name','=', event_name),('correlation_key','=', correlation_key),('status','=','active')])
        for s in subs:
            request.env['orchestrator.helper'].sudo()._enqueue(s.proc_id, payload.get('next_node') or 'end', '')
            s.write({'status':'consumed'})
        return {'ok': True, 'matched': len(subs)}

    @http.route('/bpm/task/complete', type='http', auth='user', methods=['GET'])
    def complete_task(self, **kw):
        act_id = int(kw.get('act_id', 0)); decision = kw.get('decision', 'approve')
        Act = request.env['activity.instance'].sudo(); act = Act.browse(act_id)
        if not act.exists():
            return request.make_response('Task not found', [('Content-Type','text/plain')], 404)
        proc = act.proc_id
        act.write({'status':'done', 'ended_at': fields.Datetime.now()})
        data = act.data or {}
        nxt = data.get('next_approve') if decision == 'approve' else data.get('next_reject') or data.get('next')
        request.env['orchestrator.helper'].sudo()._on_branch_completed(proc, act)
        if nxt:
            request.env['orchestrator.helper'].sudo()._enqueue(proc, nxt, '')
        return request.redirect(f'/web#id={proc.id}&model=process.instance&view_type=form')

    @http.route('/bpm/health', type='json', auth='user', methods=['GET'])
    def health(self, **kw):
        env = request.env
        mods = env['ir.module.module'].sudo().search_read([('name','in',['base_automation','mail'])], ['name','state'])
        return {'ok': True, 'modules': {m['name']: m['state'] for m in mods}}
