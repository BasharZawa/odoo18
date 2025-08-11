# -*- coding: utf-8 -*-
# from odoo import http


# class PresalesRequests(http.Controller):
#     @http.route('/presales_requests/presales_requests', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/presales_requests/presales_requests/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('presales_requests.listing', {
#             'root': '/presales_requests/presales_requests',
#             'objects': http.request.env['presales_requests.presales_requests'].search([]),
#         })

#     @http.route('/presales_requests/presales_requests/objects/<model("presales_requests.presales_requests"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('presales_requests.object', {
#             'object': obj
#         })

