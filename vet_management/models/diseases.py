from odoo import models, fields, api

class Disease(models.Model):
    _name = "animal.disease"
    _description = "Animal diseases table"

    name = fields.Char(string="Surgerie", required=True)
    observations = fields.Text(string="Observations")
