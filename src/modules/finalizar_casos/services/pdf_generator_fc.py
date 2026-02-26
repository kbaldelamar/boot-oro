"""
Generador de PDF de resultados de laboratorio clínico.
Módulo Finalizar Casos - Independiente de autorizar_anexo3 y laboratorio.

Réplica EXACTA del diseño del backend Flask (generar_pdf),
usando datos del API /consulta-encabezado en lugar de consultas SQL.

Estructura del PDF:
  1. Encabezado: Logo + NIT/Recepción/Sede
  2. Info usuario: Usuario/Documento, Edad/Sexo, Fecha/Autorización (con borde)
  3. Tabla resultados: 4 columnas (Estudios y Parámetros | Resultado | Valores Ref | Firma)
     - Agrupado por nombreProcedimiento
     - Firma (imagen + nombre + especialidad + T.P.) al final de cada grupo
  4. Pie de página: Dirección + Teléfono + Impreso por

Dependencias: reportlab (ya en requirements.txt)
"""
import os
import time
from collections import OrderedDict
from typing import Optional, Callable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)

from config.config import Config


class PDFGeneratorFC:
    """
    Genera PDFs de resultados de laboratorio clínico.
    Réplica exacta del diseño del backend Flask.
    """

    def __init__(self, log_function: Optional[Callable[[str], None]] = None):
        config = Config()

        self.logo_path = config.fc_logo_path
        self.firmas_path = config.fc_firmas_path
        self.output_dir = config.fc_pdf_output_dir

        self.log = log_function or print

        # Estilos base
        self.styles = getSampleStyleSheet()
        self.style_body = self.styles['BodyText']
        self.style_bold = ParagraphStyle(
            name='BoldLarge',
            parent=self.style_body,
            fontName='Helvetica-Bold',
            fontSize=8,
            spaceAfter=4,
        )

    # ==================================================================
    # Método público principal
    # ==================================================================

    def generar_pdf(self, id_recepcion: int, encabezado_data: dict) -> Optional[str]:
        """
        Genera el PDF de resultados de laboratorio.

        Args:
            id_recepcion: ID de la recepción
            encabezado_data: Dict 'data' de /consulta-encabezado

        Returns:
            Ruta absoluta del PDF generado, o None si falló.
        """
        try:
            self._limpiar_carpeta_salida()

            timestamp = int(time.time() * 1000)
            nombre_pdf = f"resultados_{id_recepcion}_{timestamp}.pdf"
            ruta_pdf = os.path.join(self.output_dir, nombre_pdf)

            doc = SimpleDocTemplate(ruta_pdf, pagesize=letter)
            story = []

            # Página 1 de 1
            story.append(Paragraph(
                "Página 1 de 1",
                ParagraphStyle(name='Right', parent=self.style_body, alignment=2),
            ))
            story.append(Spacer(1, 12))

            # 1. Encabezado (Logo + IPS)
            story.append(self._crear_encabezado(encabezado_data))
            story.append(Spacer(1, 12))

            # 2. Info del paciente
            story.append(self._crear_info_usuario(encabezado_data))
            story.append(Spacer(1, 12))

            # 3. Tabla de resultados
            story.append(self._crear_tabla_resultados(encabezado_data))
            story.append(Spacer(1, 12))

            # 4. Pie de página
            story.append(self._crear_pie_pagina(encabezado_data))

            # Construir
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

            if os.path.exists(ruta_pdf) and os.path.getsize(ruta_pdf) > 0:
                self.log(f"✅ PDF generado: {ruta_pdf} ({os.path.getsize(ruta_pdf)} bytes)")
                return ruta_pdf
            else:
                self.log("❌ Error: PDF no generado")
                return None

        except Exception as e:
            self.log(f"❌ Error generando PDF: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ==================================================================
    # Número de página
    # ==================================================================

    @staticmethod
    def _add_page_number(canvas, doc):
        """Agrega número de página al pie."""
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(7.5 * inch, 0.75 * inch, text)

    # ==================================================================
    # Limpieza
    # ==================================================================

    def _limpiar_carpeta_salida(self):
        """Elimina todos los archivos de la carpeta de salida antes de generar."""
        if os.path.exists(self.output_dir):
            for f in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, f)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                except Exception as e:
                    self.log(f"⚠️ No se pudo eliminar {filepath}: {e}")
        else:
            os.makedirs(self.output_dir, exist_ok=True)

    # ==================================================================
    # 1. Encabezado: Logo + NIT / Recepción / Sede
    # ==================================================================

    def _crear_encabezado(self, data: dict) -> Table:
        """Logo a la izquierda + datos IPS a la derecha."""
        nombre_ips = data.get('nombreIps', 'N/A')
        num_recepcion = data.get('numeroRecepcion', 'N/A')
        sede = data.get('sede', 'N/A')

        # Logo
        logo_element = self._cargar_logo()

        header_data = [
            [
                logo_element,
                [
                    Paragraph(f"<b>NIT.</b> {nombre_ips}", self.style_bold),
                    Paragraph(f"No. Recepción: {num_recepcion}", self.style_body),
                    Paragraph(f"Sede: {sede}", self.style_body),
                ]
            ]
        ]

        header_table = Table(header_data, colWidths=[150, 350])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        return header_table

    def _cargar_logo(self):
        """Carga el logo desde FC_LOGO_PATH. Retorna Image o Paragraph placeholder."""
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                return Image(self.logo_path, width=1.5 * inch, height=0.75 * inch)
            except Exception as e:
                self.log(f"⚠️ Error cargando logo: {e}")
                return Paragraph("<b>[LOGO NO DISPONIBLE]</b>", self.style_bold)
        else:
            if self.logo_path:
                self.log(f"⚠️ Logo no encontrado: {self.logo_path}")
            return Paragraph("<b>[LOGO NO ENCONTRADO]</b>", self.style_bold)

    # ==================================================================
    # 2. Info del usuario (3 filas con borde)
    # ==================================================================

    def _crear_info_usuario(self, data: dict) -> Table:
        """Tabla 3x2 con info del paciente y borde negro."""
        nombre = data.get('nombreUsuario', 'N/A')
        documento = data.get('numeroDocumento', 'N/A')
        edad = data.get('edad', 'N/A')
        sexo = data.get('idSexo', 'N/A')
        fecha = data.get('fechaRecep', 'N/A')
        autorizacion = data.get('numeroAutorizacion', 'N/A')

        user_data = [
            [
                Paragraph(f"<b>Usuario:</b> {nombre}", self.style_body),
                Paragraph(f"<b>Documento:</b> {documento}", self.style_body),
            ],
            [
                Paragraph(f"<b>Edad:</b> {edad}", self.style_body),
                Paragraph(f"<b>Sexo:</b> {sexo}", self.style_body),
            ],
            [
                Paragraph(f"<b>Fecha:</b> {fecha}", self.style_body),
                Paragraph(f"<b>Autorización:</b> {autorizacion}", self.style_body),
            ],
        ]

        user_table = Table(user_data, colWidths=[250, 250])
        user_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))

        return user_table

    # ==================================================================
    # 3. Tabla de resultados (4 columnas, agrupado por procedimiento)
    # ==================================================================

    def _crear_tabla_resultados(self, data: dict) -> Table:
        """
        4 columnas: ESTUDIOS Y PARÁMETROS | RESULTADO | VALORES DE REFERENCIA | FIRMA
        Agrupado por nombreProcedimiento.
        Firma al final de cada grupo (imagen + profesional + especialidad + T.P.)
        """
        table_data = [
            ["ESTUDIOS Y PARÁMETROS", "RESULTADO", "VALORES DE REFERENCIA", "FIRMA"]
        ]
        # Índices de filas que son firma (para aplicar SPAN)
        firma_rows = []

        list_detalle = data.get('listDetalle', [])

        # Agrupar por nombreProcedimiento manteniendo orden
        agrupados = OrderedDict()
        for d in list_detalle:
            key = d.get('nombreProcedimiento', 'Sin procedimiento')
            if key not in agrupados:
                agrupados[key] = {"protocolos": [], "firma": d}
            agrupados[key]["protocolos"].append(d)

        for idx, (nombre_proc, info) in enumerate(agrupados.items()):
            # Fila de encabezado del procedimiento (bold)
            table_data.append([
                Paragraph(f"<b>{nombre_proc}</b>", self.style_body),
                "", "", ""
            ])

            # Filas de protocolos/detalle
            for d in info["protocolos"]:
                nombre_protocolo = d.get('nombreProtocolo', '') or ''
                valor_resultado = d.get('valorResultado', '') or ''
                valor_unidad = d.get('valorUnidad', '') or ''
                valor_minimo = d.get('valorMinimo', '') or ''
                valor_maximo = d.get('valorMaximo', '') or ''

                resultado_text = f"{valor_resultado} {valor_unidad}".strip()
                referencia_text = (
                    f"{valor_minimo} - {valor_maximo}"
                    if valor_minimo or valor_maximo
                    else ''
                )

                table_data.append([
                    Paragraph(str(nombre_protocolo), self.style_body),
                    resultado_text,
                    referencia_text,
                    ""
                ])

            # Fila de firma al final del grupo (span all columns, right-aligned)
            firma_table = self._crear_bloque_firma(info["firma"], idx)
            firma_row_idx = len(table_data)
            firma_rows.append(firma_row_idx)
            table_data.append([firma_table, "", "", ""])

        # Construir tabla principal
        table = Table(table_data, colWidths=[250, 80, 120, 100])

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ]

        # SPAN firma rows across all 4 columns + align right
        for row_idx in firma_rows:
            style_cmds.append(('SPAN', (0, row_idx), (3, row_idx)))
            style_cmds.append(('ALIGN', (0, row_idx), (3, row_idx), 'RIGHT'))

        table.setStyle(TableStyle(style_cmds))

        return table

    # ==================================================================
    # Bloque de firma (imagen + profesional + especialidad + T.P.)
    # ==================================================================

    def _crear_bloque_firma(self, detalle: dict, idx: int) -> Table:
        """
        Bloque de firma como sub-tabla para insertar en la columna FIRMA.
        Réplica exacta del Flask: imagen + nombre + especialidad + T.P.
        """
        profesional = (
            detalle.get('profesional_Valida')
            or detalle.get('profesional_Graba', '')
        )
        tarjeta = (
            detalle.get('tarjetaProfesionalValida')
            or detalle.get('tarjetaProfesionalGraba', '')
        )
        url_firma = (
            detalle.get('url_FirmaValida')
            or detalle.get('url_FirmaGraba', '')
        )
        especialidad = (
            detalle.get('especialidad_Valida')
            or detalle.get('especialidad_Graba', '')
        )

        # Imagen de firma
        firma_element = self._cargar_firma(url_firma)

        # Sub-tabla con firma + textos
        firma_content = [
            [firma_element],
            [Paragraph(
                f"<b>{profesional or ''}</b>",
                ParagraphStyle(
                    name=f'FirmaNombre{idx}', parent=self.style_body,
                    alignment=1, fontSize=7
                ),
            )],
            [Paragraph(
                especialidad or '',
                ParagraphStyle(
                    name=f'FirmaEsp{idx}', parent=self.style_body,
                    alignment=1, fontSize=6
                ),
            )],
            [Paragraph(
                f"<b>T.P.:</b> {tarjeta if tarjeta else 'N/A'}",
                ParagraphStyle(
                    name=f'FirmaTarjeta{idx}', parent=self.style_body,
                    alignment=1, fontSize=6
                ),
            )],
        ]

        firma_table = Table(firma_content, colWidths=[200])
        firma_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))

        return firma_table

    def _cargar_firma(self, url_firma: Optional[str]):
        """Carga imagen de firma desde FC_FIRMAS_PATH + url_FirmaValida."""
        if url_firma:
            firma_path = os.path.join(self.firmas_path, url_firma)
            if os.path.exists(firma_path):
                try:
                    return Image(firma_path, width=1.5 * inch, height=0.6 * inch)
                except Exception as e:
                    self.log(f"⚠️ Error cargando firma {url_firma}: {e}")
                    return Paragraph("____________________", self.style_body)
            else:
                self.log(f"⚠️ Firma no encontrada: {firma_path}")
                return Paragraph("____________________", self.style_body)
        return Paragraph("____________________", self.style_body)

    # ==================================================================
    # 4. Pie de página
    # ==================================================================

    def _crear_pie_pagina(self, data: dict) -> Table:
        """Dirección + Teléfono + Impreso por."""
        direccion = data.get('direccionIps', 'N/A')
        telefono = data.get('numeroTelefonoIps', 'N/A')

        footer_data = [
            [
                Paragraph(f"Dirección: {direccion}", self.style_body),
                Paragraph(f"Teléfono: {telefono}", self.style_body),
            ],
            [
                Paragraph(
                    "Impreso por: GENOMA EMPRESARIAL CONSULTORES S.A.S - NIT 900825382-4",
                    self.style_body,
                ),
                "",
            ],
        ]

        footer_table = Table(footer_data, colWidths=[250, 250])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        return footer_table
