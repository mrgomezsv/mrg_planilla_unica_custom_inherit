# -*- coding: utf-8 -*-
from odoo import models, api, fields, _

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def generar(self, nominas, params=[]):
        rec = super(HrPayslipEmployees, self).generar(nominas, params)

        # Si se trata de una Planilla Única Patronal
        if self.tipo == "patronal" and self.employer_type == "unica":
            payrolls = self.env["hr.planilla"].search(rec)
            for payroll in payrolls:
                payroll.generar_lineas_planilla_unica(self.desde, self.hasta)

        return rec
