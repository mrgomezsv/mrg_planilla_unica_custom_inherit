# -*- coding: utf-8 -*-
from odoo import models, fields

class HrContract(models.Model):
    _inherit = 'hr.contract'

    medio_tiempo = fields.Boolean(
        string="Medio Tiempo",
        default=False,
        help="Marcar si el contrato corresponde a jornada de medio tiempo (4 horas diarias)."
    )
