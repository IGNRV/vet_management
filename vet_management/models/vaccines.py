from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Vaccine(models.Model):
    _name = "animal.vaccine"
    _description = "Animal vaccines table"

    # === Datos básicos ===
    name = fields.Char(string="Vacuna", required=True)
    description = fields.Text(string="Descripción")

    # === Presentación / Empaques ===
    vials_per_box = fields.Integer(
        string="Frascos por caja",
        default=1,
        help="Cantidad de frascos que trae una caja (presentación). Debe ser mayor que 0."
    )
    doses_per_vial = fields.Integer(
        string="Dosis por frasco",
        default=1,
        help="Cantidad de dosis que trae un frasco (presentación). Debe ser mayor que 0."
    )
    packaging_notes = fields.Text(
        string="Notas de presentación",
        help="Notas generales sobre presentación, instrucciones, equivalencias, etc."
    )

    # === Stock por presentación (editable) ===
    stock_boxes = fields.Integer(
        string="Stock (cajas)",
        default=0,
        tracking=True
    )
    stock_vials = fields.Integer(
        string="Stock (frascos sueltos)",
        default=0,
        tracking=True
    )
    stock_doses = fields.Float(
        string="Stock (dosis sueltas)",
        default=0.0,
        tracking=True,
        help="Dosis sueltas disponibles (puede incluir fracciones si se aprovecha un frasco parcialmente)."
    )

    # === Totales (lectura) ===
    stock_total_doses = fields.Float(
        string="Stock total (dosis)",
        compute="_compute_stock_total_doses",
        store=True,
        help="Total de dosis considerando cajas, frascos y dosis sueltas."
    )

    @api.depends('stock_boxes', 'stock_vials', 'stock_doses', 'vials_per_box', 'doses_per_vial')
    def _compute_stock_total_doses(self):
        for rec in self:
            vpb = max(rec.vials_per_box or 0, 0)
            dpv = max(rec.doses_per_vial or 0, 0)
            total = (rec.stock_boxes or 0) * vpb * dpv
            total += (rec.stock_vials or 0) * dpv
            total += (rec.stock_doses or 0.0)
            rec.stock_total_doses = total

    # === Validaciones ===
    @api.constrains('vials_per_box', 'doses_per_vial', 'stock_boxes', 'stock_vials', 'stock_doses')
    def _check_non_negative_and_positive_conversions(self):
        for rec in self:
            if rec.vials_per_box and rec.vials_per_box < 1:
                raise UserError(_("El campo 'Frascos por caja' debe ser mayor o igual a 1."))
            if rec.doses_per_vial and rec.doses_per_vial < 1:
                raise UserError(_("El campo 'Dosis por frasco' debe ser mayor o igual a 1."))
            if rec.stock_boxes is not None and rec.stock_boxes < 0:
                raise UserError(_("El stock de cajas no puede ser negativo."))
            if rec.stock_vials is not None and rec.stock_vials < 0:
                raise UserError(_("El stock de frascos no puede ser negativo."))
            if rec.stock_doses is not None and rec.stock_doses < 0:
                raise UserError(_("El stock de dosis sueltas no puede ser negativo."))

    # === Consumo / Reposición de stock en 'dosis' ===
    def _ensure_enough_doses(self, doses_needed):
        self.ensure_one()
        if doses_needed <= 0:
            return
        if (self.stock_total_doses or 0.0) < doses_needed:
            raise UserError(_(
                "Stock insuficiente de la vacuna '%s'. Dosis requeridas: %.2f, disponibles: %.2f"
            ) % (self.name, doses_needed, self.stock_total_doses or 0.0))

    def _break_vial_to_doses(self, how_many_vials=1):
        """Convierte frascos a dosis sueltas, si hay frascos disponibles."""
        self.ensure_one()
        if how_many_vials <= 0:
            return
        if (self.stock_vials or 0) < how_many_vials:
            raise UserError(_("No hay frascos suficientes para fraccionar."))
        self.stock_vials -= how_many_vials
        self.stock_doses += float(how_many_vials) * float(self.doses_per_vial or 0)

    def _break_box_to_vials(self, how_many_boxes=1):
        """Convierte cajas a frascos sueltos."""
        self.ensure_one()
        if how_many_boxes <= 0:
            return
        if (self.stock_boxes or 0) < how_many_boxes:
            raise UserError(_("No hay cajas suficientes para fraccionar."))
        self.stock_boxes -= how_many_boxes
        self.stock_vials += int(how_many_boxes) * int(self.vials_per_box or 0)

    def _consume_doses(self, doses):
        """
        Consume 'doses' dosis del stock, fraccionando según sea necesario:
        primero dosis sueltas, luego frascos, luego cajas.
        """
        self.ensure_one()
        if not doses or doses <= 0:
            return

        self._ensure_enough_doses(doses)

        # Asegurar suficiencia de dosis sueltas, fraccionando de frascos/cajas si falta
        dpv = int(self.doses_per_vial or 0)
        vpb = int(self.vials_per_box or 0)

        # Si faltan dosis sueltas, intento romper frascos; si no, cajas.
        deficit = doses - (self.stock_doses or 0.0)
        while deficit > 0:
            if (self.stock_vials or 0) > 0:
                self._break_vial_to_doses(1)
            elif (self.stock_boxes or 0) > 0:
                self._break_box_to_vials(1)
            else:
                # No debería entrar aquí por _ensure_enough_doses, pero por seguridad:
                raise UserError(_("No hay stock suficiente para fraccionar en dosis."))
            deficit = doses - (self.stock_doses or 0.0)

        # Ahora ya hay dosis sueltas suficientes
        self.stock_doses -= doses

    def _revert_doses(self, doses):
        """
        Devuelve 'doses' dosis al stock como dosis sueltas (no recompone cajas/frasco).
        """
        self.ensure_one()
        if not doses or doses <= 0:
            return
        self.stock_doses += doses


class Vaccination(models.Model):
    _name = "animal.vaccination"
    _description = "Registro de vacunación por animal"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc, id desc"

    # Enlaces
    animal_id = fields.Many2one(
        "animal",
        string="Animal",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    vaccine_id = fields.Many2one(
        "animal.vaccine",
        string="Vacuna",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    # Datos de la aplicación
    date = fields.Date(string="Fecha de vacunación", required=True, tracking=True)
    route = fields.Selection([
        ('sc', 'Subcutánea'),
        ('im', 'Intramuscular'),
        ('iv', 'Intravenosa'),
        ('oral', 'Oral'),
        ('intranasal', 'Intranasal'),
        ('topical', 'Tópica'),
        ('other', 'Otra'),
    ], string="Vía de administración", tracking=True)
    doctor = fields.Char(string="Dr/Dra (aplicó)", tracking=True)
    next_date = fields.Date(string="Próxima vacunación", tracking=True)
    notes = fields.Text(string="Notas/Observaciones")

    # === Detalles de consumo / lote ===
    applied_doses = fields.Float(
        string="Dosis aplicadas",
        default=1.0,
        tracking=True,
        help="Cantidad de dosis aplicadas en este registro (se descuenta del stock si corresponde)."
    )
    lot_number = fields.Char(string="Lote / Serie")
    lot_expiration = fields.Date(string="Vencimiento (lote)")

    consume_stock = fields.Boolean(
        string="Descontar stock",
        default=True,
        help="Si está activado, al guardar se descuenta la(s) dosis del stock de la vacuna."
    )

    # Auxiliares de lectura
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

    @api.onchange('animal_id')
    def _onchange_animal_id_prefill_doctor(self):
        """Si el animal tiene 'médico tratante', proponerlo como doctor."""
        for rec in self:
            if rec.animal_id and rec.animal_id.treating_doctor and not rec.doctor:
                rec.doctor = rec.animal_id.treating_doctor

    def name_get(self):
        res = []
        for rec in self:
            label = "%s" % (rec.vaccine_id.name if rec.vaccine_id else "Vacuna")
            if rec.date:
                label += " - %s" % fields.Date.to_string(rec.date)
            res.append((rec.id, label))
        return res

    _sql_constraints = [
        # Evitar duplicados exactos (mismo animal, misma vacuna, misma fecha)
        ('unique_animal_vaccine_date',
         'unique(animal_id, vaccine_id, date)',
         'Ya existe un registro de esta vacuna para el animal en la misma fecha.')
    ]

    # === Movimiento de stock ===
    @api.model
    def create(self, vals):
        records = super().create(vals)
        for rec in records:
            if rec.consume_stock and rec.vaccine_id and rec.applied_doses:
                rec.vaccine_id._consume_doses(rec.applied_doses)
        return records

    def write(self, vals):
        # Guardamos estado previo para calcular diferencias
        before = {rec.id: {
            'vaccine_id': rec.vaccine_id.id,
            'applied_doses': rec.applied_doses,
            'consume_stock': rec.consume_stock,
        } for rec in self}

        res = super().write(vals)

        for rec in self:
            prev = before[rec.id]
            prev_vac = prev['vaccine_id'] and self.env['animal.vaccine'].browse(prev['vaccine_id']) or False
            prev_doses = float(prev['applied_doses'] or 0.0)
            prev_consume = bool(prev['consume_stock'])
            new_vac = rec.vaccine_id
            new_doses = float(rec.applied_doses or 0.0)
            new_consume = bool(rec.consume_stock)

            # Casos:
            # 1) Antes consumía y ahora NO -> revertir prev_doses en prev_vac
            if prev_consume and not new_consume and prev_vac and prev_doses:
                prev_vac._revert_doses(prev_doses)

            # 2) Antes NO y ahora SÍ -> consumir new_doses en new_vac
            elif not prev_consume and new_consume and new_vac and new_doses:
                new_vac._consume_doses(new_doses)

            # 3) Sigue consumiendo: revisar cambios de vacuna o cantidad
            elif prev_consume and new_consume:
                if prev_vac and new_vac and prev_vac.id != new_vac.id:
                    # Cambió la vacuna: devolver a la anterior y consumir de la nueva
                    if prev_doses:
                        prev_vac._revert_doses(prev_doses)
                    if new_doses:
                        new_vac._consume_doses(new_doses)
                else:
                    # Misma vacuna: consumir diferencia
                    delta = new_doses - prev_doses
                    if delta > 0:
                        new_vac._consume_doses(delta)
                    elif delta < 0:
                        new_vac._revert_doses(-delta)

        return res

    def unlink(self):
        for rec in self:
            if rec.consume_stock and rec.vaccine_id and rec.applied_doses:
                # Devolver las dosis consumidas
                rec.vaccine_id._revert_doses(rec.applied_doses)
        return super().unlink()