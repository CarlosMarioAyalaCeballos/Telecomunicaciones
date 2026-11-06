"""Generación de la hoja de vida del equipo en PDF (ReportLab)."""
import io
from datetime import datetime
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

PRIMARIO = colors.HexColor("#0f766e")  # teal petróleo, igual que la web
PRIMARIO_CLARO = colors.HexColor("#e3f1ef")
GRIS = colors.HexColor("#c3cfcc")

_base = getSampleStyleSheet()
ESTILOS = {
    "titulo": ParagraphStyle("titulo", parent=_base["Title"], fontSize=15, textColor=PRIMARIO, spaceAfter=2),
    "empresa": ParagraphStyle("empresa", parent=_base["Normal"], fontSize=10, alignment=TA_CENTER,
                              textColor=colors.HexColor("#444444")),
    "seccion": ParagraphStyle("seccion", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=10,
                              textColor=colors.white),
    "etiqueta": ParagraphStyle("etiqueta", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=8,
                               textColor=PRIMARIO, leading=10),
    "valor": ParagraphStyle("valor", parent=_base["Normal"], fontSize=8.5, leading=11),
    "firma": ParagraphStyle("firma", parent=_base["Normal"], fontSize=8.5, alignment=TA_CENTER),
    "celda": ParagraphStyle("celda", parent=_base["Normal"], fontSize=7.5, leading=9.5),
    "celda_h": ParagraphStyle("celda_h", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=7.5,
                              textColor=colors.white, leading=9.5),
}
ANCHO = letter[0] - 3 * cm


def _t(valor):
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, Decimal):
        return "$ " + f"{valor:,.0f}".replace(",", ".")
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    return escape(str(valor)).replace("\n", "<br/>")


def _seccion(titulo, espacio_despues=0):
    t = Table([[Paragraph(titulo, ESTILOS["seccion"])]], colWidths=[ANCHO])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARIO),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    bloque = [Spacer(1, 8), t] + ([Spacer(1, espacio_despues)] if espacio_despues else [])
    # El título nunca queda solo al final de una página
    for f in bloque:
        f.keepWithNext = True
    return bloque


def _pares(pares, columnas=2):
    """Tabla etiqueta/valor en `columnas` pares por fila."""
    filas, fila = [], []
    for etiqueta, valor in pares:
        fila += [Paragraph(etiqueta, ESTILOS["etiqueta"]), Paragraph(_t(valor), ESTILOS["valor"])]
        if len(fila) == columnas * 2:
            filas.append(fila)
            fila = []
    if fila:
        fila += [""] * (columnas * 2 - len(fila))
        filas.append(fila)
    ancho_et, ancho_val = ANCHO * 0.17, ANCHO * (1 / columnas - 0.17)
    t = Table(filas, colWidths=[ancho_et, ancho_val] * columnas)
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for c in range(0, columnas * 2, 2):
        estilo.append(("BACKGROUND", (c, 0), (c, -1), PRIMARIO_CLARO))
    t.setStyle(TableStyle(estilo))
    return t


def _tabla(encabezados, filas, anchos, vacio):
    if not filas:
        return Paragraph(f"<i>{vacio}</i>", ESTILOS["valor"])
    datos = [[Paragraph(h, ESTILOS["celda_h"]) for h in encabezados]]
    datos += [[Paragraph(_t(c), ESTILOS["celda"]) for c in fila] for fila in filas]
    t = Table(datos, colWidths=[ANCHO * a for a in anchos], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARIO),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
    ]))
    return t


def generar_hoja_vida(equipo, empresa, generado_por):
    buffer = io.BytesIO()
    generado = datetime.now()

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.5 * cm, 1 * cm,
                          f"Hoja de vida {equipo.codigo_activo} — generado el {generado:%d/%m/%Y %H:%M} por {generado_por}")
        canvas.drawRightString(letter[0] - 1.5 * cm, 1 * cm, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.3 * cm, bottomMargin=1.6 * cm,
                            title=f"Hoja de vida {equipo.codigo_activo}", author=empresa)
    h = []

    # --- Encabezado con foto ---
    encabezado = [Paragraph(escape(empresa), ESTILOS["empresa"]),
                  Paragraph("HOJA DE VIDA DE ACTIVO FIJO", ESTILOS["titulo"]),
                  Paragraph(f"<b>{escape(equipo.codigo_activo)}</b> — {escape(equipo.nombre)}", ESTILOS["empresa"])]
    foto = None
    if equipo.foto_datos:
        try:
            ancho, alto = ImageReader(io.BytesIO(equipo.foto_datos)).getSize()
            escala = min(3.2 * cm / ancho, 3.2 * cm / alto)
            foto = Image(io.BytesIO(equipo.foto_datos), width=ancho * escala, height=alto * escala)
        except Exception:
            foto = None
    if foto:
        t = Table([[encabezado, foto]], colWidths=[ANCHO - 3.6 * cm, 3.6 * cm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
        h.append(t)
    else:
        h += encabezado

    numero = iter(range(1, 20))

    def seccion(titulo, **kw):
        return _seccion(f"{next(numero)}. {titulo}", **kw)

    # --- Identificación ---
    h += seccion("IDENTIFICACIÓN DEL EQUIPO")
    h.append(_pares([
        ("Código de activo", equipo.codigo_activo), ("Nombre", equipo.nombre),
        ("Categoría", f"{equipo.categoria.nombre} ({equipo.categoria.grupo})"), ("Marca", equipo.marca),
        ("Modelo", equipo.modelo), ("N.º de serie", equipo.numero_serie),
        ("Part number", equipo.part_number), ("Estado", equipo.estado),
        ("Criticidad", equipo.criticidad), ("Fecha registro", equipo.creado_en),
    ]))

    # --- Cómputo y móviles ---
    if equipo.es_computo:
        h += seccion("CÓMPUTO Y DISPOSITIVO MÓVIL")
        h.append(_pares([
            ("Procesador", equipo.procesador), ("Memoria RAM", equipo.memoria_ram),
            ("Almacenamiento", equipo.almacenamiento), ("Pantalla", equipo.pantalla),
            ("Sistema operativo", equipo.sistema_operativo), ("Licencia SO", equipo.licencia_so),
            ("IMEI", equipo.imei),
            ("Línea / operador", " - ".join(filter(None, [equipo.numero_linea, equipo.operador_movil])) or None),
            ("Área", equipo.area), ("Accesorios", equipo.accesorios),
        ]))
        if equipo.software_instalado:
            h.append(Spacer(1, 4))
            h.append(_pares([("Software instalado", equipo.software_instalado)], columnas=1))

    # --- Técnica / red ---
    h += seccion("INFORMACIÓN TÉCNICA / RED")
    h.append(_pares([
        ("Dirección IP", equipo.direccion_ip), ("Dirección MAC", equipo.direccion_mac),
        ("Hostname", equipo.hostname), ("Firmware", equipo.firmware),
        ("Consumo energía", f"{equipo.consumo_energia_w} W" if equipo.consumo_energia_w is not None else None),
    ]))
    if equipo.especificaciones:
        h.append(Spacer(1, 4))
        h.append(_pares([("Especificaciones", equipo.especificaciones)], columnas=1))

    # --- Ubicación ---
    u = equipo.ubicacion
    h += seccion("UBICACIÓN Y RESPONSABLE")
    h.append(_pares([
        ("Sitio", u.nombre if u else None), ("Tipo de sitio", u.tipo if u else None),
        ("Dirección", u.direccion if u else None),
        ("Ciudad", f"{u.ciudad or ''}{' - ' + u.departamento if u and u.departamento else ''}" if u else None),
        ("Coordenadas", f"{u.latitud}, {u.longitud}" if u and u.latitud is not None else None),
        ("Rack / posición", equipo.rack_posicion),
        ("Asignado a" if equipo.es_computo else "Responsable", equipo.responsable), ("Fecha instalación", equipo.fecha_instalacion),
    ]))

    # --- Adquisición y financiera ---
    p = equipo.proveedor
    h += seccion("ADQUISICIÓN E INFORMACIÓN FINANCIERA")
    h.append(_pares([
        ("Proveedor", p.nombre if p else None), ("NIT proveedor", p.nit if p else None),
        ("Contacto proveedor", f"{p.contacto or ''} {p.telefono or ''}".strip() if p else None),
        ("Fecha adquisición", equipo.fecha_adquisicion),
        ("N.º factura", equipo.numero_factura), ("Orden de compra", equipo.orden_compra),
        ("Valor de compra", equipo.valor_compra), ("Valor residual", equipo.valor_residual),
        ("Vida útil", f"{equipo.vida_util_anios} años" if equipo.vida_util_anios else None),
        ("Años de uso", equipo.anios_uso),
        ("Depreciación anual", equipo.depreciacion_anual),
        ("Depreciación acumulada", equipo.depreciacion_acumulada),
        ("Valor en libros", equipo.valor_en_libros),
        ("Garantía hasta", f"{equipo.garantia_hasta:%d/%m/%Y} ({'vigente' if equipo.en_garantia else 'vencida'})"
         if equipo.garantia_hasta else None),
        ("Costo total mant.", equipo.costo_mantenimientos),
    ]))

    # --- Mantenimientos ---
    h += seccion(f"HISTORIAL DE MANTENIMIENTOS ({len(equipo.mantenimientos)})", espacio_despues=3)
    h.append(_tabla(
        ["Fecha", "Tipo", "Descripción", "Técnico", "Costo", "Próximo"],
        [[m.fecha, m.tipo, m.descripcion, m.tecnico, m.costo, m.proxima_fecha] for m in equipo.mantenimientos],
        [0.11, 0.13, 0.40, 0.14, 0.11, 0.11], "Sin mantenimientos registrados."))

    # --- Historial de eventos ---
    h += seccion("HISTORIAL DE EVENTOS Y MOVIMIENTOS", espacio_despues=3)
    h.append(_tabla(
        ["Fecha", "Evento", "Detalle", "Usuario"],
        [[ev.fecha.strftime("%d/%m/%Y %H:%M"), ev.accion, ev.detalle,
          ev.usuario.nombre if ev.usuario else None] for ev in equipo.historial],
        [0.15, 0.14, 0.53, 0.18], "Sin eventos registrados."))

    # --- Observaciones ---
    if equipo.observaciones:
        h += seccion("OBSERVACIONES", espacio_despues=3)
        h.append(Paragraph(_t(equipo.observaciones), ESTILOS["valor"]))

    # --- Firmas (en cómputo funciona como acta de entrega al usuario) ---
    if equipo.es_computo:
        firma_izq, firma_der = "Entregó", f"Recibió: {escape(equipo.responsable or '')}"
    else:
        firma_izq, firma_der = "Elaboró", "Revisó / Aprobó"
    firmas = Table([["", "", ""],
                    [Paragraph(firma_izq, ESTILOS["firma"]), "", Paragraph(firma_der, ESTILOS["firma"])]],
                   colWidths=[ANCHO * 0.4, ANCHO * 0.2, ANCHO * 0.4], rowHeights=[1.4 * cm, None])
    firmas.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (0, 1), 0.6, colors.black),
        ("LINEABOVE", (2, 1), (2, 1), 0.6, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    h.append(KeepTogether([Spacer(1, 18), firmas]))

    doc.build(h, onFirstPage=pie, onLaterPages=pie)
    return buffer.getvalue()
