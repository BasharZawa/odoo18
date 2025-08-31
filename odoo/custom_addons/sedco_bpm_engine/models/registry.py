from odoo import models, fields, _
from odoo.exceptions import UserError

class BpmRegistry(models.Model):
    _name = "bpm.registry"
    _description = "BPM Whitelist Registry"

    name = fields.Char(required=True)
    dotted_path = fields.Char(required=True, help="Python dotted path to a callable(env, ctx)")
    kind = fields.Selection([('system_action','System Action'),('assignee','Assignee Resolver')], required=True)

    _sql_constraints = [('dotted_unique', 'unique(dotted_path, kind)', 'Each callable must be unique per kind.')]

    def call(self, dotted_path, ctx):
        rec = self.search([('dotted_path','=',dotted_path)], limit=1)
        if not rec:
            raise UserError(_("Not in whitelist: %s") % dotted_path)
        module_name, func_name = dotted_path.rsplit('.', 1)
        mod = __import__(module_name, fromlist=[func_name])
        fn = getattr(mod, func_name)
        return fn(self.env, ctx)
