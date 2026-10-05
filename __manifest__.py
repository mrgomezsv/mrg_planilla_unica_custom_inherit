# -*- coding: utf-8 -*-
{
    'name': 'MRG Planilla Única Custom Inherit',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Mejoras y cálculos para la generación y exportación CSV de Planilla Única',
    'description': """
        Módulo custom para dar cumplimiento al requerimiento de Planilla Única:
        - Agrega el campo 'Medio Tiempo' (check) en el contrato del empleado.
        - Filtra y agrupa en la Planilla Única a los empleados de planillas PAGADAS en el rango de fechas en una sola línea por empleado.
        - Calcula Total Devengado (excluyendo la regla de Vacaciones), Total Vacaciones, Días de Vacación (15 o 0), Días Trabajados y Horas (04 u 08).
        - Hereda los Códigos de Observación 1 y 2 de planillas anteriores del mismo tipo o los establece en '00' (editables en vista lista).
        - Implementa la exportación CSV con las 21 columnas requeridas para Planilla Única.
    """,
    'author': 'Mario Roberto Gomez',
    'website': 'https://mrgomezsv.github.io',
    'depends': [
        'base',
        'hr_payroll',
        'hr_work_entry_contract',
        'treming_sv_payroll',
        'mrg_planilla_unica_custom',
    ],
    'data': [
        'views/hr_contract_views.xml',
        'views/hr_planilla_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
