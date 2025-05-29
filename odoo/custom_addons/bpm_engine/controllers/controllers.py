# -*- coding: utf-8 -*-
# from odoo import http


# class BpmEngine(http.Controller):
#     @http.route('/bpm_engine/bpm_engine', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bpm_engine/bpm_engine/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('bpm_engine.listing', {
#             'root': '/bpm_engine/bpm_engine',
#             'objects': http.request.env['bpm_engine.bpm_engine'].search([]),
#         })

#     @http.route('/bpm_engine/bpm_engine/objects/<model("bpm_engine.bpm_engine"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bpm_engine.object', {
#             'object': obj
#         })

