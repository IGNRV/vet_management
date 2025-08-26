from odoo import models, fields, api

class Tag(models.Model):
    _name = "animal.tag"
    _description = "Animal tags table"

    name = fields.Char(string="Etiqueta", required=True)
    description = fields.Text(string="Descripción")
    color = fields.Integer(string="Color")
