from odoo import models, fields, api


class Allergy(models.Model):
    _name = "animal.allergy"
    _description = "Animal allergies table"

    name = fields.Char(string="Alergia", required=True)
    description = fields.Text(string="Descripción")
    allergy_type = fields.Selection([
        ("food", "Alimentaria"),
        ("drug", "Medicamento"),
        ("environment", "Ambiental"),
        ("other", "Otra"),
    ], string="Tipo")
    severity = fields.Selection([
        ("low", "Leve"),
        ("medium", "Moderada"),
        ("high", "Grave"),
    ], string="Severidad")
    symptoms = fields.Text(string="Síntomas")
    treatment = fields.Text(string="Tratamiento recomendado")
    animal_ids = fields.Many2many(
        "animal", string="Animales", relation="animal_allergy_rel"
    )
