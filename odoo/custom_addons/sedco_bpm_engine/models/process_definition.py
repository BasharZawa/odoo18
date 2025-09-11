from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProcessDefinition(models.Model):
    _name = "process.definition"
    _description = "BPM Process Definition"
    _rec_name = "name"

    name = fields.Char(required=True)
    key = fields.Char(required=True, help="Unique key for this process across versions")
    version = fields.Integer(default=1, required=True)
    is_active = fields.Boolean(default=True)
    definition_json = fields.Text(help="Process definition in JSON DSL (nodes, transitions, options)")
    note = fields.Html()
    bpmn_xml = fields.Text(help="Raw BPMN 2.0 XML for this process (edited via the BPMN Modeler).")
    
    # Activity relationship
    activity_ids = fields.One2many("process.definition.activity", "definition_id", string="Activities")
    activity_count = fields.Integer(string="Activity Count", compute="_compute_activity_count")

    model_id = fields.Many2one('ir.model', string='Bind to Model')
    auto_apply = fields.Boolean(string='Auto-apply on Create', default=False)
    start_on_create_domain = fields.Char(string='Creation Domain', help="Python domain string to auto-start, e.g. [('type','=','Discount')]")

    _sql_constraints = [('key_version_unique', 'unique(key, version)', 'Key+Version must be unique.')]

    @api.depends('activity_ids')
    def _compute_activity_count(self):
        for definition in self:
            definition.activity_count = len(definition.activity_ids)

    def compile_definition(self):
        import json
        for rec in self:
            if not rec.definition_json: raise ValueError(_("Definition JSON is required"))
            try:
                data = json.loads(rec.definition_json)
            except Exception as e:
                raise ValueError(_("Invalid JSON: %s") % e)
            if 'nodes' not in data or not isinstance(data['nodes'], list):
                raise ValueError(_("Definition requires a 'nodes' list."))
        return True

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            try:
                if rec.bpmn_xml:
                    rec.action_compile_bpmn()
            except Exception:
                pass
            rec._ensure_activation_binder()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if 'bpmn_xml' in vals:
            try:
                self.action_compile_bpmn()
            except Exception:
                pass
        if any(k in vals for k in ['is_active','model_id','auto_apply','start_on_create_domain']):
            for rec in self:
                rec._ensure_activation_binder()
        return res

    def _ensure_activation_binder(self):
        for rec in self:
            rec._remove_activation_binder()
            if rec.is_active and rec.auto_apply and rec.model_id:
                srv = self.env['ir.actions.server'].sudo().create({
                    'name': f'BPM Start {rec.key} v{rec.version}',
                    'model_id': rec.model_id.id,
                    'state': 'code',
                    'code': f"env['process.definition'].browse({rec.id}).action_start_for_record(record)"  # Fixed typo: bmp -> bpm
                })
                domain = rec.start_on_create_domain or '[]'
                # Use server_action_ids (Many2many) instead of action_server_id
                self.env['base.automation'].sudo().create({
                    'name': f'Auto-start {rec.key} v{rec.version}',
                    'model_id': rec.model_id.id,
                    'trigger': 'on_create',
                    'active': True,
                    'filter_domain': domain
                })

    def _remove_activation_binder(self):
        for rec in self:
            self.env['base.automation'].sudo().search([('name','=', f'Auto-start {rec.key} v{rec.version}')]).unlink()
            self.env['ir.actions.server'].sudo().search([('name','=', f'BPM Start {rec.key} v{rec.version}')]).unlink()

    def action_start_test(self):
        import json
        self.ensure_one()
        proc = self.env['process.instance'].sudo().create({
            'definition_id': self.id,
            'business_key': 'TEST-%s' % self.id,
            'ctx_json': {'proc_id': 0},
        })
        ctx = proc.ctx_json or {}; ctx['proc_id'] = proc.id; proc.write({'ctx_json': ctx})
        data = json.loads(self.definition_json or '{}')
        start = next((n for n in data.get('nodes', []) if n.get('type') == 'start'), None)
        if not start: raise ValueError("No start node in definition")
        self.env['activity.instance'].sudo().create({
            'proc_id': proc.id, 'node_id': start.get('id'), 'type': 'start', 'status':'ready', 'data': start
        })
        proc.post_note("Started test instance.")
        return True

    def action_start_for_record(self, record):
        import json as _json
        self.ensure_one()
        ctx = {'model': record._name, 'res_id': record.id, 'proc_id': 0}
        proc = self.env['process.instance'].sudo().create({
            'definition_id': self.id,
            'business_key': f"{record._name},{record.id}",
            'ctx_json': ctx,
        })
        ctx['proc_id'] = proc.id; proc.write({'ctx_json': ctx})
        data = _json.loads(self.definition_json or '{}')
        start = next((n for n in data.get('nodes', []) if n.get('type') == 'start'), None)
        if not start: raise ValueError("No start node in definition")
        self.env['activity.instance'].sudo().create({
            'proc_id': proc.id, 'node_id': start.get('id'), 'type': 'start', 'status':'ready', 'data': start
        })
        proc.post_note("Process auto-started for %s(%s)" % (record._name, record.id))
        return True

    def action_compile_bpmn(self):
        import xml.etree.ElementTree as ET, json
        self.ensure_one()
        if not self.bpmn_xml: raise ValueError(_("No BPMN XML to compile."))
        ns = {'bpmn':'http://www.omg.org/spec/BPMN/20100524/MODEL','bpmndi':'http://www.omg.org/spec/BPMN/20100524/DI','dc':'http://www.omg.org/spec/DD/20100524/DC','di':'http://www.omg.org/spec/DD/20100524/DI','sedco':'https://sedco.com/bpmn/extensions'}
        root = ET.fromstring(self.bpmn_xml)

        flows = {}
        for sf in root.findall('.//bpmn:sequenceFlow', ns):
            sid = sf.get('id'); src = sf.get('sourceRef'); tgt = sf.get('targetRef')
            cond_el = sf.find('bpmn:conditionExpression', ns)
            cond = cond_el.text.strip() if cond_el is not None and cond_el.text else None
            flows[sid] = {'id': sid, 'source': src, 'target': tgt, 'condition': cond}

        outgoing, incoming = {}, {}
        for f in flows.values():
            outgoing.setdefault(f['source'], []).append(f)
            incoming.setdefault(f['target'], []).append(f)

        def node_json(nid, ntype, extra=None):
            d = {'id': nid, 'type': ntype}
            if extra: d.update(extra)
            return d

        nodes, id2node = [], {}

        def ext_value(el, tag, attr):
            ee = el.find('bpmn:extensionElements', ns)
            if ee is None: return None
            ext = ee.find(f"sedco:{tag}", ns)
            if ext is None: return None
            return ext.get(attr)

        for e in root.findall('.//bpmn:startEvent', ns):
            nid = e.get('id'); nx = outgoing.get(nid, [])
            n = node_json(nid, 'start', {'next': nx[0]['target'] if nx else None})
            nodes.append(n); id2node[nid] = n

        for e in root.findall('.//bpmn:endEvent', ns):
            nid = e.get('id'); n = node_json(nid, 'end')
            nodes.append(n); id2node[nid] = n

        for e in root.findall('.//bpmn:userTask', ns):
            nid = e.get('id')
            assignee = ext_value(e, 'assignment', 'value')
            label = e.get('name') or 'Task'
            nx = outgoing.get(nid, [])
            approve_t = ext_value(e, 'approve', 'target')
            reject_t = ext_value(e, 'reject', 'target')
            n = node_json(nid, 'task', {'label': label,'assignee_id': int(assignee) if assignee and assignee.isdigit() else None,'next': nx[0]['target'] if nx else None,'next_approve': approve_t,'next_reject': reject_t})
            nodes.append(n); id2node[nid] = n

        for e in root.findall('.//bpmn:serviceTask', ns):
            nid = e.get('id'); action = ext_value(e, 'action', 'dotted'); nx = outgoing.get(nid, [])
            n = node_json(nid, 'sys', {'action': action, 'next': nx[0]['target'] if nx else None})
            nodes.append(n); id2node[nid] = n

        for e in root.findall('.//bpmn:exclusiveGateway', ns):
            nid = e.get('id'); outs = outgoing.get(nid, [])
            on_true = on_false = expr = None
            if outs:
                conds = [o for o in outs if o.get('condition')]
                if conds:
                    expr = conds[0]['condition']; on_true = conds[0]['target']
                    non = [o for o in outs if o is not conds[0]]
                    on_false = (non[0]['target'] if non else None)
                else:
                    on_true = outs[0]['target']; on_false = outs[1]['target'] if len(outs)>1 else None
            n = node_json(nid, 'if', {'expression': expr or 'True', 'on_true': on_true, 'on_false': on_false})
            nodes.append(n); id2node[nid] = n

        for e in root.findall('.//bpmn:parallelGateway', ns):
            nid = e.get('id'); outs = outgoing.get(nid, []); incs = incoming.get(nid, [])
            if len(outs) > 1:
                n = node_json(nid, 'pbranch', {'branches': [o['target'] for o in outs], 'join': None, 'next': None})
            elif len(incs) > 1:
                nx = outs[0]['target'] if outs else None
                n = node_json(nid, 'pwait', {'next': nx})
            else:
                n = node_json(nid, 'pbranch', {'branches': [o['target'] for o in outs]})
            nodes.append(n); id2node[nid] = n

        for e in root.findall('.//bpmn:intermediateCatchEvent', ns):
            nid = e.get('id')
            if e.find('bpmn:timerEventDefinition', ns) is not None:
                delay = ext_value(e, 'timer', 'seconds'); nx = outgoing.get(nid, [])
                n = node_json(nid, 'wtime', {'delay_seconds': int(delay) if delay and delay.isdigit() else 0, 'next': nx[0]['target'] if nx else None})
            elif e.find('bpmn:messageEventDefinition', ns) is not None:
                ev = ext_value(e, 'message', 'name') or 'event'; corr = ext_value(e, 'message', 'correlation') or 'id'; nx = outgoing.get(nid, [])
                n = node_json(nid, 'wevent', {'event_name': ev, 'correlation_key': corr, 'next': nx[0]['target'] if nx else None})
            else:
                continue
            nodes.append(n); id2node[nid] = n

        for n in nodes:
            if n['type'] == 'pbranch':
                targets = n.get('branches', [])
                for t in targets:
                    outs = outgoing.get(t, [])
                    if outs:
                        maybe = id2node.get(outs[0]['target'])
                        if maybe and maybe.get('type') == 'pwait':
                            n['join'] = maybe['id']; break

        self.definition_json = json.dumps({'nodes': nodes}, indent=2)
        return True

    def action_save_bpmn_xml(self, xml_content):
        """Save BPMN XML content - used by the editor widget"""
        self.ensure_one()
        self.write({'bpmn_xml': xml_content})
        return True

    def action_compile_bpmn_from_xml(self, xml_content):
        """Save and compile BPMN XML to JSON - used by the editor widget"""
        self.ensure_one()
        self.write({'bpmn_xml': xml_content})
        self.action_compile_bpmn()
        return True

    def action_open_bpmn_editor(self):
        """Open a popup with the BPMN editor"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/bpmn_editor/{self.id}',
            'target': 'new',
        }

    def action_generate_definition_from_activities(self):
        """Generate JSON definition from the activity records"""
        self.ensure_one()
        if not self.activity_ids:
            raise UserError(_("No activities defined. Please add activities first."))
        
        nodes = []
        for activity in self.activity_ids:
            nodes.append(activity.to_json_node())

        import json
        self.definition_json = json.dumps({'nodes': nodes}, indent=2)
        return True

    def action_sync_activities_from_json(self):
        """Sync activities from existing JSON definition (backward compatibility)"""
        self.ensure_one()
        if not self.definition_json:
            raise UserError(_("No JSON definition found to sync from."))
        
        import json
        try:
            data = json.loads(self.definition_json)
            nodes = data.get('nodes', [])
        except Exception as e:
            raise UserError(_("Invalid JSON definition: %s") % str(e))
        
        # Clear existing activities
        self.activity_ids.unlink()
        
        # Create activities from JSON nodes
        activity_vals = []
        for i, node in enumerate(nodes):
            vals = {
                'definition_id': self.id,
                'sequence': (i + 1) * 10,
                'node_id': node.get('id', f'Node_{i}'),
                'name': node.get('label', node.get('id', f'Activity {i+1}')),
                'type': node.get('type', 'task'),
                'custom_data': {k: v for k, v in node.items() if k not in ['id', 'type', 'label']}
            }
            
            # Map specific fields based on type
            if node.get('type') == 'task':
                if 'assignee_id' in node:
                    vals['assignee_type'] = 'static'
                    vals['assignee_id'] = node['assignee_id']
                elif 'assignee_resolver' in node:
                    vals['assignee_type'] = 'resolver' 
                    vals['assignee_resolver'] = node['assignee_resolver']
                    
            elif node.get('type') == 'sys':
                vals['service_action'] = node.get('action')
                
            elif node.get('type') == 'if':
                vals['condition_expression'] = node.get('expression')
                
            elif node.get('type') == 'wtime':
                vals['total_delay_seconds'] = node.get('delay_seconds', 0)
                
            elif node.get('type') == 'wevent':
                vals['event_name'] = node.get('event_name')
                vals['correlation_key'] = node.get('correlation_key')
            
            activity_vals.append(vals)
        
        # Create all activities
        activities = self.env['process.definition.activity'].create(activity_vals)
        
        # Second pass to set relationships (after all activities are created)
        for activity, node in zip(activities, nodes):
            updates = {}
            
            # Find next activity
            if 'next' in node:
                next_activity = activities.filtered(lambda a: a.node_id == node['next'])
                if next_activity:
                    updates['next_activity_id'] = next_activity[0].id
            
            # Task-specific relationships
            if node.get('type') == 'task':
                if 'next_approve' in node:
                    approve_activity = activities.filtered(lambda a: a.node_id == node['next_approve'])
                    if approve_activity:
                        updates['next_approve_activity_id'] = approve_activity[0].id
                        
                if 'next_reject' in node:
                    reject_activity = activities.filtered(lambda a: a.node_id == node['next_reject'])
                    if reject_activity:
                        updates['next_reject_activity_id'] = reject_activity[0].id
            
            # Gateway relationships
            elif node.get('type') == 'if':
                if 'on_true' in node:
                    true_activity = activities.filtered(lambda a: a.node_id == node['on_true'])
                    if true_activity:
                        updates['true_activity_id'] = true_activity[0].id
                        
                if 'on_false' in node:
                    false_activity = activities.filtered(lambda a: a.node_id == node['on_false'])
                    if false_activity:
                        updates['false_activity_id'] = false_activity[0].id
            
            # Parallel gateway relationships
            elif node.get('type') == 'pbranch':
                if 'branches' in node:
                    branch_activities = activities.filtered(lambda a: a.node_id in node['branches'])
                    if branch_activities:
                        updates['branch_activity_ids'] = [(6, 0, branch_activities.ids)]
                        
                if 'join' in node:
                    join_activity = activities.filtered(lambda a: a.node_id == node['join'])
                    if join_activity:
                        updates['join_activity_id'] = join_activity[0].id
            
            if updates:
                activity.write(updates)
        
        return True

    def action_open_activities(self):
        """Open the activities view for this definition"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Activities - {self.name}',
            'res_model': 'process.definition.activity',
            'view_mode': 'tree,form',
            'domain': [('definition_id', '=', self.id)],
            'context': {'default_definition_id': self.id},
            'target': 'current',
        }
