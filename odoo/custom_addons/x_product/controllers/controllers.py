# -*- coding: utf-8 -*-
# from odoo import http


# class XAccounting(http.Controller):
#     @http.route('/x__accounting/x__accounting', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/x__accounting/x__accounting/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('x__accounting.listing', {
#             'root': '/x__accounting/x__accounting',
#             'objects': http.request.env['x__accounting.x__accounting'].search([]),
#         })

#     @http.route('/x__accounting/x__accounting/objects/<model("x__accounting.x__accounting"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('x__accounting.object', {
#             'object': obj
#         })

