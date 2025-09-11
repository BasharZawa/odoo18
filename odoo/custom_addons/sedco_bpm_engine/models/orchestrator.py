from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)

# Build a deterministic de-duplication key by joining parts with '|'.
def _dedup_key(*parts):
    return '|'.join([str(p) for p in parts])

class BpmOrchestratorHelper(models.TransientModel):
    _name = "bpm.orchestrator.helper"
    _description = "BPM Orchestrator Helper"

    # Return approve/reject action URLs for a human task activity.
    def _task_links(self, act):
        base = '/bpm/task/complete'
        return {'approve': f"{base}?act_id={act.id}&decision=approve", 'reject': f"{base}?act_id={act.id}&decision=reject"}

    # Cron entry: pick a batch of 'ready' activities and execute them.
    def cron_tick(self, limit=20):
        Activity = self.env['bpm.activity.instance'].sudo()
        acts = Activity.search([('status','=','ready')], limit=limit, order="id asc")
        for act in acts:
            self._execute_activity(act)

    # Core state machine to progress a single activity instance.
    # Handles node types: start, if, task, sys, pbranch, pwait, wtime, wevent,
    # wcond, end. Updates activity/proc status, enqueues next nodes, and emits
    # outbox/timers/subscriptions as needed. Errors mark the process failed.
    def _execute_activity(self, act):
        proc = act.proc_id.sudo()
        now = fields.Datetime.now()
        if not act.started_at:
            act.write({'started_at': now})
        node_type = act.type

        try:
            if node_type == 'start':
                nxt = (act.data or {}).get('next')
                act.write({'status':'done','ended_at': now})
                self._on_branch_completed(proc, act)
                if nxt: self._enqueue(proc, nxt, '')
            elif node_type == 'if':
                expr = (act.data or {}).get('expression') or 'False'
                res = safe_eval(expr, {'ctx': proc.ctx_json or {}}, nocopy=True)
                nxt = (act.data or {}).get('on_true') if res else (act.data or {}).get('on_false')
                notify = (act.data or {}).get('notify')
                if notify:
                    dedup = _dedup_key(proc.id, act.node_id, 'if_notify')
                    self.env['bpm.outbox'].sudo().create({'kind':'email','dedup_key': dedup,'payload': {'to': notify.get('to'), 'subject': notify.get('subject') or 'IF Notification', 'body': notify.get('body') or '<p>Branch taken.</p>'}})
                act.write({'status':'done','ended_at': now})
                self._on_branch_completed(proc, act)
                if nxt: self._enqueue(proc, nxt, '')
            elif node_type == 'task':
                if act.status != 'waiting':
                    # Resolve assignee from multiple sources
                    assignee_id = (act.data or {}).get('assignee_id')
                    assignee_role_id = (act.data or {}).get('assignee_role_id')
                    
                    # If role is specified, get the current assignee from the role
                    if assignee_role_id and not assignee_id:
                        role = self.env['bpm.role'].sudo().browse(assignee_role_id)
                        if role.exists():
                            assignee_id = role.get_current_assignee().id
                            # Store role assignment in activity instance
                            act.write({'assignee_role_id': assignee_role_id})
                    
                    body = ((act.data or {}).get('label') or 'BPM Task') + '<div style="margin-top:8px">' + \
                           f"<a href='{self._task_links(act)['approve']}' class='btn btn-primary btn-sm'>Approve</a> " + \
                           f"<a href='{self._task_links(act)['reject']}' class='btn btn-secondary btn-sm'>Reject</a></div>"
                    self.env['mail.activity'].sudo().create({
                        'res_model': 'bpm.process.instance','res_id': proc.id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'user_id': assignee_id or self.env.user.id,
                        'note': body,'date_deadline': fields.Date.today() + timedelta(days=2),
                    })
                    act.write({'status':'waiting', 'assignee_id': assignee_id})
            elif node_type == 'sys':
                action = (act.data or {}).get('action')
                dedup = _dedup_key(proc.id, act.node_id, 'sys', action or '')
                self.env['bpm.outbox'].sudo().create({'kind':'sys', 'dedup_key': dedup,'payload': {'action': action, 'ctx': proc.ctx_json or {}}})
                act.write({'status':'done','ended_at': now})
                self._on_branch_completed(proc, act)
                nxt = (act.data or {}).get('next')
                if nxt: self._enqueue(proc, nxt, '')
            elif node_type == 'pbranch':
                branches = (act.data or {}).get('branches') or []
                join_node = (act.data or {}).get('join')
                act.write({'status':'done','ended_at': now})
                self._on_branch_completed(proc, act)
                for nid in branches:
                    self._enqueue(proc, nid, 'branch')
                    created = self.env['bpm.activity.instance'].sudo().search([('proc_id','=',proc.id),('node_id','=',nid)], limit=1)
                    if created:
                        data = created.data or {}; data['join_node'] = join_node; created.write({'data': data})
                if join_node:
                    join = self.env['bpm.activity.instance'].sudo().search([('proc_id','=',proc.id),('node_id','=',join_node)], limit=1)
                    if not join:
                        self.env['bpm.activity.instance'].sudo().create({'proc_id': proc.id, 'node_id': join_node, 'type':'pwait', 'status':'waiting', 'data': {'remaining': len(branches), 'next': (act.data or {}).get('next')}})
                    else:
                        join.write({'data': {'remaining': len(branches), 'next': (act.data or {}).get('next')}, 'status':'waiting'})
            elif node_type == 'pwait':
                remaining = (act.data or {}).get('remaining', 0)
                if remaining <= 0:
                    act.write({'status':'done','ended_at': now})
                    nxt = (act.data or {}).get('next')
                    if nxt: self._enqueue(proc, nxt, '')
            elif node_type == 'wtime':
                delay_seconds = int((act.data or {}).get('delay_seconds', 0))
                due = now + timedelta(seconds=delay_seconds)
                self.env['bpm.timer'].sudo().create({'proc_id': proc.id, 'node_id': act.node_id, 'due_at': due, 'payload': {'next': (act.data or {}).get('next')}})
                act.write({'status':'waiting'})
            elif node_type == 'wevent':
                ev = (act.data or {}).get('event_name'); corr = (act.data or {}).get('correlation_key')
                self.env['bpm.event.subscription'].sudo().create({'proc_id': proc.id, 'node_id': act.node_id, 'event_name': ev, 'correlation_key': corr})
                act.write({'status':'waiting'})
            elif node_type == 'wcond':
                expr = (act.data or {}).get('predicate') or 'False'
                res = safe_eval(expr, {'ctx': proc.ctx_json or {}}, nocopy=True)
                if res:
                    act.write({'status':'done','ended_at': now})
                    nxt = (act.data or {}).get('next')
                    if nxt: self._enqueue(proc, nxt, '')
                else:
                    act.write({'status':'waiting'})
            elif node_type == 'end':
                proc.mark_done()
                act.write({'status':'done','ended_at': now})
                self._on_branch_completed(proc, act)
            else:
                raise UserError(_("Unknown activity type: %s") % node_type)
        except Exception as e:
            act.write({'status':'failed'})
            _logger.exception('BPM activity failed: proc=%s node=%s', proc.id, act.node_id)
            proc.mark_failed(str(e))
            self.env.cr.commit()

    # Decrement join counter when a parallel branch finishes and release join.
    # If the pwait node reaches zero remaining branches, mark it done and enqueue next.
    def _on_branch_completed(self, proc, act):
        join_node = (act.data or {}).get('join_node')
        if not join_node: return
        join = self.env['bpm.activity.instance'].sudo().search([('proc_id','=',proc.id),('node_id','=',join_node),('type','=','pwait')], limit=1)
        if not join: return
        data = join.data or {}; remaining = int(data.get('remaining', 0))
        if remaining > 0: remaining -= 1; data['remaining'] = remaining; join.write({'data': data})
        if remaining <= 0 and join.status == 'waiting':
            join.write({'status':'done','ended_at': fields.Datetime.now()})
            nxt = (join.data or {}).get('next')
            if nxt: self._enqueue(proc, nxt, '')

    # Create a new activity instance for the given node in 'ready' state.
    def _enqueue(self, proc, node_id, kind):
        self.env['bpm.activity.instance'].sudo().create({'proc_id': proc.id, 'node_id': node_id, 'type': self._infer_type(proc, node_id), 'status':'ready', 'data': {}})

    # Look up the node type from the process definition JSON; fallback to 'sys'.
    def _infer_type(self, proc, node_id):
        import json
        data = json.loads(proc.definition_id.definition_json or '{}')
        for n in data.get('nodes', []):
            if n.get('id') == node_id: return n.get('type')
        return 'sys'

    # Cron entry: dispatch pending outbox messages via bpm.outbox model.
    def cron_dispatch_outbox(self):
        return self.env['bpm.outbox'].sudo().dispatch_pending()

    # Cron entry: fire due timers by enqueuing their next nodes and marking fired.
    def cron_fire_due_timers(self, limit=100):
        Timer = self.env['bpm.timer'].sudo()
        due = Timer.search([('status','=','scheduled'),('due_at','<=', fields.Datetime.now())], limit=limit, order='due_at asc')
        for t in due:
            nxt = (t.payload or {}).get('next')
            if nxt and t.proc_id: self._enqueue(t.proc_id, nxt, '')
            t.write({'status':'fired'})
