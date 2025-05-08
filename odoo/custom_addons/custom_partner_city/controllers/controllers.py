from odoo import http


class CustomPartnerCity(http.Controller):
    @http.route('/custom_partner_city/indexs', auth='public', method =['GET'], website=True)
    def index(self, **kw):
        return "Welcome to Custom Partner City!"

    @http.route('/custom_partner_city/objects', auth='public', website=True)
    def list(self, **kw):
        objects = http.request.env['custom_partner_city.custom_partner_city'].search([])
        return http.request.render('custom_partner_city.listing', {
            'root': '/custom_partner_city',
            'objects': objects,
        })

    @http.route('/custom_partner_city/objects/<model("custom_partner_city.custom_partner_city"):obj>', auth='public', website=True)
    def object(self, obj, **kw):
        return http.request.render('custom_partner_city.object', {
            'object': obj
        })

