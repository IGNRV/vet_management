from odoo import models, fields, api


class Consent(models.Model):
    _name = "animal.consent"
    _description = "Consentimientos informados"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc, sequence desc"

    # Identificador / referencia
    sequence = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: 'Nuevo',
        tracking=True
    )

    # Enlaces
    animal_id = fields.Many2one(
        'animal',
        string='Animal',
        required=True,
        tracking=True,
    )
    owner_id = fields.Many2one(
        related='animal_id.owner',
        string="Dueño",
        store=True,
        readonly=True
    )

    # Datos del paciente (solo lectura para filtros/listados e impresión)
    specie_id = fields.Many2one(
        related='animal_id.species',
        string='Especie',
        store=True,
        readonly=True
    )
    breed_id = fields.Many2one(
        related='animal_id.breed',
        string='Raza',
        store=True,
        readonly=True
    )
    sex = fields.Selection(
        related='animal_id.sex',
        string='Sexo',
        store=True,
        readonly=True
    )
    microchip_number = fields.Char(
        related='animal_id.microchip_number',
        string="N° de microchip",
        store=True,
        readonly=True
    )

    # Datos del consentimiento
    date = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    consent_type = fields.Selection([
        ('anesthesia', 'Anestesia / Sedación'),
        ('surgery', 'Cirugía / Procedimiento Quirúrgico'),
        ('procedure', 'Procedimiento / Examen'),
        ('hospitalization', 'Hospitalización'),
        ('euthanasia', 'Eutanasia'),
        ('treatment', 'Tratamiento'),
        ('other', 'Otro'),
    ], string="Tipo de consentimiento", tracking=True)

    consent_title = fields.Char(string="Título (impresión)", help="Título que saldrá en el PDF (opcional). Si lo dejas vacío, se usará el tipo de consentimiento.")
    description = fields.Text(string="Descripción del procedimiento / motivo")
    risks = fields.Text(string="Riesgos y posibles complicaciones")
    post_instructions = fields.Text(string="Instrucciones postprocedimiento")

    # Firmas y datos de participantes
    doctor_name = fields.Char(string="Nombre M. Veterinario/a")
    doctor_rut = fields.Char(string="RUT (médico)")
    doctor_signature = fields.Binary(string="Firma Médico/a")
    owner_signature = fields.Binary(string="Firma Propietario/a")

    # Estado del consentimiento
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('signed', 'Firmado'),
        ('cancelled', 'Cancelado'),
    ], string="Estado", default='draft', tracking=True)

    # Auxiliares
    notes = fields.Text(string="Notas internas")

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'Nuevo') == 'Nuevo':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('animal.consent.sequence') or 'Nuevo'
        return super(Consent, self).create(vals)

    @api.onchange('animal_id')
    def _onchange_animal_id_set_doctor(self):
        """
        Si el animal tiene 'médico tratante', sugerirlo como doctor_name.
        """
        for rec in self:
            if rec.animal_id and rec.animal_id.treating_doctor and not rec.doctor_name:
                rec.doctor_name = rec.animal_id.treating_doctor

    # Acciones de estado
    def action_confirm(self):
        self.write({'state': 'signed'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True
