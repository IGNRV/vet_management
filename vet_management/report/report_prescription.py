# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools import file_open
import base64


class ReportPrescription(models.AbstractModel):
    _name = 'report.vet_management.report_prescription'
    _description = 'Report Prescription (PDF)'

    def _get_report_values(self, docids, data=None):
        docs = self.env['animal.prescription'].browse(docids)

        header_b64 = False
        # Reutilizamos el header de "visita" si existe en el módulo
        try:
            with file_open('vet_management/static/src/img/visita_header.png', 'rb') as f:
                header_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            header_b64 = False

        return {
            'doc_ids': docs.ids,
            'doc_model': 'animal.prescription',
            'docs': docs,
            'presc_header_image': header_b64,
        }
