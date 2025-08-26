from odoo import models, fields, api


class ExamOrder(models.Model):
    _name = "animal.exam.order"
    _description = "Órdenes de Exámenes"
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

    # Datos del paciente (de solo lectura para filtros/listados)
    specie = fields.Many2one(
        related='animal_id.species',
        string='Especie',
        store=True,
        readonly=True
    )
    breed = fields.Many2one(
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

    # Datos de la orden
    date = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    doctor = fields.Char(string="Dr/Dra")
    exam_type = fields.Selection([
        ('hemograma', 'Hemograma'),
        ('perfil_bioquimico', 'Perfil bioquímico'),
        ('orina', 'Orina (EGO)'),
        ('coproparasitario', 'Coproparasitológico'),
        ('radiografia', 'Radiografía'),
        ('ecografia', 'Ecografía'),
        ('citologia', 'Citología'),
        ('biopsia', 'Biopsia'),
        ('otro', 'Otro'),
    ], string="Tipo de examen", tracking=True)
    exam_type_other = fields.Char(string="Otro (especificar)")
    priority = fields.Selection([
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ], string="Prioridad", default='normal', tracking=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('ordered', 'Ordenado'),
        ('done', 'Completado'),
        ('cancelled', 'Cancelado'),
    ], string="Estado", default='draft', tracking=True)

    notes = fields.Text(string="Notas/Indicaciones")
    results = fields.Text(string="Resultados")

    # Adjuntos opcionales (además de los de chatter)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'animal_exam_order_ir_attachments_rel',
        'order_id',
        'attachment_id',
        string="Adjuntos"
    )

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'Nuevo') == 'Nuevo':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('animal.exam.order.sequence') or 'Nuevo'
        return super(ExamOrder, self).create(vals)

    # Acciones de estado
    def action_confirm(self):
        self.write({'state': 'ordered'})
        return True

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        return True
