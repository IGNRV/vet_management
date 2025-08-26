from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VetWaitingTicket(models.Model):
    _name = "vet.waiting.ticket"
    _description = "Sala de Espera - Ticket"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "state, priority desc, arrival_time asc, id asc"

    # Identificador / referencia
    sequence = fields.Char(
        string="Ticket",
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

    # Datos del paciente (solo lectura para filtros/listados)
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

    # Sala de espera
    arrival_time = fields.Datetime(
        string="Ingreso",
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    called_time = fields.Datetime(string="Llamado")
    start_time = fields.Datetime(string="Inicio atención")
    end_time = fields.Datetime(string="Fin atención")

    reason = fields.Text(string="Motivo")
    doctor = fields.Char(string="Dr/Dra asignado/a", tracking=True)
    room = fields.Char(string="Box/consulta")

    # Prioridad/Triage (ordenable desc por valor)
    priority = fields.Selection([
        ('0', 'Baja'),
        ('1', 'Normal'),
        ('2', 'Alta'),
        ('3', 'Emergencia'),
    ], string="Prioridad", default='1', tracking=True, index=True)

    # Estado del ticket
    state = fields.Selection([
        ('waiting', 'En espera'),
        ('called', 'Llamado'),
        ('in_consultation', 'En consulta'),
        ('paused', 'Pausado'),
        ('done', 'Atendido'),
        ('cancelled', 'Cancelado'),
    ], string="Estado", default='waiting', tracking=True, index=True)

    # Visita creada a partir del ticket
    visit_id = fields.Many2one('animal.visit', string="Visita vinculada", tracking=True)

    # Auxiliares
    waiting_minutes = fields.Integer(
        string="Min. en espera",
        compute="_compute_waiting_minutes",
        help="Minutos transcurridos desde el ingreso hasta ahora o hasta el inicio/fin."
    )
    notes = fields.Text(string="Notas internas")

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'Nuevo') == 'Nuevo':
            vals['sequence'] = self.env['ir.sequence'].next_by_code('vet.waiting.ticket.sequence') or 'Nuevo'
        return super().create(vals)

    @api.depends('arrival_time', 'start_time', 'end_time')
    def _compute_waiting_minutes(self):
        """Calcula minutos de espera efectivos (hasta start_time, end_time o ahora)."""
        now = fields.Datetime.now()
        for rec in self:
            if not rec.arrival_time:
                rec.waiting_minutes = 0
                continue
            stop = rec.start_time or rec.end_time or now
            delta = fields.Datetime.to_datetime(stop) - fields.Datetime.to_datetime(rec.arrival_time)
            rec.waiting_minutes = int(delta.total_seconds() // 60)

    @api.onchange('animal_id')
    def _onchange_animal_id_suggest_doctor(self):
        """Si el animal tiene 'médico tratante', sugerirlo como doctor."""
        for rec in self:
            if rec.animal_id and rec.animal_id.treating_doctor and not rec.doctor:
                rec.doctor = rec.animal_id.treating_doctor

    # === Acciones de flujo ===
    def action_call(self):
        for rec in self:
            if rec.state not in ('waiting', 'paused'):
                raise UserError(_("Solo se puede 'llamar' tickets en espera o pausados."))
            rec.write({'state': 'called', 'called_time': fields.Datetime.now()})
        return True

    def action_start_consultation(self):
        """Pasa a 'En consulta'. Si no existe, crea la visita y la vincula."""
        for rec in self:
            if rec.state not in ('waiting', 'called', 'paused'):
                raise UserError(_("Solo se puede iniciar atención desde En espera/Llamado/Pausado."))

            visit = rec.visit_id
            if not visit:
                visit_vals = {
                    'animal_id': rec.animal_id.id,
                    'date': fields.Datetime.now(),
                    'doctor': rec.doctor or (rec.animal_id and rec.animal_id.treating_doctor) or False,
                    # Campos nuevos en Visit (v17 del módulo): los rellenamos si existen
                    'consultation_reason': rec.reason or '',
                }
                visit = self.env['animal.visit'].create(visit_vals)
                rec.visit_id = visit.id

            rec.write({'state': 'in_consultation', 'start_time': fields.Datetime.now()})

            # Abrir la visita en formulario
            return {
                'type': 'ir.actions.act_window',
                'name': _('Visita'),
                'res_model': 'animal.visit',
                'view_mode': 'form',
                'res_id': visit.id,
                'target': 'current',
                'context': dict(self._context),
            }
        return True

    def action_open_visit(self):
        self.ensure_one()
        if not self.visit_id:
            raise UserError(_("Aún no hay una visita vinculada. Usa 'Iniciar atención'."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Visita'),
            'res_model': 'animal.visit',
            'view_mode': 'form',
            'res_id': self.visit_id.id,
            'target': 'current',
        }

    def action_pause(self):
        for rec in self:
            if rec.state != 'in_consultation':
                raise UserError(_("Solo se puede pausar cuando está 'En consulta'."))
            rec.state = 'paused'
        return True

    def action_resume(self):
        for rec in self:
            if rec.state != 'paused':
                raise UserError(_("Solo se puede reanudar desde 'Pausado'."))
            rec.state = 'in_consultation'
        return True

    def action_done(self):
        for rec in self:
            if rec.state not in ('in_consultation', 'called', 'paused'):
                raise UserError(_("Solo se puede finalizar cuando el ticket está en consulta/llamado/pausado."))
            rec.write({'state': 'done', 'end_time': fields.Datetime.now()})
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ('done',):
                raise UserError(_("No es posible cancelar un ticket ya atendido."))
            rec.state = 'cancelled'
        return True

    def action_reset_to_waiting(self):
        for rec in self:
            rec.write({
                'state': 'waiting',
                'called_time': False,
                'start_time': False,
                'end_time': False,
            })
        return True

    # === Utilidad para acción de servidor "Llamar siguiente" ===
    @api.model
    def action_call_next(self):
        """
        Busca el siguiente ticket en espera por prioridad (desc) y antigüedad,
        lo marca como 'Llamado' y lo abre en formulario.
        """
        ticket = self.search([('state', '=', 'waiting')], order='priority desc, arrival_time asc', limit=1)
        if not ticket:
            # Notificación al usuario
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sala de espera'),
                    'message': _('No hay tickets en espera.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        ticket.action_call()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ticket'),
            'res_model': 'vet.waiting.ticket',
            'view_mode': 'form',
            'res_id': ticket.id,
            'target': 'current',
        }
