import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

def generar_recibo_pdf(pago, renta):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)

    styles = getSampleStyleSheet()
    story  = []

    titulo = ParagraphStyle("titulo", fontSize=16, fontName="Helvetica-Bold",
                             spaceAfter=6, textColor=colors.HexColor("#224abe"))
    normal = styles["Normal"]
    bold   = ParagraphStyle("bold", fontSize=10, fontName="Helvetica-Bold")

    # Encabezado
    story.append(Paragraph("RECIBO DE PAGO", titulo))
    story.append(Paragraph(
        f"Folio: <b>{renta.folio_renta or renta.folio}</b> &nbsp;&nbsp; "
        f"Pago #: <b>{pago.pk}</b>", normal))
    story.append(Spacer(1, 0.4*cm))

    # Datos
    datos = [
        ["Cliente:",        str(renta.cliente)],
        ["Equipo:",         str(renta.equipo)],
        ["Fecha pago:",     pago.creado.strftime("%d/%m/%Y %H:%M") if hasattr(pago, "creado") else "—"],
        ["Método de pago:", pago.get_metodo_pago_display()],
        ["Referencia:",     pago.referencia or "—"],
        ["Importe pagado:", f"$ {pago.importe:,.2f}"],
        ["Saldo restante:", f"$ {renta.saldo:,.2f}"],
        ["Estatus:",        renta.get_estatus_financiero_display()],
    ]

    tabla = Table(datos, colWidths=[5*cm, 12*cm])
    tabla.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f9fc")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#e3e6f0")),
        ("PADDING",     (0, 0), (-1, -1), 6),
    ]))

    story.append(tabla)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Este documento es comprobante de pago.", normal))

    doc.build(story)
    buffer.seek(0)
    return buffer