# -*- coding: utf-8 -*-
# from odoo import http


# class Vet(http.Controller):
#     @http.route('/vet/vet', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vet/vet/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('vet.listing', {
#             'root': '/vet/vet',
#             'objects': http.request.env['vet.vet'].search([]),
#         })

#     @http.route('/vet/vet/objects/<model("vet.vet"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vet.object', {
#             'object': obj
#         })

