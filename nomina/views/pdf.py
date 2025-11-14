from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.edit import FormView
from django.views import generic
from django.views import View
from django.http import JsonResponse, HttpResponse
from bases.views import SinPrivilegios
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from nomina.models import (
    Empleado, Asistencia, Nomina, NominaHistorial, NominaDetalle,
    PeriodosNomina, EmpleadoArchivo, AsignacionDiaria, MovimientoCuentaProyecto, TipoDestajo, TarifaDiariaObra, TarifaDestajoObra,
    RegistroDestajo
    )
from nomina.views.nomina_calculo import calcular_nomina_semanal_todos
from inv.models import Material
from adm.models import MovimientoCuenta, Cuenta, Proyecto, RegistroCuenta
from nomina.forms import (
    EmpleadoForm, FaltaForm,  PeriodosNominaForm, EmpleadoArchivoForm, AsignarProyectoForm, SeleccionarPeriodoForm,
    NominaEmpleadoProyectoForm, AsignacionDiaria, AsignacionDiariaForm, AsignacionDiariaFormSet, TarifaDestajoObraForm, TipoDestajoForm
)
from xhtml2pdf import pisa
from django.template.loader import render_to_string, get_template
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import SimpleDocTemplate, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, legal
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from django.db.models import Sum, Max, Q, Count, F, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import traceback
import logging
from io import BytesIO
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.utils import ImageReader
import os



def formato_fecha(fecha):
    return fecha.strftime("%d-%B-%Y").capitalize()



# @login_required(login_url='bases:login')
# def generar_nomina_pdf(request, fecha_str):
#     """
#     Genera PDF profesional multipágina de nómina semanal:
#     - Logo y título en todas las páginas
#     - Número de página (Página X de Y)
#     - Tabla ordenada con encabezados fijos
#     """

#     try:
#         fecha_inicio_semana = datetime.strptime(fecha_str, "%Y-%m-%d").date()
#     except ValueError:
#         messages.error(request, "Formato de fecha incorrecto.")
#         return redirect('nom:seleccionar_fecha')

#     fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    

#     periodo = PeriodosNomina.objects.filter(periodo_inicio=fecha_inicio_semana).first()
#     if not periodo:
#         messages.error(request, "No se encontró el período de nómina correspondiente a la fecha seleccionada.")
#         return redirect('nom:seleccionar_fecha')

#     # ✅ Pasa el objeto PeriodosNomina, no la fecha
#     resultados = calcular_nomina_semanal_todos(periodo)
#     nomina_data = resultados.get('nomina', [])

#     if not nomina_data:
#         messages.info(request, "No hay datos de nómina para generar el PDF.")
#         return redirect('nom:seleccionar_fecha')

#     # === CONFIGURACIÓN GENERAL ===
#     buffer = BytesIO()
#     response = HttpResponse(content_type="application/pdf")
#     response["Content-Disposition"] = f'attachment; filename=\"nomina_semanal_{fecha_str}.pdf\"'

#     width, height = landscape(legal)
#     margen_izq, margen_der, margen_sup, margen_inf = 10, 40, 60, 50
#     logo_path = os.path.join(settings.BASE_DIR, "static/base/img/inemo.png")

#     # === ENCABEZADO Y PIE DE PÁGINA ===
#     def header_footer(canvas, doc):
#         canvas.saveState()
#         logo_w, logo_h = 120, 50
#         y_top = height - 50

#         # Logo
#         try:
#             canvas.drawImage(ImageReader(logo_path), margen_izq, y_top - logo_h,
#                              width=logo_w, height=logo_h, mask="auto")
#         except Exception as e:
#             print(f"⚠ No se pudo cargar el logo: {e}")

#         # Título
#         titulo = f"NÓMINA SEMANAL DEL {fecha_inicio_semana.strftime('%d/%m/%Y')} AL {fecha_fin_semana.strftime('%d/%m/%Y')}"
#         canvas.setFont("Helvetica-Bold", 15)
#         canvas.drawCentredString(width / 2, y_top - 15, titulo)

#         # Subtítulo
#         canvas.setFont("Helvetica", 9)
#         canvas.drawCentredString(width / 2, y_top - 30, "INEMO Constructora  •  RFC: IEM060621IE3")
#         canvas.drawCentredString(width / 2, y_top - 42, "Puerto Altata 590, Culiacán, Sinaloa")

#         # Línea divisoria
#         canvas.line(margen_izq, y_top - 50, width - margen_der, y_top - 50)

#         # Pie de página
#         canvas.setFont("Helvetica", 8)
#         canvas.drawString(
#             margen_izq, 40,
#             "01 Sueldo Diario • 02 Días Trabajados • 03 Sueldo Percibido • 04 Séptimo Día • 05 Compensación • "
#             "06 Horas Extra • 07 Destajos • 08 Total Percepciones • 09 Faltas • 10 Importe Falta • "
#             "11 Descuento 7° Día • 12 Total Deducciones • 13 Total Neto"
#         )

#         page_num = canvas.getPageNumber()
#         canvas.drawRightString(width - margen_der, 40, f"Página {page_num}")
#         canvas.restoreState()

#     # === DOCUMENTO ===
#     doc = BaseDocTemplate(
#         buffer,
#         pagesize=landscape(legal),
#         leftMargin=margen_izq,
#         rightMargin=margen_der,
#         topMargin=margen_sup + 40,
#         bottomMargin=margen_inf + 20,
#     )

#     frame = Frame(
#         margen_izq,
#         margen_inf,
#         width - margen_izq - margen_der,
#         height - (margen_sup + margen_inf + 40),
#         id="normal"
#     )
#     doc.addPageTemplates([PageTemplate(id="Nomina", frames=[frame], onPage=header_footer)])

#     # === CONTENIDO ===
#     elementos = []
#     estilos = getSampleStyleSheet()

#     encabezados = [
#         "Empleado", "1", "2", "3",
#         "4", "5", "6", "7",
#         "8", "9", "10",
#         "11", "12", "Total Neto", "Firma"
#     ]

#     # === Estilo del nombre del empleado (corrección) ===
#     estilo_empleado = ParagraphStyle(
#         "empleado",
#         fontName="Helvetica",
#         fontSize=8,
#         leading=9,
#         alignment=0,
#         leftIndent=4,   # Sangría interna para evitar que se corte el texto
#     )

#     filas = []
#     for item in nomina_data:
#         total_per = (
#             Decimal(item.get("sueldo_semanal", 0)) +
#             Decimal(item.get("septimo_dia", 0)) +
#             Decimal(item.get("compensacion", 0)) +
#             Decimal(item.get("horas_extras", 0)) +
#             Decimal(item.get("destajos", 0))
#         )
#         total_ded = Decimal(item.get("importe_faltas", 0)) + Decimal(item.get("descuento_septimo_dia", 0))
#         total_neto = total_per - total_ded

#         # ✅ Usar Paragraph para el nombre
#         nombre = Paragraph(str(item.get("empleado", "")), estilo_empleado)

#         filas.append([
#             nombre,
#             f"${item.get('sueldo_diario', 0):,.2f}",
#             f"{item.get('dias_trabajados', 0)}",
#             f"${item.get('sueldo_semanal', 0):,.2f}",
#             f"${item.get('septimo_dia', 0):,.2f}",
#             f"${item.get('compensacion', 0):,.2f}",
#             f"${item.get('horas_extras', 0):,.2f}",
#             f"${item.get('destajos', 0):,.2f}",
#             f"${total_per:,.2f}",
#             f"{item.get('faltas', 0)}",
#             f"${item.get('importe_faltas', 0):,.2f}",
#             f"${item.get('descuento_septimo_dia', 0):,.2f}",
#             f"${total_ded:,.2f}",
#             f"${total_neto:,.2f}",
#             ""
#         ])

#     total_percepciones = sum(
#         Decimal(item.get("sueldo_semanal", 0)) +
#         Decimal(item.get("septimo_dia", 0)) +
#         Decimal(item.get("compensacion", 0)) +
#         Decimal(item.get("horas_extras", 0)) +
#         Decimal(item.get("destajos", 0))
#         for item in nomina_data
#     )
#     total_deducciones = sum(
#         Decimal(item.get("importe_faltas", 0)) +
#         Decimal(item.get("descuento_septimo_dia", 0))
#         for item in nomina_data
#     )
#     total_neto_general = total_percepciones - total_deducciones

#     # === Totales por columna específica (3 al 8) ===
#     total_col3 = sum(Decimal(item.get("sueldo_semanal", 0)) for item in nomina_data)
#     total_col4 = sum(Decimal(item.get("septimo_dia", 0)) for item in nomina_data)
#     total_col5 = sum(Decimal(item.get("compensacion", 0)) for item in nomina_data)
#     total_col6 = sum(Decimal(item.get("horas_extras", 0)) for item in nomina_data)
#     total_col7 = sum(Decimal(item.get("destajos", 0)) for item in nomina_data)
#     total_col8 = sum(
#     Decimal(item.get("sueldo_semanal", 0))
#     + Decimal(item.get("septimo_dia", 0))
#     + Decimal(item.get("compensacion", 0))
#     + Decimal(item.get("horas_extras", 0))
#     + Decimal(item.get("destajos", 0))
#     for item in nomina_data
# )
#     # === Totales por columna específica (9 al 12) ===
#     total_col9 = sum(Decimal(item.get("faltas", 0)) for item in nomina_data)
#     total_col10 = sum(Decimal(item.get("importe_faltas", 0)) for item in nomina_data)
#     total_col11 = sum(Decimal(item.get("descuento_septimo_dia", 0)) for item in nomina_data)
#     total_col12 = sum(
#         Decimal(item.get("importe_faltas", 0))
#         + Decimal(item.get("descuento_septimo_dia", 0))
#         for item in nomina_data
# )



#     filas.append([
#     "TOTALES", "", "", 
#     f"${total_col3:,.2f}",   # 3 Sueldo Percibido
#     f"${total_col4:,.2f}",   # 4 Séptimo Día
#     f"${total_col5:,.2f}",   # 5 Compensación
#     f"${total_col6:,.2f}",   # 6 Horas Extra
#     f"${total_col7:,.2f}",   # 7 Destajos
#     f"${total_col8:,.2f}",   # 8 Total Percepciones
#     f"{total_col9}",         # 9 Faltas
#     f"${total_col10:,.2f}",  # 10 Importe Falta
#     f"${total_col11:,.2f}",  # 11 Descuento 7° Día
#     f"${total_col12:,.2f}",  # 12 Total Deducciones
#     f"${total_neto_general:,.2f}",  # 13 Total Neto
#     ""                       # Firma
# ])



#     data = [encabezados] + filas

#     # === LIGERO AUMENTO DE ANCHO EN “Empleado” ===
#     col_widths = [
#     150,  # Empleado
#     55, 45, 60, 55, 60, 55, 60, 75, 40, 60, 60, 70, 75, 65  # Resto + Firma visible
#     ]   

#     tabla = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
#     tabla.spaceBefore = 0
#     tabla.spaceAfter = 0
#     tabla.setStyle(TableStyle([
#     # Encabezado
#     ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
#     ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
#     ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#     ("ALIGN", (0, 0), (-1, 0), "CENTER"),   # ✅ Encabezados centrados
#     ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),

#     # Cuerpo
#     ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
#     ("ALIGN", (0, 1), (0, -1), "LEFT"),
#     ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),

#     # Formato general
#     ("FONTSIZE", (0, 0), (-1, -1), 8),
#     ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
#     ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
#     ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
#     ("LEFTPADDING", (0, 0), (0, -1), 10),
# ]))


#     elementos.append(tabla)
#     doc.build(elementos)

#     pdf = buffer.getvalue()
#     buffer.close()
#     response.write(pdf)
#     return response






@login_required(login_url='bases:login')
def generar_nomina_pdf(request, fecha_str):
    """Reporte PDF de Nómina agrupado por proyecto con totales detallados por columnas y globales."""

    # === Obtener el periodo ===
    try:
        fecha_inicio_semana = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha incorrecto.")
        return redirect('nom:seleccionar_fecha')

    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)
    periodo = PeriodosNomina.objects.filter(periodo_inicio=fecha_inicio_semana).first()
    if not periodo:
        messages.error(request, "No se encontró el período de nómina correspondiente a la fecha seleccionada.")
        return redirect('nom:seleccionar_fecha')

    resultados = calcular_nomina_semanal_todos(periodo)
    nomina_data = resultados.get('nomina', [])
    if not nomina_data:
        messages.info(request, "No hay datos de nómina para generar el PDF.")
        return redirect('nom:seleccionar_fecha')

    # === Configuración general ===
    buffer = BytesIO()
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="nomina_semanal_{fecha_str}.pdf"'

    width, height = landscape(legal)
    margen_izq, margen_der, margen_sup, margen_inf = 10, 40, 60, 50
    logo_path = os.path.join(settings.BASE_DIR, "static/base/img/inemo.png")

    # === Encabezado y pie de página ===
    def header_footer(canvas, doc):
        canvas.saveState()
        y_top = height - 50
        logo_w, logo_h = 120, 50
        try:
            canvas.drawImage(ImageReader(logo_path), margen_izq, y_top - logo_h,
                             width=logo_w, height=logo_h, mask="auto")
        except Exception:
            pass

        titulo = f"NÓMINA SEMANAL DEL {fecha_inicio_semana.strftime('%d/%m/%Y')} AL {fecha_fin_semana.strftime('%d/%m/%Y')}"
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawCentredString(width / 2, y_top - 15, titulo)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(width / 2, y_top - 30, "INEMO Constructora  •  RFC: IEM060621IE3")
        canvas.drawCentredString(width / 2, y_top - 42, "Puerto Altata 590, Culiacán, Sinaloa")
        canvas.line(margen_izq, y_top - 50, width - margen_der, y_top - 50)

        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            margen_izq, 40,
            "01 Sueldo Diario • 02 Días Trabajados • 03 Sueldo Percibido • 04 Séptimo Día • 05 Compensación • "
            "06 Horas Extra • 07 Destajos • 08 Total Percepciones • 09 Faltas • 10 Importe Falta • "
            "11 Descuento 7° Día • 12 Total Deducciones • 13 Total Neto"
        )
        page_num = canvas.getPageNumber()
        canvas.drawRightString(width - margen_der, 40, f"Página {page_num}")
        canvas.restoreState()

    # === Documento ===
    doc = BaseDocTemplate(
        buffer,
        pagesize=landscape(legal),
        leftMargin=margen_izq,
        rightMargin=margen_der,
        topMargin=margen_sup + 40,
        bottomMargin=margen_inf + 20,
    )
    frame = Frame(
        margen_izq,
        margen_inf,
        width - margen_izq - margen_der,
        height - (margen_sup + margen_inf + 40),
        id="normal"
    )
    doc.addPageTemplates([PageTemplate(id="Nomina", frames=[frame], onPage=header_footer)])

    # === Contenido ===
    elementos = []
    estilo_empleado = ParagraphStyle("empleado", fontName="Helvetica", fontSize=8, leading=9, alignment=0, leftIndent=4)
    estilo_subtitulo = ParagraphStyle("subtitulo", fontName="Helvetica-Bold", fontSize=11, textColor=colors.darkblue, spaceAfter=6)

    encabezados = [
        "Empleado", "1", "2", "3", "4", "5", "6", "7",
        "8", "9", "10", "11", "12", "Total Neto", "Firma"
    ]
    col_widths = [150, 55, 45, 60, 55, 60, 55, 60, 75, 40, 60, 60, 70, 75, 65]

    # === Agrupar por proyecto ===
    proyectos = (
        AsignacionDiaria.objects.filter(fecha__range=(fecha_inicio_semana, fecha_fin_semana))
        .values("proyecto__id", "proyecto__nombre")
        .distinct()
    )

    total_general_per = total_general_ded = Decimal("0.00")

    for proj in proyectos:
        elementos.append(Paragraph(f"PROYECTO: {proj['proyecto__nombre']}", estilo_subtitulo))

        empleados_ids = (
            AsignacionDiaria.objects.filter(
                proyecto_id=proj["proyecto__id"],
                fecha__range=(fecha_inicio_semana, fecha_fin_semana)
            ).values_list("empleado_id", flat=True).distinct()
        )
        empleados = Empleado.objects.filter(id__in=empleados_ids).order_by("codigo")

        filas = []

        # Totales por columnas dentro del proyecto (iniciales en 0)
        col3 = col4 = col5 = col6 = col7 = Decimal("0.00")     # Percepciones
        col10 = col11 = col12 = Decimal("0.00")                 # Deducciones
        subtotal_neto = Decimal("0.00")

        for emp in empleados:
            item = next((x for x in nomina_data if x["empleado"] == emp.nombre), None)
            if not item:
                continue

            # --- Tomar valores por FILA ---
            sueldo_semanal  = Decimal(item.get("sueldo_semanal", 0) or 0)
            septimo_dia     = Decimal(item.get("septimo_dia", 0) or 0)
            comp_fija       = Decimal(item.get("compensacion_fija", 0) or 0)
            comp_variable   = Decimal(item.get("compensacion_variable", 0) or 0)
            horas_extras    = Decimal(item.get("horas_extras", 0) or 0)
            destajos        = Decimal(item.get("destajos", 0) or 0)
            importe_faltas  = Decimal(item.get("importe_faltas", 0) or 0)
            desc_7mo        = Decimal(item.get("descuento_septimo_dia", 0) or 0)

            compensacion_total = comp_fija + comp_variable
            total_per_fila = sueldo_semanal + septimo_dia + compensacion_total + horas_extras + destajos
            total_ded_fila = importe_faltas + desc_7mo
            total_neto_fila = total_per_fila - total_ded_fila

            # --- Acumular columnas por proyecto ---
            col3  += sueldo_semanal
            col4  += septimo_dia
            col5  += compensacion_total
            col6  += horas_extras
            col7  += destajos
            col10 += importe_faltas
            col11 += desc_7mo
            col12 += total_ded_fila
            subtotal_neto += total_neto_fila

            nombre = Paragraph(str(item.get("empleado", "")), estilo_empleado)
            filas.append([
                nombre,
                f"${Decimal(item.get('sueldo_diario', 0) or 0):,.2f}",               # 1 Sueldo Diario
                f"{item.get('dias_trabajados', 0)}",                                  # 2 Días Trabajados
                f"${sueldo_semanal:,.2f}",                                            # 3 Sueldo Percibido
                f"${septimo_dia:,.2f}",                                               # 4 Séptimo Día
                f"${compensacion_total:,.2f}",                                        # 5 Compensación (fija + variable)
                f"${horas_extras:,.2f}",                                              # 6 Horas Extra
                f"${destajos:,.2f}",                                                  # 7 Destajos
                f"${total_per_fila:,.2f}",                                            # 8 Total Percepciones
                f"{item.get('faltas', 0)}",                                           # 9 Faltas
                f"${importe_faltas:,.2f}",                                            # 10 Importe Falta
                f"${desc_7mo:,.2f}",                                                  # 11 Descuento 7° Día
                f"${total_ded_fila:,.2f}",                                            # 12 Total Deducciones (10+11)
                f"${total_neto_fila:,.2f}",                                           # Total Neto
                ""
            ])

        # ---------- Subtotal por PROYECTO (una sola fila) ----------
        subtotal_per = col3 + col4 + col5 + col6 + col7
        subtotal_ded = col12  # ya es (10+11) acumulado

        filas.append([
            Paragraph("<b>TOTALES PROYECTO</b>", estilo_empleado), "", "",
            f"${col3:,.2f}",                        # 3
            f"${col4:,.2f}",                        # 4
            f"${col5:,.2f}",                        # 5 (comp fija + variable)
            f"${col6:,.2f}",                        # 6
            f"${col7:,.2f}",                        # 7
            f"${subtotal_per:,.2f}",                # 8
            "",                                     # 9 Faltas (no se suma personas aquí)
            f"${col10:,.2f}",                       # 10
            f"${col11:,.2f}",                       # 11
            f"${subtotal_ded:,.2f}",                # 12
            f"${subtotal_neto:,.2f}",               # Total Neto
            ""
        ])

        # === Acumular totales generales ===
        total_general_per += subtotal_per
        total_general_ded += subtotal_ded

        data = [encabezados] + filas
        tabla = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 10))

    # === Totales generales ===
    total_neto_general = total_general_per - total_general_ded
    elementos.append(Spacer(1, 15))
    elementos.append(Paragraph("<b>TOTALES GENERALES DE LA SEMANA</b>", estilo_subtitulo))
    total_data = [[
        "", "TOTAL PERCEPCIONES", f"${total_general_per:,.2f}",
        "TOTAL DEDUCCIONES", f"${total_general_ded:,.2f}",
        "TOTAL NETO", f"${total_neto_general:,.2f}"
    ]]
    total_tabla = Table(total_data, colWidths=[100, 120, 100, 120, 100, 100, 120])
    total_tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    elementos.append(total_tabla)

    # === Generar PDF ===
    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


#============================================================================================
LOGO_PATH = "static/base/img/inemo.png"
#============================================================================================

@login_required(login_url='bases:login')
def generar_nomina_individual_pdf(request, fecha_str):
    """
    Genera PDF de recibos individuales de nómina (uno por empleado),
    con percepciones, deducciones, horas extras, destajos y subtabla de destajos_detalle.
    """
    try:
        fecha_inicio_semana = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha incorrecto.")
        return redirect('nom:seleccionar_fecha')

    fecha_fin_semana = fecha_inicio_semana + timedelta(days=6)

    # Calcular nómina
    resultados_calculo = calcular_nomina_semanal_todos(fecha_inicio_semana.strftime("%Y-%m-%d"))
    if not isinstance(resultados_calculo, dict) or 'nomina' not in resultados_calculo:
        messages.error(request, "Error al obtener datos de nómina.")
        return redirect('nom:seleccionar_fecha')

    nomina_data = resultados_calculo.get('nomina') or []
    if not nomina_data:
        messages.info(request, "No hay datos de nómina para este período.")
        return redirect('nom:seleccionar_fecha')

    # PDF Setup
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="nomina_individual_{fecha_str}.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    margen_izq, margen_der, margen_sup, margen_inf = 40, 40, 50, 50
    ancho_util = width - margen_izq - margen_der

    logo_path = os.path.join(settings.BASE_DIR, "static", "base", "img", "inemo.png")

    # -----------------------------------------------------------------------
    # DIBUJAR ENCABEZADO
    # -----------------------------------------------------------------------
    def dibujar_encabezado(empleado_data):
        y = height - margen_sup
        try:
            p.drawImage(ImageReader(logo_path), margen_izq, y - 50, width=100, height=50, mask="auto")
        except Exception as e:
            print(f"⚠ No se pudo cargar el logo: {e}")
        p.setFont("Helvetica-Bold", 14)
        p.drawString(margen_izq + 120, y - 20, "INEMO Constructora")
        p.setFont("Helvetica", 10)
        p.drawString(margen_izq + 120, y - 35, "RFC: IEM060621IE3")
        p.drawString(margen_izq + 120, y - 48, "Puerto Altata 590, Culiacán, Sinaloa")

        p.setFont("Helvetica-Bold", 12)
        p.drawString(margen_izq, y - 75, f"Recibo de Nómina - Semana del {fecha_inicio_semana.strftime('%d/%m/%Y')} al {fecha_fin_semana.strftime('%d/%m/%Y')}")

        p.setFont("Helvetica-Bold", 11)
        p.drawString(margen_izq, y - 100, f"Empleado: {empleado_data.get('empleado', '---')}")
        p.setFont("Helvetica", 10)
        p.drawString(margen_izq, y - 115, f"Fecha de Ingreso: {empleado_data.get('ingreso', '') or '---'}")

        return y - 140  # punto de partida para la tabla

    # -----------------------------------------------------------------------
    # DIBUJAR DETALLE DE NÓMINA
    # -----------------------------------------------------------------------
    def dibujar_detalle(empleado_data, y_inicio):
        """
        Dibuja las percepciones y deducciones del empleado.
        """
        cuadro_x = margen_izq
        cuadro_y = y_inicio - 220
        cuadro_ancho = ancho_util
        cuadro_alto = 200

        # Evita que se salga de la hoja
        if cuadro_y < 100:
            p.showPage()
            return dibujar_encabezado(empleado_data) - 220

        # Marco general
        p.setLineWidth(1)
        p.rect(cuadro_x, cuadro_y, cuadro_ancho, cuadro_alto)

        # Línea vertical divisoria (centro)
        centro_x = cuadro_x + (cuadro_ancho / 2)
        p.line(centro_x, cuadro_y, centro_x, cuadro_y + cuadro_alto)

        # Encabezados
        p.setFont("Helvetica-Bold", 12)
        p.drawString(cuadro_x + 15, cuadro_y + cuadro_alto - 20, "PERCEPCIONES")
        p.drawString(centro_x + 15, cuadro_y + cuadro_alto - 20, "DEDUCCIONES")

        # Percepciones
        p.setFont("Helvetica", 10)
        percepciones = [
            ("Sueldo diario", empleado_data.get('sueldo_diario', 0)),
            ("Días trabajados", empleado_data.get('dias_trabajados', 0)),
            ("Sueldo percibido", empleado_data.get('sueldo_semanal', 0)),
            ("Séptimo día", empleado_data.get('septimo_dia', 0)),
            ("Compensación", empleado_data.get('compensacion', 0)),
            ("Horas extras", empleado_data.get('horas_extras', 0)),
            ("Destajos", empleado_data.get('destajos', 0)),
        ]

        y_pos = cuadro_y + cuadro_alto - 45
        for nombre, valor in percepciones:
            if nombre == "Días trabajados":
                texto = f"{nombre}: {int(valor)}"
            else:
                texto = f"{nombre}: ${valor:,.2f}"
            p.drawString(cuadro_x + 15, y_pos, texto)
            y_pos -= 16

        total_percepciones = (
            empleado_data.get('sueldo_semanal', 0)
            + empleado_data.get('septimo_dia', 0)
            + empleado_data.get('compensacion', 0)
            + empleado_data.get('horas_extras', 0)
            + empleado_data.get('destajos', 0)
        )

        p.setFont("Helvetica-Bold", 10)
        p.drawString(cuadro_x + 15, y_pos - 4, f"TOTAL PERCEPCIONES: ${total_percepciones:,.2f}")

        # Deducciones
        y_pos = cuadro_y + cuadro_alto - 45
        deducciones = [
            ("Faltas", empleado_data.get('faltas', 0)),
            ("Descuento faltas", empleado_data.get('importe_faltas', 0)),
            ("Desc. 7mo día", empleado_data.get('descuento_septimo_dia', 0)),
        ]
        for nombre, valor in deducciones:
            if nombre == "Faltas":
                texto = f"{nombre}: {int(valor)}"
            else:
                texto = f"{nombre}: ${valor:,.2f}"
            p.drawString(centro_x + 15, y_pos, texto)
            y_pos -= 16

        total_deducciones = empleado_data.get('deducciones', 0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(centro_x + 15, y_pos - 4, f"TOTAL DEDUCCIONES: ${total_deducciones:,.2f}")

        return cuadro_y - 40

    # -----------------------------------------------------------------------
    # DIBUJAR SUBTABLA DE DESTAJOS
    # -----------------------------------------------------------------------
    def dibujar_subtabla_destajos(empleado_data, y_pos):
        destajos_detalle = empleado_data.get('destajos_detalle', [])
        if not destajos_detalle:
            return y_pos

        p.setFont("Helvetica-Bold", 10)
        p.drawString(margen_izq, y_pos, "Detalles de Destajos:")
        y_pos -= 14

        data = [["Obra", "Tipo", "Cantidad", "Factor", "Tarifa", "Total", "Descripción"]]
        for d in destajos_detalle:
            data.append([
                d.get("obra", ""),
                d.get("tipo", ""),
                f"{d.get('cantidad', 0):.2f}",
                f"{d.get('factor', 0):.2f}",
                f"{d.get('tarifa', 0):.2f}",
                f"${d.get('total', 0):.2f}",
                d.get("descripcion", ""),
            ])

        tabla = Table(data, colWidths=[70, 90, 45, 45, 55, 60, 180])
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ALIGN", (2, 1), (5, -1), "RIGHT"),
        ]))

        _, alto_tabla = tabla.wrap(ancho_util, 300)
        if y_pos - alto_tabla < 100:
            p.showPage()
            y_pos = dibujar_encabezado(empleado_data) - 14
        tabla.drawOn(p, margen_izq, y_pos - alto_tabla)
        return y_pos - alto_tabla - 20

    # -----------------------------------------------------------------------
    # DIBUJAR TOTAL Y FIRMA
    # -----------------------------------------------------------------------
    def dibujar_total_y_firma(empleado_data, y_pos):
        total_pago = empleado_data.get('total_pago', 0)
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(colors.darkblue)
        p.drawString(margen_izq, y_pos, f"TOTAL A PAGAR: ${total_pago:,.2f}")
        p.setFillColor(colors.black)

        # Firma
        p.line(margen_izq, y_pos - 40, margen_izq + 250, y_pos - 40)
        p.drawString(margen_izq, y_pos - 55, "Firma del empleado")
        return y_pos - 70

    # -----------------------------------------------------------------------
    # GENERAR PÁGINA POR EMPLEADO
    # -----------------------------------------------------------------------
    for idx, emp in enumerate(nomina_data):
        y_cursor = dibujar_encabezado(emp)
        y_cursor = dibujar_detalle(emp, y_cursor)
        y_cursor = dibujar_subtabla_destajos(emp, y_cursor)
        dibujar_total_y_firma(emp, y_cursor)
        if idx < len(nomina_data) - 1:
            p.showPage()

    p.save()
    return response



from io import BytesIO
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, legal
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from nomina.models import PeriodosNomina
from reportlab.platypus import Image
from django.conf import settings
import os



def exportar_periodos_pdf(request):
    """
    Genera un PDF profesional de los períodos de nómina con encabezado en todas las páginas.
    """
    periodos = PeriodosNomina.objects.all().order_by("anio", "semana")

    if not periodos.exists():
        return HttpResponse("No hay períodos de nómina registrados.", status=404)

    # === CONFIGURACIÓN GENERAL ===
    buffer = BytesIO()
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="periodos_nomina_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'

    width, height = landscape(legal)
    margen_izq, margen_der, margen_sup, margen_inf = 20, 40, 60, 50
    logo_path = os.path.join(settings.BASE_DIR, "static/base/img/inemo.png")

    # === ENCABEZADO Y PIE DE PÁGINA ===
    def header_footer(canvas, doc):
        canvas.saveState()
        logo_w, logo_h = 120, 50
        y_top = height - 50

        # Logo
        try:
            canvas.drawImage(ImageReader(logo_path), margen_izq, y_top - logo_h,
                             width=logo_w, height=logo_h, mask="auto")
        except Exception as e:
            print(f"⚠ No se pudo cargar el logo: {e}")

        # Título
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawCentredString(width / 2, y_top - 15, "REPORTE DE PERÍODOS DE NÓMINA")

        # Subtítulo
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(width / 2, y_top - 30, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        # Línea divisoria
        canvas.line(margen_izq, y_top - 50, width - margen_der, y_top - 50)

        # Pie de página
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margen_izq, 40, "INEMO Constructora • RFC: IEM060621IE3 • Puerto Altata 590, Culiacán, Sinaloa")

        page_num = canvas.getPageNumber()
        canvas.drawRightString(width - margen_der, 40, f"Página {page_num}")
        canvas.restoreState()

    # === DOCUMENTO ===
    doc = BaseDocTemplate(
        buffer,
        pagesize=landscape(legal),
        leftMargin=margen_izq,
        rightMargin=margen_der,
        topMargin=margen_sup + 40,
        bottomMargin=margen_inf + 20,
    )

    frame = Frame(
        margen_izq,
        margen_inf,
        width - margen_izq - margen_der,
        height - (margen_sup + margen_inf + 40),
        id="normal"
    )
    doc.addPageTemplates([PageTemplate(id="Periodos", frames=[frame], onPage=header_footer)])

    # === CONTENIDO ===
    elementos = []
    estilos = getSampleStyleSheet()
    estilo_normal = ParagraphStyle("normal", fontName="Helvetica", fontSize=9)
    estilo_centrado = ParagraphStyle("centrado", fontName="Helvetica", fontSize=9, alignment=1)
    estilo_titulo_tabla = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=9, alignment=1)

    # === ENCABEZADOS ===
    encabezados = [
        "Semana", "Inicio", "Fin", "Fecha de Corte",
        "Día de Pago", "Estatus", "Año"
    ]

    filas = [encabezados]

    for p in periodos:
        filas.append([
            Paragraph(str(p.semana), estilo_centrado),
            Paragraph(p.periodo_inicio.strftime("%d/%m/%Y"), estilo_centrado),
            Paragraph(p.periodo_final.strftime("%d/%m/%Y"), estilo_centrado),
            Paragraph(p.fecha_corte.strftime("%d/%m/%Y") if p.fecha_corte else "-", estilo_centrado),
            Paragraph(p.dia_pago.strftime("%d/%m/%Y") if p.dia_pago else "-", estilo_centrado),
            Paragraph(p.estatus, estilo_centrado),
            Paragraph(str(p.anio), estilo_centrado),
        ])

    # === TABLA ===
    col_widths = [70, 100, 100, 100, 100, 90, 70]
    tabla = Table(filas, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response



@login_required(login_url='bases:login')
def generar_nomina_asignaciones_pdf(request, fecha_inicio_str, fecha_fin_str):
    """
    Genera PDF agrupado por proyecto con empleados asignados y totales.
    """
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Formato de fecha incorrecto.")
        return redirect('nom:seleccionar_fecha')

    asignaciones = (
        AsignacionDiaria.objects
        .select_related('empleado', 'proyecto')
        .filter(fecha__range=(fecha_inicio, fecha_fin))
        .order_by('proyecto__nombre', 'empleado__nombre', 'fecha')
    )

    if not asignaciones.exists():
        messages.info(request, "No hay asignaciones en ese rango.")
        return redirect('nom:seleccionar_fecha')

    # Agrupar por proyecto
    proyectos_data = {}
    for a in asignaciones:
        proyecto = a.proyecto.nombre if a.proyecto else "SIN PROYECTO"
        if proyecto not in proyectos_data:
            proyectos_data[proyecto] = {}

        emp = a.empleado.nombre
        if emp not in proyectos_data[proyecto]:
            proyectos_data[proyecto][emp] = {'horas': 0, 'importe': Decimal('0.00'), 'sueldo': a.empleado.sueldo_diario}

        proyectos_data[proyecto][emp]['horas'] += float(a.horas_trabajadas or 0)
        proyectos_data[proyecto][emp]['importe'] += Decimal(a.empleado.sueldo_diario) * Decimal(a.horas_trabajadas or 0) / Decimal(8)

    # === PDF CONFIG ===
    buffer = BytesIO()
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="nomina_asignaciones_{fecha_inicio_str}_al_{fecha_fin_str}.pdf"'

    doc = SimpleDocTemplate(buffer, pagesize=landscape(legal), leftMargin=30, rightMargin=30, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=14, alignment=1, spaceAfter=10)
    estilo_subtitulo = ParagraphStyle('subtitulo', fontName='Helvetica-Bold', fontSize=11, spaceBefore=10, spaceAfter=6)
    estilo_normal = ParagraphStyle('normal', fontName='Helvetica', fontSize=9)

    elementos = []

    # Encabezado general
    titulo = f"NÓMINA DE ASIGNACIONES DEL {fecha_inicio.strftime('%d/%m/%Y')} AL {fecha_fin.strftime('%d/%m/%Y')}"
    elementos.append(Paragraph(titulo, estilo_titulo))
    elementos.append(Spacer(1, 8))

    total_general = Decimal('0.00')

    for proyecto, empleados in proyectos_data.items():
        elementos.append(Paragraph(f"Proyecto: {proyecto}", estilo_subtitulo))

        encabezados = ["Empleado", "Sueldo Diario", "Horas", "Importe"]
        filas = [encabezados]
        total_proyecto = Decimal('0.00')

        for emp, datos in empleados.items():
            filas.append([
                emp,
                f"${datos['sueldo']:,.2f}",
                f"{datos['horas']:.2f}",
                f"${datos['importe']:,.2f}",
            ])
            total_proyecto += datos['importe']

        filas.append(["", "", "TOTAL PROYECTO", f"${total_proyecto:,.2f}"])
        total_general += total_proyecto

        tabla = Table(filas, colWidths=[220, 100, 80, 100])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 10))

    # Total general al final
    elementos.append(Paragraph(f"<b>TOTAL GENERAL: ${total_general:,.2f}</b>", estilo_subtitulo))

    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response



from io import BytesIO
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from reportlab.lib.pagesizes import legal, landscape
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Table, TableStyle, Spacer
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from django.conf import settings
from nomina.models import (
    PeriodosNomina, NominaHistorial, NominaEmpleado,
    NominaDetalle, MovimientoCuentaProyecto
)
from django.contrib import messages
import os


from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from nomina.models import NominaHistorial, NominaEmpleado, MovimientoCuentaProyecto


def generar_auditoria_nomina_pdf(request, historial_id):
    historial = get_object_or_404(NominaHistorial, pk=historial_id)

    fecha_inicio = historial.periodo_inicio
    fecha_fin = historial.periodo_fin

    empleados_nomina = (
        NominaEmpleado.objects
        .filter(historial=historial)
        .select_related("empleado")
        .order_by("empleado__codigo")
    )

    movs = MovimientoCuentaProyecto.objects.filter(periodo=historial).select_related("proyecto", "empleado")
    proyectos_por_empleado = {m.empleado_id: m.proyecto.nombre if m.proyecto else "—" for m in movs}

    # === Crear PDF ===
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename=\"auditoria_nomina_{historial_id}.pdf\"'

    doc = SimpleDocTemplate(response, pagesize=letter, leftMargin=30, rightMargin=30, topMargin=60, bottomMargin=30)
    styles = getSampleStyleSheet()
    elementos = []

    # === LOGO ===
    logo_path = os.path.join(settings.BASE_DIR, "static/base/img/inemo.png")

    try:
        logo = Image(logo_path, width=120, height=50)  # ajusta tamaño si deseas
        elementos.append(logo)
    except Exception:
        elementos.append(Paragraph("INEMO Constructora", styles["Title"]))

    elementos.append(Spacer(1, 10))

    # === Encabezado del reporte ===
    elementos.append(Paragraph(f"<b>AUDITORÍA DE NÓMINA #{historial_id}</b>", styles["Title"]))
    elementos.append(Paragraph(f"Período: {fecha_inicio} al {fecha_fin}", styles["Normal"]))
    elementos.append(Paragraph(f"Estatus: {historial.estatus}", styles["Normal"]))
    elementos.append(Spacer(1, 15))

    # --- Encabezado de tabla ---
    data = [["Empleado", "Proyecto", "Percepciones", "Deducciones", "Neto"]]

    total_percepciones = 0
    total_deducciones = 0
    total_neto = 0

    for ne in empleados_nomina:
        empleado = ne.empleado
        proyecto_nombre = proyectos_por_empleado.get(empleado.id, "—")

        per = ne.total_percepciones or 0
        ded = ne.total_deducciones or 0
        neto = ne.total_neto or 0

        total_percepciones += per
        total_deducciones += ded
        total_neto += neto

        data.append([
            empleado.nombre,
            proyecto_nombre,
            f"${per:,.2f}",
            f"${ded:,.2f}",
            f"${neto:,.2f}",
        ])

    # --- Fila de totales ---
    data.append([
        "TOTALES",
        "",
        f"${total_percepciones:,.2f}",
        f"${total_deducciones:,.2f}",
        f"${total_neto:,.2f}",
    ])

    tabla = Table(data, colWidths=[180, 150, 90, 90, 90])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    elementos.append(tabla)

    doc.build(elementos)
    return response
