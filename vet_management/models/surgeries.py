from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Surgery(models.Model):
    _name = "animal.surgery"
    _description = "Catálogo de cirugías"

    # === Datos de catálogo ===
    name = fields.Char(string="Cirugía", required=True, help="Nombre común de la cirugía (p. ej. Enterectomía, OVH).")
    code = fields.Char(string="Código", help="Código interno / arancelario (opcional).")
    category = fields.Selection([
        ('soft_tissue', 'Tejidos blandos'),
        ('orthopedic', 'Ortopédica'),
        ('neurologic', 'Neurológica'),
        ('ophthalmic', 'Oftálmica'),
        ('dental', 'Dental/Estomatológica'),
        ('oncologic', 'Oncológica'),
        ('reproductive', 'Reproductiva'),
        ('other', 'Otra'),
    ], string="Categoría", default='soft_tissue')
    default_duration_min = fields.Integer(string="Duración estimada (min)", help="Duración típica, solo referencial.")
    description = fields.Text(string="Descripción / Indicaciones")
    notes = fields.Text(string="Notas internas")


class SurgeryMedicationLine(models.Model):
    """
    Línea de consumo de medicamentos dentro de una cirugía.
    Descuenta stock desde animal.medicine (en 'unidades' base del medicamento).
    """
    _name = "animal.surgery.medication.line"
    _description = "Línea de medicamentos de cirugía"
    _order = "id asc"

    surgery_record_id = fields.Many2one(
        "animal.surgery.record",
        string="Registro quirúrgico",
        required=True,
        ondelete="cascade"
    )
    medicine_id = fields.Many2one(
        "animal.medicine",
        string="Medicamento/Consumible",
        required=True,
        ondelete="restrict"
    )
    quantity_units = fields.Float(
        string="Cantidad (unidades)",
        default=1.0,
        help="Cantidad a descontar en unidades base (p. ej. mL, tabletas)."
    )
    lot_number = fields.Char(string="Lote / Serie")
    lot_expiration = fields.Date(string="Vencimiento (lote)")
    consume_stock = fields.Boolean(
        string="Descontar stock",
        default=True,
        help="Si está activo, al guardar se descuenta la cantidad del stock."
    )
    notes = fields.Char(string="Notas")

    _sql_constraints = [
        ('qty_non_negative', 'CHECK(quantity_units >= 0)', 'La cantidad debe ser mayor o igual a 0.')
    ]

    # === Movimiento de stock ===
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if rec.consume_stock and rec.medicine_id and rec.quantity_units:
            rec.medicine_id._consume_units(rec.quantity_units)
        return rec

    def write(self, vals):
        before = {r.id: {
            'medicine_id': r.medicine_id.id,
            'quantity_units': float(r.quantity_units or 0.0),
            'consume_stock': bool(r.consume_stock),
        } for r in self}
        res = super().write(vals)
        for r in self:
            prev = before[r.id]
            prev_med = prev['medicine_id'] and self.env['animal.medicine'].browse(prev['medicine_id']) or False
            prev_qty = prev['quantity_units']
            prev_consume = prev['consume_stock']

            new_med = r.medicine_id
            new_qty = float(r.quantity_units or 0.0)
            new_consume = bool(r.consume_stock)

            # 1) Antes consumía y ahora NO -> revertir
            if prev_consume and not new_consume and prev_med and prev_qty:
                prev_med._revert_units(prev_qty)
            # 2) Antes NO y ahora SÍ -> consumir
            elif not prev_consume and new_consume and new_med and new_qty:
                new_med._consume_units(new_qty)
            # 3) Sigue consumiendo -> revisar cambios
            elif prev_consume and new_consume:
                if prev_med and new_med and prev_med.id != new_med.id:
                    if prev_qty:
                        prev_med._revert_units(prev_qty)
                    if new_qty:
                        new_med._consume_units(new_qty)
                else:
                    delta = new_qty - prev_qty
                    if delta > 0:
                        new_med._consume_units(delta)
                    elif delta < 0:
                        new_med._revert_units(-delta)
        return res

    def unlink(self):
        for r in self:
            if r.consume_stock and r.medicine_id and r.quantity_units:
                r.medicine_id._revert_units(r.quantity_units)
        return super().unlink()


class SurgeryRecord(models.Model):
    """
    Registro quirúrgico por animal (acto quirúrgico).
    Incluye: preoperatorio, anestesia, procedimiento, consumos y postoperatorio.
    """
    _name = "animal.surgery.record"
    _description = "Registro de cirugías por animal"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc, id desc"

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
        "animal",
        string="Animal",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    owner_id = fields.Many2one(
        related="animal_id.owner",
        string="Dueño",
        store=True,
        readonly=True
    )
    specie_id = fields.Many2one(
        related="animal_id.species",
        string="Especie",
        store=True,
        readonly=True
    )
    breed_id = fields.Many2one(
        related="animal_id.breed",
        string="Raza",
        store=True,
        readonly=True
    )
    sex = fields.Selection(
        related="animal_id.sex",
        string="Sexo",
        store=True,
        readonly=True
    )
    microchip_number = fields.Char(
        related='animal_id.microchip_number',
        string="N° de microchip",
        store=True,
        readonly=True
    )

    # Programación / Estado
    date = fields.Datetime(string="Fecha/hora", required=True, default=fields.Datetime.now, tracking=True)
    duration_min = fields.Integer(string="Duración (min)", tracking=True)
    state = fields.Selection([
        ('scheduled', 'Programada'),
        ('in_progress', 'En curso'),
        ('done', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], string="Estado", default='scheduled', tracking=True, index=True)

    # Equipo
    surgeon = fields.Char(string="Cirujano/a", tracking=True)
    assistant = fields.Char(string="Asistente", tracking=True)
    anesthetist = fields.Char(string="Anestesista", tracking=True)

    # Procedimiento
    surgery_id = fields.Many2one(
        "animal.surgery",
        string="Cirugía",
        required=True,
        ondelete="restrict",
        tracking=True
    )
    side = fields.Selection([
        ('na', 'N/A'),
        ('left', 'Izquierda'),
        ('right', 'Derecha'),
        ('midline', 'Línea media'),
        ('bilateral', 'Bilateral'),
    ], string="Lado/Abordaje", default='na', tracking=True)
    wound_class = fields.Selection([
        ('clean', 'Limpia'),
        ('clean_contaminated', 'Limpia-contaminada'),
        ('contaminated', 'Contaminada'),
        ('dirty', 'Sucia'),
    ], string="Clasificación herida", tracking=True)
    preop_diagnosis = fields.Text(string="Diagnóstico preoperatorio")
    postop_diagnosis = fields.Text(string="Diagnóstico postoperatorio")
    procedure_details = fields.Text(string="Detalles del procedimiento")
    complications = fields.Text(string="Complicaciones")
    samples_taken = fields.Text(string="Muestras tomadas (biopsia, etc.)")
    estimated_blood_loss_ml = fields.Float(string="Pérdida sanguínea estimada (mL)")

    # Preoperatorio / Riesgo
    fasting_hours = fields.Float(string="Horas de ayuno")
    asa_status = fields.Selection([
        ('I', 'ASA I'),
        ('II', 'ASA II'),
        ('III', 'ASA III'),
        ('IV', 'ASA IV'),
        ('V', 'ASA V'),
    ], string="Estado ASA")
    preop_checks = fields.Text(string="Evaluación preoperatoria (exámenes / hallazgos)")
    consent_id = fields.Many2one(
        "animal.consent",
        string="Consentimiento informado",
        domain="[('animal_id', '=', animal_id), ('state', '=', 'signed')]",
        help="Vincula un consentimiento firmado para cirugía/anestesia."
    )

    # Anestesia / Analgesia
    anesthesia_protocol = fields.Text(string="Protocolo anestésico (premed/inducción/mantenimiento)")
    fluids_ml = fields.Float(string="Fluidos totales (mL)")
    analgesia = fields.Text(string="Analgesia/antibióticos (intra/post)")
    monitoring_notes = fields.Text(string="Monitoreo y eventos intraoperatorios")

    # Monitorización (campos opcionales)
    vitals_hr = fields.Float(string="Frecuencia cardiaca (lpm)")
    vitals_rr = fields.Float(string="Frecuencia respiratoria (rpm)")
    vitals_temp = fields.Float(string="Temperatura (°C)")
    vitals_spo2 = fields.Float(string="SpO₂ (%)")
    vitals_map = fields.Float(string="PAM (mmHg)")
    vitals_etco2 = fields.Float(string="ETCO₂ (mmHg)")

    # Postoperatorio
    hospitalization = fields.Boolean(string="Hospitalización", help="¿Queda hospitalizado tras la cirugía?")
    discharge_datetime = fields.Datetime(string="Alta (fecha/hora)")
    post_instructions = fields.Text(string="Indicaciones postoperatorias")
    next_control = fields.Date(string="Próximo control")

    # Consumos (descuentan stock de medicamentos)
    medication_line_ids = fields.One2many(
        "animal.surgery.medication.line",
        "surgery_record_id",
        string="Consumos / Medicación intra-quirúrgica"
    )

    # Adjuntos adicionales
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'animal_surgery_record_ir_attachments_rel',
        'record_id',
        'attachment_id',
        string="Adjuntos"
    )

    notes = fields.Text(string="Notas internas")

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'Nuevo') == 'Nuevo':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('animal.surgery.record.sequence') or 'Nuevo'
        return super().create(vals)

    @api.onchange('animal_id')
    def _onchange_animal_id_prefill_team(self):
        """
        Si el animal tiene 'médico tratante', proponerlo como Cirujano.
        Sugerimos consentimiento firmado más reciente del animal.
        """
        for rec in self:
            if rec.animal_id and rec.animal_id.treating_doctor and not rec.surgeon:
                rec.surgeon = rec.animal_id.treating_doctor
            if rec.animal_id and not rec.consent_id:
                consent = self.env['animal.consent'].search([
                    ('animal_id', '=', rec.animal_id.id),
                    ('state', '=', 'signed'),
                    ('consent_type', 'in', ('surgery', 'anesthesia'))
                ], order='date desc', limit=1)
                if consent:
                    rec.consent_id = consent.id

    def name_get(self):
        res = []
        for rec in self:
            label = rec.sequence or _("Cirugía")
            if rec.animal_id:
                label = "%s - %s" % (label, rec.animal_id.name)
            res.append((rec.id, label))
        return res

    # === Acciones de flujo ===
    def action_start(self):
        for rec in self:
            if rec.state not in ('scheduled',):
                raise UserError(_("Solo se puede iniciar una cirugía programada."))
            rec.state = 'in_progress'
        return True

    def action_done(self):
        for rec in self:
            if rec.state not in ('in_progress', 'scheduled'):
                raise UserError(_("Solo se puede finalizar una cirugía en curso o programada."))
            rec.state = 'done'
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("No es posible cancelar una cirugía completada."))
            rec.state = 'cancelled'
        return True

    def action_reset_to_scheduled(self):
        for rec in self:
            rec.state = 'scheduled'
        return True
