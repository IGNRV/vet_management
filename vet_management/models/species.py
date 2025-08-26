from odoo import models, fields, api 


class Specie(models.Model):
    _name = "animal.specie"
    _description = "Animals species table"

    name = fields.Char(string="Especie")
    characteristics = fields.Text(string="Características")
