from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Dewormer(models.Model):
    _name = "animal.dewormer"
    _description = "Catálogo de desparasitantes (antiparasitarios)"

    # === Datos básicos ===
    name = fields.Char(string="Desparasitante", required=True)
    description = fields.Text(string="Descripción")

    # === Presentación genérica (caja -> pack/blíster/botella -> unidad) ===
    packs_per_box = fields.Integer(
        string="Packs por caja",
        default=1,
        help="Cantidad de packs/blísteres/botellas por caja.",
    )
    units_per_pack = fields.Float(
        string="Unidades por pack",
        default=1.0,
        help="Unidades por pack/blíster/botella (por ejemplo: tabletas por blíster, mL por frasco).",
    )
    packaging_notes = fields.Text(
        string="Notas de presentación",
        help="Notas sobre presentación (p.ej. mL por frasco, tabletas por blíster), equivalencias y uso.",
    )

    # === Stock por presentación (editable) ===
    stock_boxes = fields.Integer(string="Stock (cajas)", default=0, tracking=True)
    stock_packs = fields.Integer(string="Stock (packs sueltos)", default=0, tracking=True)
    stock_units = fields.Float(string="Stock (unidades sueltas)", default=0.0, tracking=True)

    # === Totales (lectura) ===
    stock_total_units = fields.Float(
        string="Stock total (unidades)",
        compute="_compute_stock_total_units",
        store=True,
        help="Total de unidades considerando cajas, packs y sueltas.",
    )

    @api.depends('stock_boxes', 'stock_packs', 'stock_units', 'packs_per_box', 'units_per_pack')
    def _compute_stock_total_units(self):
        for rec in self:
            ppb = max(rec.packs_per_box or 0, 0)
            upp = float(rec.units_per_pack or 0.0)
            total = (rec.stock_boxes or 0) * ppb * upp
            total += (rec.stock_packs or 0) * upp
            total += float(rec.stock_units or 0.0)
            rec.stock_total_units = total

    @api.constrains('packs_per_box', 'units_per_pack', 'stock_boxes', 'stock_packs', 'stock_units')
    def _check_non_negative(self):
        for rec in self:
            if rec.packs_per_box and rec.packs_per_box < 1:
                raise UserError(_("El campo 'Packs por caja' debe ser mayor o igual a 1."))
            if rec.units_per_pack and rec.units_per_pack <= 0:
                raise UserError(_("El campo 'Unidades por pack' debe ser mayor que 0."))
            if rec.stock_boxes is not None and rec.stock_boxes < 0:
                raise UserError(_("El stock de cajas no puede ser negativo."))
            if rec.stock_packs is not None and rec.stock_packs < 0:
                raise UserError(_("El stock de packs no puede ser negativo."))
            if rec.stock_units is not None and rec.stock_units < 0:
                raise UserError(_("El stock de unidades sueltas no puede ser negativo."))

    # === Helpers de fraccionamiento ===
    def _ensure_enough_units(self, units_needed):
        self.ensure_one()
        if units_needed <= 0:
            return
        if (self.stock_total_units or 0.0) < units_needed:
            raise UserError(
                _(
                    "Stock insuficiente del desparasitante '%s'. Unidades requeridas: %.2f, disponibles: %.2f"
                )
                % (self.name, units_needed, self.stock_total_units or 0.0)
            )

    def _break_pack_to_units(self, how_many_packs=1):
        self.ensure_one()
        if how_many_packs <= 0:
            return
        if (self.stock_packs or 0) < how_many_packs:
            raise UserError(_("No hay packs suficientes para fraccionar."))
        self.stock_packs -= how_many_packs
        self.stock_units += float(how_many_packs) * float(self.units_per_pack or 0)

    def _break_box_to_packs(self, how_many_boxes=1):
        self.ensure_one()
        if how_many_boxes <= 0:
            return
        if (self.stock_boxes or 0) < how_many_boxes:
            raise UserError(_("No hay cajas suficientes para fraccionar."))
        self.stock_boxes -= how_many_boxes
        self.stock_packs += int(how_many_boxes) * int(self.packs_per_box or 0)

    def _consume_units(self, units):
        """Consume 'units' unidades del stock, fraccionando según sea necesario."""
        self.ensure_one()
        if not units or units <= 0:
            return

        self._ensure_enough_units(units)

        deficit = units - (self.stock_units or 0.0)
        while deficit > 0:
            if (self.stock_packs or 0) > 0:
                self._break_pack_to_units(1)
            elif (self.stock_boxes or 0) > 0:
                self._break_box_to_packs(1)
            else:
                raise UserError(_("No hay stock suficiente para fraccionar en unidades."))
            deficit = units - (self.stock_units or 0.0)

        self.stock_units -= units

    def _revert_units(self, units):
        """Devuelve 'units' al stock como unidades sueltas."""
        self.ensure_one()
        if not units or units <= 0:
            return
        self.stock_units += units


class Deworming(models.Model):
    _name = "animal.deworming"
    _description = "Registro de desparasitación por animal"
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
    dewormer_id = fields.Many2one(
        "animal.dewormer",
        string="Desparasitante",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    # Datos de la aplicación
    date = fields.Datetime(string="Fecha", required=True, default=fields.Datetime.now, tracking=True)
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
    next_date = fields.Date(string="Próxima desparasitación", tracking=True)
    notes = fields.Text(string="Notas/Observaciones")

    # Consumo (en UNIDADES del desparasitante)
    quantity_units = fields.Float(
        string="Cantidad (unidades)",
        default=1.0,
        tracking=True,
        help="Cantidad a descontar en unidades base del desparasitante (p.ej. mL, tabletas).",
    )
    lot_number = fields.Char(string="Lote / Serie")
    lot_expiration = fields.Date(string="Vencimiento (lote)")

    consume_stock = fields.Boolean(
        string="Descontar stock",
        default=True,
        help="Si está activado, al guardar se descuenta 'Cantidad (unidades)' del stock del desparasitante.",
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
            label = "%s" % (rec.dewormer_id.name if rec.dewormer_id else "Desparasitación")
            if rec.date:
                label += " - %s" % fields.Datetime.to_string(rec.date)
            res.append((rec.id, label))
        return res

    _sql_constraints = [
        # Evitar duplicados exactos (mismo animal, mismo desparasitante, misma fecha)
        (
            'unique_animal_dewormer_date',
            'unique(animal_id, dewormer_id, date)',
            'Ya existe un registro de esta desparasitación para el animal en la misma fecha.',
        ),
        (
            'positive_units',
            'CHECK(quantity_units >= 0)',
            'La cantidad (unidades) debe ser mayor o igual a 0.',
        ),
    ]

    # === Movimiento de stock ===
    @api.model
    def create(self, vals):
        records = super().create(vals)
        for rec in records:
            if rec.consume_stock and rec.dewormer_id and rec.quantity_units:
                rec.dewormer_id._consume_units(rec.quantity_units)
        return records

    def write(self, vals):
        before = {
            rec.id: {
                'dewormer_id': rec.dewormer_id.id,
                'quantity_units': float(rec.quantity_units or 0.0),
                'consume_stock': bool(rec.consume_stock),
            }
            for rec in self
        }

        res = super().write(vals)

        for rec in self:
            prev = before[rec.id]
            prev_dew = prev['dewormer_id'] and self.env['animal.dewormer'].browse(prev['dewormer_id']) or False
            prev_qty = prev['quantity_units']
            prev_consume = prev['consume_stock']

            new_dew = rec.dewormer_id
            new_qty = float(rec.quantity_units or 0.0)
            new_consume = bool(rec.consume_stock)

            if prev_consume and not new_consume and prev_dew and prev_qty:
                prev_dew._revert_units(prev_qty)
            elif not prev_consume and new_consume and new_dew and new_qty:
                new_dew._consume_units(new_qty)
            elif prev_consume and new_consume:
                if prev_dew and new_dew and prev_dew.id != new_dew.id:
                    if prev_qty:
                        prev_dew._revert_units(prev_qty)
                    if new_qty:
                        new_dew._consume_units(new_qty)
                else:
                    delta = new_qty - prev_qty
                    if delta > 0:
                        new_dew._consume_units(delta)
                    elif delta < 0:
                        new_dew._revert_units(-delta)

        return res

    def unlink(self):
        for rec in self:
            if rec.consume_stock and rec.dewormer_id and rec.quantity_units:
                rec.dewormer_id._revert_units(rec.quantity_units)
        return super().unlink()
