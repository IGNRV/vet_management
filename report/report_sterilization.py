# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import file_open
import base64

class ReportSterilization(models.AbstractModel):
    _name = 'report.vet_management.report_sterilization'
    _description = 'Report Sterilization (PDF)'

    def _get_report_values(self, docids, data=None):
        docs = self.env['animal.sterilization'].browse(docids)

        img_b64 = False
        # Intentamos primero el header específico de esterilización
        paths_to_try = [
            'vet_management/static/src/img/sterilizacion_header.png',
            # fallback por si se usa el mismo header de "visita"
            'vet_management/static/src/img/visita_header.png',
        ]
        for p in paths_to_try:
            try:
                with file_open(p, 'rb') as f:
                    img_b64 = base64.b64encode(f.read()).decode('utf-8')
                    if img_b64:
                        break
            except Exception:
                continue

        return {
            'doc_ids': docs.ids,
            'doc_model': 'animal.sterilization',
            'docs': docs,
            # Imagen para el template en data URI
            'stz_title_image': img_b64,
        }
