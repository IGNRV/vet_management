from odoo import models, fields, api

class Insurance(models.Model):
    _name = "animal.insurance"
    _description = "Animals insurances table"

    name = fields.Char(string="Seguro", required=True)
    characteristics = fields.Text(string="Características")
    cost = fields.Integer(string="Costo")
