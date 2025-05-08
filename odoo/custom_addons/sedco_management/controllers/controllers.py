# -*- coding: utf-8 -*-
# from odoo import http


# class SedcoManagement(http.Controller):
#     @http.route('/sedco_management/sedco_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sedco_management/sedco_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sedco_management.listing', {
#             'root': '/sedco_management/sedco_management',
#             'objects': http.request.env['sedco_management.sedco_management'].search([]),
#         })

#     @http.route('/sedco_management/sedco_management/objects/<model("sedco_management.sedco_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sedco_management.object', {
#             'object': obj
#         })

