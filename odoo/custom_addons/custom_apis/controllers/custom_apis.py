# -*- coding: utf-8 -*-
from odoo import http


class custom_apis(http.Controller):
    @http.route('/custom_apis/custom_apis', auth='public')
    def index(self, **kw):
        return "Hello, world"

#     @http.route('/custom_apis/custom_apis/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_apis.listing', {
#             'root': '/custom_apis/custom_apis',
#             'objects': http.request.env['custom_apis.custom_apis'].search([]),
#         })

#     @http.route('/custom_apis/custom_apis/objects/<model("custom_apis.custom_apis"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_apis.object', {
#             'object': obj
#         })

