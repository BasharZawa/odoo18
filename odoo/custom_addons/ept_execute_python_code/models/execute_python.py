from odoo import models, fields, api, _
from odoo.tools.translate import _
from odoo.exceptions import UserError


class emipro_execute_python(models.Model):
    _name = "emipro.execute.python"
    _description = "Execute Python Code"
    
    name = fields.Char(string='Name', size=1024, required=True)
    code = fields.Text(string='Python Code', required=True)
    result = fields.Text(string='Result', readonly=True)
        
    def execute_code(self):
        localdict = {'self':self, 'user_obj':self.env.user}
        for obj in self:  # .browse(self._ids):
            try :
                exec(obj.code, localdict)
                if localdict.get('result', False):
                    self.write({'result':localdict['result']})
                else : 
                    self.write({'result':''})
            except Exception as e:
                raise UserError('Python code is not able to run ! message : %s' % (e))
        
        return True
    
