from odoo import fields, models, api

class Visit(models.Model):
    _name = "animal.visit"
    _description = "Animals visits table"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc"

    animal_id = fields.Many2one('animal', string='Animal', required=True)  # Campo de relación Many2one con animal
    date = fields.Datetime(string="Fecha", required=True)
    name = fields.Char(related="animal_id.name", string="Animal", required=True, readonly=False)
    owner = fields.Many2one(related="animal_id.owner", string="Dueño", readonly=True, store=True)
    sex = fields.Selection(related="animal_id.sex", string="Sexo", readonly=True, store=True)
    breed = fields.Many2one(related="animal_id.breed", string="Raza", readonly=True, store=True)
    specie = fields.Many2one(related="animal_id.species", string="Especie", readonly=True, store=True)

    # ---- CAMPO(S) HISTÓRICOS (se mantienen por compatibilidad) ----
    reason = fields.Text(string="Razón")
    suggested_treatment = fields.Text(string="Tratamiento sugerido")
    observations = fields.Text(string="Observaciones")

    # ---- NUEVOS CAMPOS SOLICITADOS ----
    consultation_reason = fields.Text(string="Motivo de consulta")
    anamnesis = fields.Text(string="Anamnesis Remota y Actual")
    clinical_exam = fields.Text(string="Examen Clínico")
    prediagnoses = fields.Text(string="Prediagnósticos")
    treatment = fields.Text(string="Tratamiento")
    rp = fields.Text(string="Rp")
    follow_up = fields.Text(string="Control")

    # ---- NUEVO CAMPO: MÉDICO RESPONSABLE ----
    doctor = fields.Char(string="Dr/Dra")  # mostrado a la derecha de "Fecha" en el formulario

    sequence = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: 'Nuevo'
    )

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'Nuevo') == 'Nuevo':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('animal.visit.sequence') or 'Nuevo'
        return super(Visit, self).create(vals)