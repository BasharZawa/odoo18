# -*- coding: utf-8 -*-
# from odoo import http


# class CustomerManagementEpt(http.Controller):
#     @http.route('/customer_management_ept/customer_management_ept', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/customer_management_ept/customer_management_ept/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('customer_management_ept.listing', {
#             'root': '/customer_management_ept/customer_management_ept',
#             'objects': http.request.env['customer_management_ept.customer_management_ept'].search([]),
#         })

#     @http.route('/customer_management_ept/customer_management_ept/objects/<model("customer_management_ept.customer_management_ept"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('customer_management_ept.object', {
#             'object': obj
#         })

