# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import file_open
import base64

class ReportVisit(models.AbstractModel):
    _name = 'report.vet_management.report_visit'
    _description = 'Report Visit (PDF)'

    def _get_report_values(self, docids, data=None):
        docs = self.env['animal.visit'].browse(docids)

        header_b64 = False
        divider_b64 = False

        # Intentamos cargar ambas imágenes desde el módulo; si falla, seguimos sin romper el reporte
        try:
            with file_open('vet_management/static/src/img/visita_header.png', 'rb') as f:
                header_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            header_b64 = False

        try:
            with file_open('vet_management/static/src/img/visita_divider.png', 'rb') as f:
                divider_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            divider_b64 = False

        return {
            'doc_ids': docs.ids,
            'doc_model': 'animal.visit',
            'docs': docs,
            'visit_header_image': header_b64,
            'visit_divider_image': divider_b64,
        }
