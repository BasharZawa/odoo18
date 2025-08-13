# -*- coding: utf-8 -*-
# from odoo import http


# class QuoteManagement(http.Controller):
#     @http.route('/quote_management/quote_management', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/quote_management/quote_management/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('quote_management.listing', {
#             'root': '/quote_management/quote_management',
#             'objects': http.request.env['quote_management.quote_management'].search([]),
#         })

#     @http.route('/quote_management/quote_management/objects/<model("quote_management.quote_management"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('quote_management.object', {
#             'object': obj
#         })

