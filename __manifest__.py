# -*- coding: utf-8 -*- 
{
    'name': "Gestión Veterinaria",

    'summary': "Gestiona los animales que visitan la veterinaria",

    'description': """
Gestiona los animales que visitan la veterinaria.
Incluye visitas, vacunas, cirugías, recetas y más.
    """,

    'author': "z99sys",
    'website': "https://z99sys.cl/",
    'license': 'OPL-1',  # Cambiado desde AGPL-3 para permitir venta en Odoo Apps
    'category': 'Animales',
    'version': '17.0.1.0.0',  # Debe iniciar con la serie para Odoo 17

    # any module necessary for this one to work correctly
    'depends': ['base','mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        # === Reportes ===
        'report/sterilization_report.xml',
        'report/visit_report.xml',
        'report/exam_order_report.xml',
        # EXISTENTE
        'report/vaccination_report.xml',
        'report/consent_report.xml',
        # === NUEVO: Reporte de Recetas ===
        'report/prescription_report.xml',
        # === NUEVO: Reporte de Cirugías ===
        'report/surgery_report.xml',

        # === Vistas base ===
        'views/animals_views.xml',
        'views/medicines_views.xml',
        'views/allergies_views.xml',
        'views/surgeries_views.xml',
        'views/vaccines_views.xml',
        'views/visits_views.xml',
        'views/species_views.xml',
        'views/breeds_views.xml',
        'views/tags_views.xml',
        'views/animal_partner_views.xml',

        # Vistas de Seguros
        'views/insurances_views.xml',

        # Vistas de Esterilizaciones
        'views/sterilizations_views.xml',

        # Vistas de Órdenes de Exámenes
        'views/exam_orders_views.xml',

        # REGISTROS de Vacunación (existente)
        'views/vaccinations_views.xml',

        # Catálogo y REGISTROS de Desparasitación (existente)
        'views/dewormers_views.xml',
        'views/dewormings_views.xml',

        # Consentimientos
        'views/consents_views.xml',

        # Sala de Espera
        'views/waiting_room_sequence.xml',
        'views/waiting_room_views.xml',

        # === NUEVO: Vistas de Recetas ===
        'views/prescriptions_views.xml',

        # Menús
        'views/animals_menus.xml',
        'views/statistics_views.xml',

        # Secuencias/otros
        'views/visit_sequence.xml',
        'views/animals_identification.xml',
        'views/exam_order_sequence.xml',
        'views/consent_sequence.xml',
        # === NUEVO: Secuencia de Recetas ===
        'views/prescription_sequence.xml',
        # === NUEVO: Secuencia de Cirugías ===
        'views/surgery_sequence.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "images": [
        "static/images/banner.png",
        "static/description/icon.png",
        "static/src/img/visita_header.png",
        "static/src/img/visita_divider.png",
        "static/src/img/sterilizacion_header.png"
    ],
    'installable': True,
    'application': True,
    'auto_install': False,

    'price': 200.0,
    'currency': 'USD',
}
