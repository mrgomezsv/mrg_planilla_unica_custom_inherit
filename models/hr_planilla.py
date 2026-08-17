# -*- coding: utf-8 -*-
import calendar
import base64
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


def parse_employee_name(full_name):
    """
    Desglosa el nombre completo de un empleado en:
    (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, apellido_casada)
    Cumple con el requerimiento de la columna 13 para la partícula 'de'.
    """
    if not full_name:
        return "", "", "", "", ""

    tokens = full_name.strip().split()
    if not tokens:
        return "", "", "", "", ""

    married_surname = ""
    tokens_clean = list(tokens)

    # Buscar si existe la partícula 'de'
    lower_tokens = [t.lower() for t in tokens]
    if 'de' in lower_tokens:
        de_idx = lower_tokens.index('de')
        if de_idx > 0 and de_idx < len(tokens) - 1:
            married_surname = " ".join(tokens[de_idx + 1:])
            tokens_clean = tokens[:de_idx]

    n = len(tokens_clean)
    first_name = ""
    second_name = ""
    first_surname = ""
    second_surname = ""

    if n >= 4:
        first_name = tokens_clean[0]
        second_name = " ".join(tokens_clean[1:n-2])
        first_surname = tokens_clean[n-2]
        second_surname = tokens_clean[n-1]
    elif n == 3:
        first_name = tokens_clean[0]
        second_name = tokens_clean[1]
        first_surname = tokens_clean[2]
    elif n == 2:
        first_name = tokens_clean[0]
        first_surname = tokens_clean[1]
    elif n == 1:
        first_name = tokens_clean[0]

    # Si se llena la columna 13 (apellido casada), la columna 12 (segundo apellido) queda vacía
    if married_surname:
        second_surname = ""

    return first_name, second_name, first_surname, second_surname, married_surname


class HrPlanilla(models.Model):
    _inherit = 'hr.planilla'

    csv_file_unica = fields.Binary(string="Archivo CSV Planilla Única", readonly=True)
    csv_filename_unica = fields.Char(string="Nombre Archivo CSV", readonly=True)

    def generar_lineas_planilla_unica(self, desde, hasta):
        """
        Consolida a los empleados presentes en planillas con estado 'PAGADAS'
        dentro del rango de fechas [desde, hasta]. Cada empleado aparecerá
        en una SOLA LÍNEA en la Planilla Única.
        """
        self.ensure_one()

        # Buscar planillas pagadas de la misma compañía en el rango de fecha
        domain_paid = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'pagada'),
            ('id', '!=', self.id),
            '|', '&', ('desde', '>=', desde), ('desde', '<=', hasta),
                 '&', ('hasta', '>=', desde), ('hasta', '<=', hasta)
        ]
        paid_payrolls = self.env['hr.planilla'].search(domain_paid)

        if not paid_payrolls:
            # Reintentar ampliando búsqueda a planillas pagadas que solapen el rango
            domain_paid = [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'pagada'),
                ('id', '!=', self.id),
                ('desde', '<=', hasta),
                ('hasta', '>=', desde)
            ]
            paid_payrolls = self.env['hr.planilla'].search(domain_paid)

        # Buscar la Planilla Única anterior para heredar códigos de observación 1 y 2
        prev_unica = self.env['hr.planilla'].search([
            ('company_id', '=', self.company_id.id),
            ('employer_type', '=', 'unica'),
            ('id', '!=', self.id),
            ('desde', '<', desde)
        ], order='desde desc', limit=1)

        obs_previous_map = {}
        if prev_unica:
            for pl in prev_unica.planilla_lines:
                emp_id = pl.nomina_id.employee_id.id if pl.nomina_id else False
                if emp_id:
                    obs_previous_map[emp_id] = (pl.codigo_observacion_1 or "00", pl.codigo_observacion_2 or "00")

        # Agrupar las líneas de las planillas pagadas por empleado
        employee_data = {}
        for payroll in paid_payrolls:
            for line in payroll.planilla_lines:
                emp = line.nomina_id.employee_id if line.nomina_id else False
                if not emp:
                    continue

                emp_id = emp.id
                if emp_id not in employee_data:
                    employee_data[emp_id] = {
                        'employee': emp,
                        'sample_line': line,
                        'sample_payslip': line.nomina_id,
                        'total_devengado': 0.0,
                        'total_vacaciones': 0.0,
                    }

                # Calcular devengado y vacaciones en las reglas de esta línea
                cat_rem_ref = self.env.ref("treming_sv_payroll.cat_rem", raise_if_not_found=False)
                cat_rem_id = cat_rem_ref.id if cat_rem_ref else False

                for r in line.reglas_ids:
                    code = (r.salary_rule_id.code or "").upper()
                    name = (r.salary_rule_id.name or "").upper()
                    cat_code = (r.category_id.code or "").upper()

                    # Regla de Vacaciones (Código 'RV' o Nombre 'VACACIONES')
                    if code == 'RV' or 'VACACIONES' in name:
                        employee_data[emp_id]['total_vacaciones'] += r.total
                    elif cat_code in ['RMN', 'SAL', 'REM'] or (cat_rem_id and r.category_id.id == cat_rem_id):
                        employee_data[emp_id]['total_devengado'] += r.total

        # Limpiar líneas previas generadas por defecto en esta planilla única
        self.planilla_lines.unlink()

        # Determinar número de días del mes del periodo (ej. 28, 29, 30 o 31)
        ref_date = hasta or self.hasta or fields.Date.today()
        days_in_month = calendar.monthrange(ref_date.year, ref_date.month)[1]

        # Crear una sola línea consolidada por empleado
        new_lines_vals = []
        for emp_id, data in employee_data.items():
            emp = data['employee']
            sample_payslip = data['sample_payslip']

            tot_dev = round(data['total_devengado'], 2)
            tot_vac = round(data['total_vacaciones'], 2)

            dias_vac = 15 if tot_vac > 0 else 0
            dias_trab = days_in_month - dias_vac

            contract = emp.contract_id or (sample_payslip.contract_id if sample_payslip else False)
            horas = "04" if (contract and getattr(contract, 'medio_tiempo', False)) else "08"

            obs1, obs2 = obs_previous_map.get(emp_id, ("00", "00"))

            new_lines_vals.append((0, 0, {
                'planilla_id': self.id,
                'nomina_id': sample_payslip.id if sample_payslip else False,
                'empleado': emp.name,
                'departamento': emp.department_id.name if emp.department_id else "",
                'salario': contract.wage if contract else 0.0,
                'liquido': tot_dev + tot_vac,
                'total_devengado_unica': tot_dev,
                'total_vacaciones_unica': tot_vac,
                'dias_vacacion_unica': dias_vac,
                'dias_trabajados_unica': dias_trab,
                'horas_diarias_unica': horas,
                'codigo_observacion_1': obs1,
                'codigo_observacion_2': obs2,
            }))

        if new_lines_vals:
            self.write({'planilla_lines': new_lines_vals})

        self.CalcularTotales()

    def action_download_planilla_unica_csv(self):
        """
        Genera y descarga el archivo CSV de Planilla Única con las 21 columnas
        especificadas en el requerimiento.
        """
        self.ensure_one()

        company = self.company_id or self.env.company
        nif = getattr(company.partner_id, 'vat', False) or getattr(company, 'vat', False) or ""
        numero_patronal = getattr(company, 'isss_patron_number', False) or getattr(company, 'numero_patronal', False) or ""

        ref_date = self.hasta or self.desde or fields.Date.today()
        periodo_mmaaaa = ref_date.strftime("%m%Y")
        centro_trabajo = getattr(company, 'isss_work_center', False) or getattr(company, 'centro_trabajo', False) or ""

        csv_rows = []
        for line in self.planilla_lines:
            emp = line.nomina_id.employee_id if line.nomina_id else False
            if not emp:
                continue

            # Col 5: DUI sin guiones
            dui = emp.doc_identi_id.num_doc if getattr(emp, 'doc_identi_id', False) else (getattr(emp, 'dui_number', False) or "")
            dui_clean = re.sub(r'\D', '', str(dui))

            # Col 6: Código tipo documento (01 para DUI)
            tipo_doc_code = "01"
            if getattr(emp, 'doc_identi_id', False) and getattr(emp.doc_identi_id, 'tipo_doc_id', False):
                code_val = getattr(emp.doc_identi_id.tipo_doc_id, 'codigo', False)
                if code_val:
                    tipo_doc_code = str(code_val).zfill(2)

            # Col 7: Código ISSS del empleado
            isss = line.isss_number if getattr(line, 'isss_number', False) else (getattr(emp, 'isss_number', False) or "")
            isss_clean = re.sub(r'\D', '', str(isss))

            # Col 8: Tipo AFP (COF o MAX)
            afp_code = line.afp_csv_code if getattr(line, 'afp_csv_code', False) else False
            if not afp_code:
                emp_afp = (getattr(emp, 'afp_code', '') or getattr(emp, 'afp_name_tr', '') or '').upper()
                if 'CONFIA' in emp_afp or 'COF' in emp_afp:
                    afp_code = "COF"
                else:
                    afp_code = "MAX"

            # Col 9 a 13: Desglose de nombres y apellidos
            p_nom, s_nom, p_ape, s_ape, ape_cas = parse_employee_name(emp.name)

            row = [
                str(nif),
                str(numero_patronal),
                str(periodo_mmaaaa),
                str(centro_trabajo),
                str(dui_clean),
                str(tipo_doc_code),
                str(isss_clean),
                str(afp_code),
                str(p_nom),
                str(s_nom),
                str(p_ape),
                str(s_ape),
                str(ape_cas),
                "{:.2f}".format(line.total_devengado_unica),
                "0",
                "{:.2f}".format(line.total_vacaciones_unica),
                str(line.dias_trabajados_unica),
                str(line.horas_diarias_unica),
                str(line.dias_vacacion_unica),
                str(line.codigo_observacion_1 or "00").zfill(2),
                str(line.codigo_observacion_2 or "00").zfill(2),
            ]
            csv_rows.append(",".join(row))

        csv_content = "\n".join(csv_rows)
        file_name = f"Planilla_Unica_{self.nombre or self.id}.csv"
        
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': base64.b64encode(csv_content.encode('utf-8')),
            'mimetype': 'text/csv',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
