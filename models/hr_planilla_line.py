# -*- coding: utf-8 -*-
from odoo import models, fields

class HrPlanillaLine(models.Model):
    _inherit = 'hr.planilla.line'

    total_devengado_unica = fields.Monetary(string="Total Devengado (Única)", default=0.0)
    total_vacaciones_unica = fields.Monetary(string="Total Vacaciones (Única)", default=0.0)
    dias_vacacion_unica = fields.Integer(string="Días Vacaciones (Única)", default=0)
    dias_trabajados_unica = fields.Integer(string="Días (Única)", default=0)
    horas_diarias_unica = fields.Char(string="Horas (Única)", default="08")
    codigo_observacion_1 = fields.Char(string="Código Observación 1", size=2, default="00")
    codigo_observacion_2 = fields.Char(string="Código Observación 2", size=2, default="00")
