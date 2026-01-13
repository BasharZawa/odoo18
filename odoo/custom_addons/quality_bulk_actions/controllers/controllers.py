# -*- coding: utf-8 -*-
# from odoo import http


# class QualityBulkActions(http.Controller):
#     @http.route('/quality_bulk_actions/quality_bulk_actions', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/quality_bulk_actions/quality_bulk_actions/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('quality_bulk_actions.listing', {
#             'root': '/quality_bulk_actions/quality_bulk_actions',
#             'objects': http.request.env['quality_bulk_actions.quality_bulk_actions'].search([]),
#         })

#     @http.route('/quality_bulk_actions/quality_bulk_actions/objects/<model("quality_bulk_actions.quality_bulk_actions"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('quality_bulk_actions.object', {
#             'object': obj
#         })

