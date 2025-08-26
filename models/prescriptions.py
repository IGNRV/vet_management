from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Prescription(models.Model):
    _name = "animal.prescription"
    _description = "Recetas veterinarias"
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
        ondelete='cascade',
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

    # Datos de la receta
    date = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    doctor_name = fields.Char(string="Nombre M. Veterinario/a", tracking=True)
    doctor_rut = fields.Char(string="RUT (médico)", tracking=True)

    diagnosis = fields.Text(string="Diagnóstico")
    rp = fields.Text(string="Rp (prescripción)")  # cuerpo de receta
    indications = fields.Text(string="Indicaciones al propietario")
    duration_days = fields.Integer(string="Duración (días)")
    next_control = fields.Date(string="Próximo control")
    notes = fields.Text(string="Notas internas")

    # Firmas
    doctor_signature = fields.Binary(string="Firma Médico/a")
    owner_signature = fields.Binary(string="Firma Propietario/a")

    # Estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('issued', 'Emitida/Firmada'),
        ('cancelled', 'Cancelada'),
    ], string="Estado", default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'Nuevo') == 'Nuevo':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('animal.prescription.sequence') or 'Nuevo'
        return super().create(vals)

    @api.onchange('animal_id')
    def _onchange_animal_id_set_doctor(self):
        """Si el animal tiene 'médico tratante', sugerirlo en la receta."""
        for rec in self:
            if rec.animal_id and rec.animal_id.treating_doctor and not rec.doctor_name:
                rec.doctor_name = rec.animal_id.treating_doctor

    # Acciones
    def action_issue(self):
        """Marcar como emitida. (Opcional) Validar que haya contenido en Rp."""
        for rec in self:
            if not (rec.rp or rec.indications):
                raise UserError(_("La receta no tiene contenido. Completa 'Rp' o 'Indicaciones'."))
            rec.state = 'issued'
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True

    def name_get(self):
        res = []
        for rec in self:
            label = rec.sequence or _("Receta")
            if rec.animal_id:
                label = "%s - %s" % (label, rec.animal_id.name)
            res.append((rec.id, label))
        return res
