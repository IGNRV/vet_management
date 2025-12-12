from odoo import models, fields, api


class Sterilization(models.Model):
    _name = "animal.sterilization"
    _description = "Registro de esterilizaciones"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc"

    # ========= Enlaces opcionales =========
    animal_id = fields.Many2one("animal", string="Animal")
    owner_id = fields.Many2one("res.partner", string="Responsable")

    # ========= Datos responsable =========
    date = fields.Date(string="Fecha", tracking=True)
    resp_rut = fields.Char(string="RUT")
    resp_birthdate = fields.Date(string="Fecha de nacimiento (responsable)")
    resp_name = fields.Char(string="Nombre")
    resp_phone1 = fields.Char(string="Teléfono 1")
    resp_phone2 = fields.Char(string="Teléfono 2")
    resp_address = fields.Char(string="Dirección")
    resp_commune = fields.Char(string="Comuna")
    resp_region = fields.Char(string="Región")
    resp_email = fields.Char(string="Mail")
    resp_is_owner = fields.Boolean(string="¿Es dueño/a de la mascota?")

    # ========= Datos Paciente =========
    patient_name = fields.Char(string="Nombre (paciente)")

    # Antes: 'specie' era Selection. Ahora usamos Many2one a animal.specie.
    specie_id = fields.Many2one(
        "animal.specie",
        string="Especie",
        ondelete="restrict",
        tracking=True,
    )

    # Antes: 'breed_text' era Char. Ahora Many2one a animal.breed, filtrada por especie.
    breed_id = fields.Many2one(
        "animal.breed",
        string="Raza",
        domain="[('specie', '=', specie_id)]",
        ondelete="restrict",
        tracking=True,
    )

    patient_birthdate = fields.Date(string="Fecha de Nacimiento")
    sex = fields.Selection([
        ('macho', 'Macho'),
        ('hembra', 'Hembra'),
    ], string="Sexo")
    color = fields.Char(string="Color")
    weight = fields.Float(string="Peso (Kg)")
    pattern = fields.Char(string="Patrón")
    tenancy_type = fields.Selection([
        ('con_dueno', 'Con dueño'),
        ('comunitario', 'Comunitario'),
        ('sin_dueno', 'Sin dueño'),
    ], string="Tipo Tenencia")
    commune_obtention = fields.Char(string="Comuna Obtención")
    animals_at_home = fields.Integer(string="N° total animales en casa")

    obtention = fields.Selection([
        ('compra', 'Compra'),
        ('recogido', 'Recogido'),
        ('nacio_en_casa', 'Nació en casa'),
        ('regalo', 'Regalo'),
        ('adopcion', 'Adopción'),
        ('na', 'N/A'),
    ], string="Obtención")

    tenure_reason = fields.Selection([
        ('asistencia', 'Asistencia'),
        ('compania', 'Compañía'),
        ('deporte', 'Deporte'),
        ('exposicion', 'Exposición'),
        ('reproduccion', 'Reproducción'),
        ('seguridad', 'Seguridad'),
        ('terapia', 'Terapia'),
        ('trabajo', 'Trabajo'),
        ('ns', 'N/S'),
        ('na', 'N/A'),
        ('otro', 'Otro'),
    ], string="Razón tenencia")
    tenure_reason_other = fields.Char(string="Razón tenencia (otro)")
    already_sterilized = fields.Boolean(string="¿Su mascota ya está esterilizada?")
    visited_vet_before = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No'),
        ('ns', 'N/S'),
    ], string="¿Ha asistido antes al Médico Veterinario?")
    microchip_today = fields.Boolean(string="¿El microchip fue implantado hoy?")

    # ========= Procedimiento =========
    procedure_type = fields.Selection([
        ('ovariohisterectomia', 'Ovariohisterectomía'),
        ('orquiectomia', 'Orquiectomía'),
    ], string="Procedimiento")

    ovario_approach = fields.Selection([
        ('linea_alba', 'Línea alba'),
        ('flanco_izquierdo', 'Flanco izquierdo'),
        ('flanco_derecho', 'Flanco derecho'),
        ('mixto', 'Mixto'),
    ], string="Abordaje (Ovariohisterectomía)")

    orchiectomy_type = fields.Selection([
        ('pre_escrotal', 'Pre escrotal'),
        ('escrotal', 'Escrotal'),
        ('pre_escrotal_inguinal', 'Pre escrotal/inguinal'),
        ('escrotal_inguinal', 'Escrotal/inguinal'),
    ], string="Técnica (Orquiectomía)")

    vet_name = fields.Char(string="Nombre M. veterinario/a")
    vet_rut = fields.Char(string="RUT (médico)")
    signature = fields.Binary(string="Firma y timbre")

    # ========= Resultado procedimientos =========
    status = fields.Selection([
        ('exito', 'Finalizado con éxito'),
        ('suspendido', 'Suspendido'),
        ('rechazado', 'Rechazado'),
        ('fallecido', 'Fallecido'),
    ], string="Estado")
    death_cause = fields.Char(string="Causa defunción")
    death_moment = fields.Selection([
        ('pre_operatorio', 'Pre operatorio'),
        ('cirugia', 'Cirugía'),
        ('post_operatorio', 'Post operatorio'),
        ('casa', 'Casa'),
    ], string="Momento de defunción")
    death_date = fields.Date(string="Fecha defunción")

    # ========= Utilidad / etiquetas =========
    notes = fields.Text(string="Notas")

    # ====== Al elegir Animal, autocompletar DATOS PACIENTE (y sugerir Responsable) ======
    @api.onchange('animal_id')
    def _onchange_animal_id_fill_species_breed(self):
        """
        Autocompleta:
          - patient_name         <- animal.name
          - specie_id            <- animal.species
          - breed_id             <- animal.breed (si coincide la especie)
          - patient_birthdate    <- animal.birthdate
          - sex                  <- mapea animal.sex (male/female) -> (macho/hembra)
          - color                <- nombres de animal.tags unidos por coma (si existen)
          - weight               <- animal.weight
        Además sugiere:
          - owner_id             <- animal.owner
          - already_sterilized   <- True si animal.reproductive_status == 'neutered'
        """
        sex_map = {'male': 'macho', 'female': 'hembra'}
        for rec in self:
            if not rec.animal_id:
                # Si se deselecciona el animal, no tocamos los campos existentes.
                continue

            animal = rec.animal_id

            # Nombre del paciente
            rec.patient_name = animal.name or False

            # Especie del paciente
            rec.specie_id = animal.species.id or False

            # Raza: solo si coincide con la especie elegida
            if animal.breed and (not rec.specie_id or animal.breed.specie.id == rec.specie_id.id):
                rec.breed_id = animal.breed.id
            else:
                rec.breed_id = False

            # Fecha de nacimiento
            rec.patient_birthdate = animal.birthdate or False

            # Sexo (mapeo)
            rec.sex = sex_map.get(animal.sex, False)

            # Color (unimos etiquetas por nombre si existen)
            if animal.tags:
                rec.color = ", ".join(animal.tags.mapped('name'))
            else:
                rec.color = False

            # Peso
            rec.weight = animal.weight or False

            # Sugerir responsable desde el dueño del animal (si existe)
            rec.owner_id = animal.owner.id if animal.owner else False

            # Autocompletar si ya está esterilizado (desde estado reproductivo del animal)
            if animal.reproductive_status:
                rec.already_sterilized = (animal.reproductive_status == 'neutered')
            else:
                rec.already_sterilized = False
