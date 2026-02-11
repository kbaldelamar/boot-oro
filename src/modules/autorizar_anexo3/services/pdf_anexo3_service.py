"""
Servicio para generar PDF del Anexo 3 (Orden médica)
Replica EXACTAMENTE el formato oficial del Ministerio de Salud
"""
import os
import requests
from datetime import datetime
from pathlib import Path
from utils.paths import get_data_path, get_resource_path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PDFAnexo3Service:
    """Generador de PDF para Anexo 3 - Formato oficial del gobierno"""
    
    # Dimensiones página (Letter en puntos: 1 punto = 1/72 pulgada)
    PAGE_WIDTH = 612  # 8.5 pulgadas
    PAGE_HEIGHT = 792  # 11 pulgadas
    
    # Márgenes según formato oficial
    MARGIN_LEFT = 20
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    
    # Tamaño de casillas individuales (estándar gobierno)
    CELL_SIZE = 11.34  # Aproximadamente 4mm
    CELL_HEIGHT = 11.34
    
    # Colores
    COLOR_NEGRO = (0, 0, 0)
    COLOR_GRIS = (0.9, 0.9, 0.9)
    COLOR_BLANCO = (1, 1, 1)
    
    # Fuentes
    FONT_NORMAL = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"
    
    def __init__(self, logger, config):
        if fitz is None:
            raise ImportError("PyMuPDF no está instalado. Ejecute: pip install PyMuPDF")
        
        self.logger = logger
        self.config = config
        self.base_url = (config.api_url_programacion_base or 'http://localhost:5000').rstrip('/')
        
        # Directorio de salida de PDFs: runtime (escritura)
        pdf_dir = config.get('PDF_OUTPUT_DIR', '')
        if pdf_dir and Path(pdf_dir).is_absolute() and Path(pdf_dir).exists():
            self.pdf_output_dir = pdf_dir
        else:
            self.pdf_output_dir = str(get_data_path('temp/anexos3'))
        
        # Logo: recurso empaquetado (solo lectura)
        logo = config.get('ANEXO3_LOGO_PATH', '')
        if logo and Path(logo).exists():
            self.logo_path = logo
        else:
            self.logo_path = str(get_resource_path('resources/images/Anexo3.png'))
        
        # Firmas: recurso empaquetado (solo lectura)
        firmas = config.get('FIRMAS_PATH', '')
        if firmas and Path(firmas).exists():
            self.firmas_path = firmas
        else:
            self.firmas_path = str(get_resource_path('resources/images'))
        
        os.makedirs(self.pdf_output_dir, exist_ok=True)
    
    def generar_anexo3(self, id_atencion: int, id_orden: int, id_procedimiento: int) -> str:
        """Genera el PDF del Anexo 3 y retorna la ruta del archivo"""
        try:
            self.logger.info('PDFAnexo3', f"📄 Generando Anexo 3 - Atención: {id_atencion}, Orden: {id_orden}, CUPS: {id_procedimiento}")
            
            # 1. Obtener datos del endpoint
            url = f"{self.base_url}/datos-orden-atencion?idAtencion={id_atencion}&idOrden={id_orden}&idProcedimiento={id_procedimiento}"
            self.logger.info('PDFAnexo3', f"🌐 Consultando: {url}")
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Error en API: HTTP {response.status_code}")
            
            data_response = response.json()
            if data_response.get('statusCode') != 200:
                raise Exception(f"Error en respuesta: {data_response.get('message')}")
            
            datos = data_response.get('data', {})
            self.logger.info('PDFAnexo3', f"✅ Datos obtenidos - Paciente: {datos.get('Nombre1')} {datos.get('Apellido1')}")
            
            # 2. Generar nombre de archivo único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            no_documento = datos.get('NoDocumento', 'SinDoc')
            filename = f"Anexo3_{id_atencion}_{id_orden}_{no_documento}_{timestamp}.pdf"
            filepath = os.path.join(self.pdf_output_dir, filename)
            
            self.logger.info('PDFAnexo3', f"📝 Archivo destino: {filepath}")
            
            # 3. Crear PDF
            self._crear_pdf(filepath, datos)
            
            # 4. Verificar que se creó correctamente
            if not os.path.exists(filepath):
                raise Exception("PDF no se generó correctamente")
            
            tamaño = os.path.getsize(filepath)
            self.logger.info('PDFAnexo3', f"✅ PDF generado exitosamente ({tamaño} bytes)")
            
            return filepath
            
        except Exception as e:
            self.logger.error('PDFAnexo3', f"Error generando Anexo 3", e)
            raise

    def generar_anexo3_grupo(self, id_atencion: int, id_orden: int) -> str:
        """Genera el PDF del Anexo 3 para grupo de procedimientos"""
        try:
            self.logger.info(
                'PDFAnexo3',
                f"📄 Generando Anexo 3 (grupo) - Atención: {id_atencion}, Orden: {id_orden}"
            )

            url = f"{self.base_url}/datos-orden-atencion-sin-procedimiento?idAtencion={id_atencion}&idOrden={id_orden}"
            self.logger.info('PDFAnexo3', f"🌐 Consultando: {url}")

            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Error en API: HTTP {response.status_code}")

            data_response = response.json()
            if data_response.get('statusCode') != 200:
                raise Exception(f"Error en respuesta: {data_response.get('message')}")

            datos = data_response.get('data', {})
            self.logger.info(
                'PDFAnexo3',
                f"✅ Datos obtenidos - Paciente: {datos.get('Nombre1')} {datos.get('Apellido1')}"
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            no_documento = datos.get('NoDocumento', 'SinDoc')
            filename = f"Anexo3_Grupo_{id_atencion}_{id_orden}_{no_documento}_{timestamp}.pdf"
            filepath = os.path.join(self.pdf_output_dir, filename)

            self.logger.info('PDFAnexo3', f"📝 Archivo destino: {filepath}")

            self._crear_pdf(filepath, datos)

            if not os.path.exists(filepath):
                raise Exception("PDF no se generó correctamente")

            tamaño = os.path.getsize(filepath)
            self.logger.info('PDFAnexo3', f"✅ PDF generado exitosamente ({tamaño} bytes)")

            return filepath

        except Exception as e:
            self.logger.error('PDFAnexo3', f"Error generando Anexo 3 (grupo)", e)
            raise
    
    def _crear_pdf(self, filepath: str, datos: dict):
        """Crea el archivo PDF siguiendo el formato oficial"""
        doc = fitz.open()
        page = doc.new_page(width=self.PAGE_WIDTH, height=self.PAGE_HEIGHT)
        
        # Dibujar todo el formulario
        y = self.MARGIN_TOP
        
        # 1. Encabezado con logo
        y = self._dibujar_encabezado_oficial(page, y)
        
        # 2. Número de solicitud, fecha y hora
        y = self._dibujar_linea_solicitud(page, y, datos)
        
        # 3. Información del prestador
        y = self._dibujar_seccion_prestador(page, y, datos)
        
        # 4. Entidad pagadora
        y = self._dibujar_seccion_pagador(page, y, datos)
        
        # 5. Datos del paciente
        y = self._dibujar_seccion_paciente(page, y, datos)
        
        # 6. Información de la atención
        y = self._dibujar_seccion_atencion(page, y, datos)
        
        # 7. Procedimientos
        y = self._dibujar_seccion_procedimientos(page, y, datos)
        
        # 8. Diagnósticos
        y = self._dibujar_seccion_diagnosticos(page, y, datos)
        
        # 9. Profesional que solicita
        self._dibujar_seccion_profesional(page, y, datos)
        
        # Guardar
        doc.save(filepath)
        doc.close()
        self.logger.info('PDFAnexo3', "📄 PDF construido exitosamente")
    
    # =========================================================================
    # SECCIONES DEL FORMULARIO OFICIAL
    # =========================================================================
    
    def _dibujar_encabezado_oficial(self, page, y: float) -> float:
        """Dibuja el encabezado oficial con logo/escudo"""
        x_start = self.MARGIN_LEFT
        ancho_total = self.PAGE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT
        
        # Insertar imagen si existe
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                img_rect = fitz.Rect(x_start, y, x_start + ancho_total, y + 70)
                page.insert_image(img_rect, filename=str(self.logo_path))
                self.logger.info('PDFAnexo3', f"✅ Logo oficial cargado")
                return y + 75
            except Exception as e:
                self.logger.warning('PDFAnexo3', f"⚠️ Error cargando logo: {e}")
        
        # Si no hay logo, dibujar encabezado de texto
        # Escudo (simulado con texto)
        self._texto(page, x_start + 5, y + 20, "🇨🇴", 16)
        
        # Título centrado
        self._texto_centrado(page, x_start + 60, y + 5, ancho_total - 120,
                           "MINISTERIO DE SALUD Y PROTECCIÓN SOCIAL", 9, True)
        self._texto_centrado(page, x_start + 60, y + 20, ancho_total - 120,
                           "SOLICITUD DE AUTORIZACION DE SERVICIOS DE SALUD", 8, True)
        
        # ANEXO TECNICO No. 3 (arriba a la derecha)
        self._texto(page, self.PAGE_WIDTH - self.MARGIN_RIGHT - 100, y + 5,
                   "ANEXO TECNICO No. 3", 7, True)
        
        return y + 40
    
    def _dibujar_linea_solicitud(self, page, y: float, datos: dict) -> float:
        """Primera línea: NUMERO DE SOLICITUD | Fecha | Hora"""
        x = self.MARGIN_LEFT
        
        # NUMERO DE SOLICITUD
        self._texto(page, x, y, "NUMERO DE SOLICITUD", 7, True)
        x_casillas = x + 110
        id_orden = str(datos.get('IdOrden', '')).zfill(10)
        for i, char in enumerate(id_orden[:10]):
            self._casilla(page, x_casillas + (i * self.CELL_SIZE), y - 2, char)
        
        # Fecha
        x_fecha = x_casillas + (10 * self.CELL_SIZE) + 5
        self._texto(page, x_fecha, y, "Fecha:", 7, True)
        fecha = datos.get('FechaOrden', '')
        if fecha:
            # Formato: dd mm aaaa con separadores
            partes = fecha.split('-')  # ['2026', '01', '13']
            if len(partes) == 3:
                fecha_str = partes[2] + partes[1] + partes[0]  # ddmmaaaa
                x_f = x_fecha + 30
                # dd
                for i in range(2):
                    char = fecha_str[i] if i < len(fecha_str) else ''
                    self._casilla(page, x_f + (i * 10), y - 2, char, 10, 11)
                # separador
                self._texto(page, x_f + 22, y, "-", 7)
                # mm
                for i in range(2):
                    char = fecha_str[i + 2] if i + 2 < len(fecha_str) else ''
                    self._casilla(page, x_f + 27 + (i * 10), y - 2, char, 10, 11)
                # separador
                self._texto(page, x_f + 49, y, "-", 7)
                # aaaa
                for i in range(4):
                    char = fecha_str[i + 4] if i + 4 < len(fecha_str) else ''
                    self._casilla(page, x_f + 54 + (i * 10), y - 2, char, 10, 11)
        
        # Hora
        x_hora = self.PAGE_WIDTH - self.MARGIN_RIGHT - 90
        self._texto(page, x_hora, y, "Hora:", 7, True)
        hora = datos.get('Hora', '')
        if hora:
            hora_str = hora.replace(':', '')[:4]
            x_h = x_hora + 30
            for i, char in enumerate(hora_str[:4]):
                if i == 2:
                    self._texto(page, x_h + (i * self.CELL_SIZE) + 2, y, ":", 7)
                    self._casilla(page, x_h + (i * self.CELL_SIZE) + 7, y - 2, char)
                else:
                    self._casilla(page, x_h + (i * self.CELL_SIZE) + (7 if i > 2 else 0), y - 2, char)
        
        return y + 18
    
    def _dibujar_seccion_prestador(self, page, y: float, datos: dict) -> float:
        """INFORMACIÓN DEL PRESTADOR (solicitante)"""
        x = self.MARGIN_LEFT
        ancho = self.PAGE_WIDTH - 2 * self.MARGIN_LEFT
        
        # Título de sección
        self._titulo_seccion(page, x, y, ancho, "INFORMACIÓN DEL PRESTADOR (solicitante)")
        y += 14
        
        # Línea 1: Nombre en cuadro grande + checkboxes NIT/CC al lado + casillas número + DV
        nombre = self.config.get('NOMBREIPS', 'OROSALUD CAUCASIA IPS S.A.S')
        self._texto(page, x + 2, y, "Nombre", 7, True)
        # Cuadro grande para el nombre
        self._cuadro_texto(page, x + 45, y - 3, 200, 13, nombre)
        
        # Checkboxes NIT/CC al lado de las casillas (mismo nivel Y)
        x_check = x + 255
        self._checkbox_con_texto(page, x_check, y - 2, True, "NIT")
        self._checkbox_con_texto(page, x_check + 35, y - 2, False, "CC")
        
        # Casillas para número de NIT
        nit = self.config.get('NITIPS', '')
        x_casillas_nit = x_check + 70
        for i, char in enumerate(str(nit).zfill(9)[:9]):
            self._casilla(page, x_casillas_nit + (i * 10), y - 2, char, 10, 11)
        
        # Etiqueta "Número" en negrita arriba
        self._texto(page, x_casillas_nit + 20, y - 12, "Número", 6, True)
        
        # DV en cuadro separado
        x_dv = x_casillas_nit + (9 * 10) + 5
        self._texto(page, x_dv, y - 12, "DV", 6, True)
        self._casilla(page, x_dv, y - 2, '', 10, 11)
        
        y += 16
        
        # Línea 2: Código | Dirección prestador
        codigo = self.config.get('CODIGOIPS', '')
        self._texto(page, x + 2, y, "Código", 7, True)
        x_cod = x + 40
        for i, char in enumerate(str(codigo).ljust(12)[:12]):
            self._casilla(page, x_cod + (i * 10), y - 2, char, 10, 11)
        
        direccion = self.config.get('DIRECCIONIPS', '')
        x_dir = x_cod + (12 * 10) + 15
        self._texto(page, x_dir, y, "Dirección prestador", 7, True)
        self._cuadro_texto(page, x_dir + 100, y - 3, 200, 13, direccion)
        
        y += 16
        
        # Línea 3: Teléfono | Departamento | Municipio
        telefono = self.config.get('TELEFONOIPS', '')
        self._texto(page, x + 2, y, "Teléfono", 7, True)
        x_tel = x + 50
        for i, char in enumerate(str(telefono).ljust(10)[:10]):
            self._casilla(page, x_tel + (i * 10), y - 2, char, 10, 11)
        
        # Departamento
        x_dept = x_tel + (10 * 10) + 15
        self._texto(page, x_dept, y, "Departamento", 7, True)
        self._texto(page, x_dept + 65, y, "ANTIOQUIA", 7)
        self._casilla(page, x_dept + 125, y - 2, "0", 10, 11)
        self._casilla(page, x_dept + 135, y - 2, "5", 10, 11)
        
        # Municipio
        x_mun = x_dept + 155
        self._texto(page, x_mun, y, "Municipio", 7, True)
        self._texto(page, x_mun + 50, y, "CAUCASIA", 7)
        self._casilla(page, x_mun + 100, y - 2, "1", 10, 11)
        self._casilla(page, x_mun + 110, y - 2, "5", 10, 11)
        self._casilla(page, x_mun + 120, y - 2, "4", 10, 11)
        
        return y + 18
    
    def _dibujar_seccion_pagador(self, page, y: float, datos: dict) -> float:
        """ENTIDAD A LA QUE SE LE SOLICITA (PAGADOR)"""
        x = self.MARGIN_LEFT
        ancho = self.PAGE_WIDTH - 2 * self.MARGIN_LEFT
        
        self._titulo_seccion(page, x, y, ancho, "ENTIDAD A LA QUE SE LE SOLICITA (PAGADOR)")
        y += 14
        
        eps_nombre = datos.get('NEmpresa', 'COOSALUD EPS S.A')
        self._cuadro_texto(page, x + 2, y - 3, 380, 13, eps_nombre)
        
        # Código en negrita
        eps_codigo = datos.get('Codigo', 'ESS024')
        x_codigo = self.PAGE_WIDTH - self.MARGIN_RIGHT - 120
        self._texto(page, x_codigo, y, "Código", 7, True)
        x_cod = x_codigo + 40
        for i, char in enumerate(str(eps_codigo).ljust(6)[:6]):
            self._casilla(page, x_cod + (i * 10), y - 2, char, 10, 11)
        
        return y + 18
    
    def _dibujar_seccion_paciente(self, page, y: float, datos: dict) -> float:
        """DATOS DEL PACIENTE"""
        x = self.MARGIN_LEFT
        ancho = self.PAGE_WIDTH - 2 * self.MARGIN_LEFT
        
        self._titulo_seccion(page, x, y, ancho, "DATOS DEL PACIENTE")
        y += 14
        
        # Apellidos y nombres en CUADROS COMPLETOS
        apellido1 = datos.get('Apellido1', '').upper()
        apellido2 = datos.get('Apellido2', '').upper()
        nombre1 = datos.get('Nombre1', '').upper()
        nombre2 = datos.get('Nombre2', '').upper()
        
        # Cuadro para 1er Apellido
        self._cuadro_texto(page, x + 2, y, 130, 14, apellido1)
        # Cuadro para 2do Apellido
        self._cuadro_texto(page, x + 135, y, 130, 14, apellido2)
        # Cuadro para 1er Nombre
        self._cuadro_texto(page, x + 268, y, 130, 14, nombre1)
        # Cuadro para 2do Nombre
        self._cuadro_texto(page, x + 401, y, 130, 14, nombre2)
        
        y += 16
        # Etiquetas debajo de los cuadros
        self._texto(page, x + 45, y, "1er Apellido", 6, True)
        self._texto(page, x + 180, y, "2do Apellido", 6, True)
        self._texto(page, x + 315, y, "1er Nombre", 6, True)
        self._texto(page, x + 450, y, "2do Nombre", 6, True)
        
        y += 12
        
        # Tipo de Documento de identificación (2 columnas como en oficial)
        self._texto(page, x + 2, y, "Tipo de Documento de identificación", 7, True)
        
        tipo_doc = datos.get('Id_TipoIdentificacion', 'CC')
        
        # Columna 1 de checkboxes
        x_col1 = x + 10
        y_tipos = y + 12
        self._checkbox_con_texto(page, x_col1, y_tipos, tipo_doc == 'RC', "Registro civil")
        self._checkbox_con_texto(page, x_col1, y_tipos + 11, tipo_doc == 'TI', "Tarjeta de identidad")
        self._checkbox_con_texto(page, x_col1, y_tipos + 22, tipo_doc == 'CC', "Cédula de ciudadanía")
        self._checkbox_con_texto(page, x_col1, y_tipos + 33, tipo_doc == 'CE', "Cédula de extranjería")
        
        # Columna 2 de checkboxes
        x_col2 = x + 120
        self._checkbox_con_texto(page, x_col2, y_tipos, tipo_doc == 'PA', "Pasaporte")
        self._checkbox_con_texto(page, x_col2, y_tipos + 11, tipo_doc == 'AS', "Adulto sin identificación")
        self._checkbox_con_texto(page, x_col2, y_tipos + 22, tipo_doc == 'MS', "Menor sin identificación")
        
        # Número de documento (a la derecha)
        x_num_doc = x + 280
        no_doc = datos.get('NoDocumento', '')
        for i in range(10):
            char = no_doc[i] if i < len(no_doc) else ''
            self._casilla(page, x_num_doc + (i * 10), y_tipos, char, 10, 11)
        self._texto(page, x_num_doc, y_tipos - 10, "Número de documento de identificación", 6, True)
        
        # Fecha de Nacimiento - título y casillas al lado
        x_fecha = x + 330
        self._texto(page, x_fecha, y_tipos + 22, "Fecha de Nacimiento", 6, True)
        # Casillas para fecha al lado del título - usar FechaNac
        fecha_nac = datos.get('FechaNac', '')
        x_fn = x_fecha + 90
        if fecha_nac:
            partes = fecha_nac.split('-') if '-' in fecha_nac else []
            if len(partes) == 3:
                # Año
                for i in range(4):
                    char = partes[0][i] if i < len(partes[0]) else ''
                    self._casilla(page, x_fn + (i * 10), y_tipos + 20, char, 10, 11)
                self._texto(page, x_fn + 42, y_tipos + 27, "-", 7)
                # Mes
                for i in range(2):
                    char = partes[1][i] if i < len(partes[1]) else ''
                    self._casilla(page, x_fn + 50 + (i * 10), y_tipos + 20, char, 10, 11)
                self._texto(page, x_fn + 72, y_tipos + 27, "-", 7)
                # Día
                for i in range(2):
                    char = partes[2][i] if i < len(partes[2]) else ''
                    self._casilla(page, x_fn + 80 + (i * 10), y_tipos + 20, char, 10, 11)
        else:
            # Casillas vacías si no hay fecha
            for i in range(4):
                self._casilla(page, x_fn + (i * 10), y_tipos + 20, '', 10, 11)
            self._texto(page, x_fn + 42, y_tipos + 27, "-", 7)
            for i in range(2):
                self._casilla(page, x_fn + 50 + (i * 10), y_tipos + 20, '', 10, 11)
            self._texto(page, x_fn + 72, y_tipos + 27, "-", 7)
            for i in range(2):
                self._casilla(page, x_fn + 80 + (i * 10), y_tipos + 20, '', 10, 11)
        
        y = y_tipos + 50
        
        # Dirección de Residencia Habitual - título en un cuadro, valor en otro pegado
        direccion = datos.get('Direccion', 'ASOVIVIENDA')
        self._cuadro_texto(page, x + 2, y - 3, 155, 14, "Dirección de Residencia Habitual:")
        self._cuadro_texto(page, x + 157, y - 3, 200, 14, direccion)
        
        # Teléfono - título en un cuadro, valor en casillas pegadas
        telefono = datos.get('TelefonoPaciente', '')
        self._cuadro_texto(page, x + 365, y - 3, 50, 14, "Teléfono")
        for i in range(10):
            char = telefono[i] if i < len(telefono) else ''
            self._casilla(page, x + 415 + (i * 10), y - 2, char, 10, 11)
        
        y += 16
        
        # Departamento y Municipio - títulos en cuadros, valores en cuadros pegados
        # Departamento y Municipio - cuadros alineados
        self._cuadro_texto(page, x + 2, y - 3, 70, 14, "Departamento")
        self._cuadro_texto(page, x + 72, y - 3, 70, 14, "ANTIOQUIA")
        self._casilla(page, x + 142, y - 3, "0", 12, 14)
        self._casilla(page, x + 154, y - 3, "5", 12, 14)
        
        self._cuadro_texto(page, x + 175, y - 3, 55, 14, "Municipio")
        self._cuadro_texto(page, x + 230, y - 3, 65, 14, "CAUCASIA")
        self._casilla(page, x + 295, y - 3, "1", 12, 14)
        self._casilla(page, x + 307, y - 3, "5", 12, 14)
        self._casilla(page, x + 319, y - 3, "4", 12, 14)
        
        y += 18
        
        # Teléfono Celular - título en cuadro, valor de TelefonoPaciente en casillas
        telefono_cel = datos.get('TelefonoPaciente', '')
        self._cuadro_texto(page, x + 2, y - 3, 80, 14, "Teléfono Celular")
        for i in range(12):
            char = telefono_cel[i] if i < len(telefono_cel) else ''
            self._casilla(page, x + 82 + (i * 12), y - 3, char, 12, 14)
        
        # Correo electrónico
        self._cuadro_texto(page, x + 235, y - 3, 90, 14, "Correo electrónico")
        self._cuadro_texto(page, x + 325, y - 3, 205, 14, '')
        
        y += 16
        
        # Cobertura en Salud (más opciones como en formato oficial)
        regimen = datos.get('Regimen', '')
        self._texto(page, x + 2, y, "Cobertura en Salud", 7, True)
        
        # Fila 1
        y_cob = y
        self._checkbox_con_texto(page, x + 2, y_cob + 10, 'Contributivo' in regimen, "Regimen Contributivo")
        self._checkbox_con_texto(page, x + 120, y_cob + 10, False, "Regimen Subsidiado - parcial")
        self._checkbox_con_texto(page, x + 260, y_cob + 10, False, "Población Pobre no asegurada sin SISBEN")
        self._checkbox_con_texto(page, x + 460, y_cob + 10, False, "Plan adicional de salud")
        
        # Fila 2
        self._checkbox_con_texto(page, x + 2, y_cob + 22, 'Subsidiado' in regimen, "Regimen Subsidiado - total")
        self._checkbox_con_texto(page, x + 120, y_cob + 22, False, "Población pobre No asegurada con SISBEN")
        self._checkbox_con_texto(page, x + 320, y_cob + 22, False, "Desplazado")
        self._checkbox_con_texto(page, x + 400, y_cob + 22, False, "Otro")
        
        return y + 38
    
    def _dibujar_seccion_atencion(self, page, y: float, datos: dict) -> float:
        """INFORMACIÓN DE LA ATENCIÓN Y SERVICIOS SOLICITADOS"""
        x = self.MARGIN_LEFT
        ancho = self.PAGE_WIDTH - 2 * self.MARGIN_LEFT
        
        self._titulo_seccion(page, x, y, ancho, "INFORMACION DE LA ATENCION Y SERVICIOS SOLICITADOS")
        y += 14
        
        # Encabezados de las 3 columnas
        self._texto(page, x + 2, y, "Origen de la atención", 7, True)
        self._texto(page, x + 220, y, "Tipo de servicios solicitados", 7, True)
        self._texto(page, x + 420, y, "Prioridad de la atención", 7, True)
        
        y += 12
        causa = datos.get('CausaExterna', '')
        
        # Columna 1: Origen de la atención (2 filas)
        self._checkbox_con_texto(page, x + 2, y, 'General' in causa, "Enfermedad General")
        self._checkbox_con_texto(page, x + 100, y, False, "Accidente de Trabajo")
        self._checkbox_con_texto(page, x + 2, y + 11, False, "Enfermedad Profesional")
        self._checkbox_con_texto(page, x + 100, y + 11, False, "Accidente de Tránsito")
        
        # Columna 2: Tipo de servicios solicitados
        self._checkbox_con_texto(page, x + 220, y, False, "Evento Catastrófico")
        self._checkbox_con_texto(page, x + 320, y, False, "Posterior a la atención inicial de urgencias")
        self._checkbox_con_texto(page, x + 220, y + 11, False, "Servicios electivos")
        
        # Columna 3: Prioridad de la atención
        self._checkbox_con_texto(page, x + 500, y, False, "Prioritaria")
        self._checkbox_con_texto(page, x + 500, y + 11, False, "No prioritaria")
        
        y += 28
        
        # Ubicación del paciente
        tipo_atencion = datos.get('TipoAtencion', '')
        self._texto(page, x + 2, y, "Ubicación del Paciente al momento de la solicitud de autorización:", 7, True)
        
        y += 12
        self._checkbox_con_texto(page, x + 2, y, 'AMBULATORIO' in tipo_atencion or 'EXTERNA' in tipo_atencion, "Consulta Externa")
        self._checkbox_con_texto(page, x + 100, y, 'HOSPITALIZACION' in tipo_atencion, "Hospitalización")
        
        # Servicio y Cama
        self._texto(page, x + 200, y, "Servicio", 7, True)
        self._cuadro_texto(page, x + 245, y - 3, 180, 13, '')
        
        self._texto(page, x + 440, y, "Cama", 7, True)
        for i in range(5):
            self._casilla(page, x + 470 + (i * 12), y - 2, '', 12, 12)
        
        y += 14
        self._checkbox_con_texto(page, x + 2, y, 'URGENCIAS' in tipo_atencion, "Urgencias")
        
        return y + 16
    
    def _dibujar_seccion_procedimientos(self, page, y: float, datos: dict) -> float:
        """Manejo integral y tabla de procedimientos"""
        x = self.MARGIN_LEFT
        
        # Manejo integral
        self._texto(page, x + 2, y, "Manejo integral según guía de:", 7, True)
        
        y += 14
        
        # Encabezados de tabla
        self._texto(page, x + 10, y, "Código", 7, True)
        self._texto(page, x + 50, y, "Cantidad", 7, True)
        self._texto(page, x + 110, y, "Descripción", 7, True)
        self._texto(page, x + 380, y, "Número de caso", 7, True)
        self._texto(page, x + 10, y + 10, "CUPS", 7, True)
        
        y += 24
        
        procedimientos = datos.get('procedimientos')
        if procedimientos and isinstance(procedimientos, list):
            for idx, proc in enumerate(procedimientos, start=1):
                cups = proc.get('Id_Procedimiento', '')
                cantidad = str(proc.get('Cantidad', 1))
                descripcion = proc.get('NProcedimiento', '')
                numero_autorizacion = proc.get('numeroAutorizacion', '')

                self._texto(page, x + 10, y, f"{idx}  {cups}", 7)
                self._texto(page, x + 65, y, cantidad, 7)
                self._texto(page, x + 110, y, descripcion[:50], 6)
                self._texto(page, x + 380, y, numero_autorizacion, 7)

                y += 12

            y += 8
        else:
            # Datos individuales
            cups = datos.get('Id_Procedimiento', '881301')
            cantidad = str(datos.get('Cantidad', 1))
            descripcion = datos.get('NProcedimiento', '')
            numero_autorizacion = datos.get('numeroAutorizacion', '')
            
            self._texto(page, x + 10, y, f"1  {cups}", 7)
            self._texto(page, x + 65, y, cantidad, 7)
            self._texto(page, x + 110, y, descripcion[:50], 6)
            self._texto(page, x + 380, y, numero_autorizacion, 7)
            
            y += 20
        
        # Justificación Clínica
        justificacion = datos.get('NotaHc', '')
        self._texto(page, x + 2, y, "Justificación Clínica:", 7, True)
        y += 12
        self._texto(page, x + 2, y, justificacion[:80], 6)
        if len(justificacion) > 80:
            y += 10
            self._texto(page, x + 2, y, justificacion[80:160], 6)
        
        return y + 16
    
    def _dibujar_seccion_diagnosticos(self, page, y: float, datos: dict) -> float:
        """Impresión Diagnóstica"""
        x = self.MARGIN_LEFT
        ancho = self.PAGE_WIDTH - 2 * self.MARGIN_LEFT
        
        self._titulo_seccion(page, x, y, ancho, "Impresión Diagnóstica:")
        y += 14
        
        # Encabezados
        self._texto(page, x + 140, y, "Código CIE10", 7, True)
        self._texto(page, x + 230, y, "Descripción", 7, True)
        
        y += 12
        
        # Diagnóstico principal
        self._texto(page, x + 2, y, "Diagnóstico principal", 7, True)
        codigo_dx = datos.get('Codigo_Dxp', 'H920')
        for i, char in enumerate(codigo_dx.ljust(4)[:4]):
            self._casilla(page, x + 140 + (i * 11), y - 2, char, 11, 11)
        
        desc_dx = datos.get('P1', 'OTALGIA')
        self._texto(page, x + 230, y, desc_dx[:40], 6)
        
        y += 14
        
        # Diagnóstico relacionado 1
        self._texto(page, x + 2, y, "Diagnóstico relacionado 1", 7, True)
        codigo_dx1 = datos.get('Codigo_DxR1', 'R102')
        for i, char in enumerate(codigo_dx1.ljust(4)[:4]):
            self._casilla(page, x + 140 + (i * 11), y - 2, char, 11, 11)
        
        desc_dx1 = datos.get('P2', 'DOLOR PELVICO Y PERINEAL')
        self._texto(page, x + 230, y, desc_dx1[:40], 6)
        
        y += 14
        
        # Diagnóstico relacionado 2
        self._texto(page, x + 2, y, "Diagnóstico relacionado 2", 7, True)
        
        return y + 16
    
    def _dibujar_seccion_profesional(self, page, y: float, datos: dict) -> float:
        """INFORMACIÓN DE LA PERSONA QUE SOLICITA"""
        x = self.MARGIN_LEFT
        ancho = self.PAGE_WIDTH - 2 * self.MARGIN_LEFT
        
        self._titulo_seccion(page, x, y, ancho, "INFORMACION DE LA PERSONA QUE SOLICITA")
        y += 14
        
        profesional = datos.get('NProfesionalOrden', 'BARRIOS VERBEL JUAN JOSE')
        self._texto(page, x + 2, y, "Nombre de que solicita:", 7, True)
        self._texto(page, x + 115, y, profesional, 7)
        
        telefono_prof = datos.get('telefonoPOrden', '')
        x_tel = x + 380
        self._texto(page, x_tel, y, "Teléfono", 7, True)
        x_tel_casillas = x_tel + 45
        for i in range(10):
            char = telefono_prof[i] if i < len(telefono_prof) else ''
            self._casilla(page, x_tel_casillas + (i * 9), y - 2, char, 9, 11)
        
        y += 14
        
        # Indicativo, Número, Extensión - etiquetas en negrita
        self._texto(page, x + 100, y, "Indicativo", 6, True)
        self._texto(page, x + 220, y, "Número", 6, True)
        self._texto(page, x + 380, y, "Extensión", 6, True)
        
        y += 14
        
        # Firma del profesional (si existe DireccionF con nombre de imagen)
        firma_archivo = datos.get('DireccionF', '')
        if firma_archivo:
            # Construir ruta completa de la firma
            firma_path = os.path.join(self.firmas_path, firma_archivo)
            if os.path.exists(firma_path):
                try:
                    # Insertar imagen de firma arriba del R.M. (tamaño aprox 80x40)
                    firma_rect = fitz.Rect(x + 2, y - 5, x + 82, y + 35)
                    page.insert_image(firma_rect, filename=firma_path)
                    y += 40  # Espacio para la firma
                except Exception as e:
                    self.logger.warning(f"No se pudo insertar firma: {e}")
        
        # R.M. (Registro Médico)
        tarjeta = datos.get('Tarjeta', '10451383380')
        self._texto(page, x + 2, y, "R.M:", 7, True)
        self._texto(page, x + 25, y, tarjeta, 7)
        
        y += 14
        
        # Cargo y celular
        especialidad = datos.get('EspecialidadOrden', 'MEDICINA GENERAL')
        self._cuadro_texto(page, x + 2, y - 3, 80, 14, "Cargo o actividad:")
        self._cuadro_texto(page, x + 82, y - 3, 180, 14, especialidad)
        
        # Teléfono celular con valor de movilProfesional
        movil_prof = datos.get('movilProfesional', '')
        self._cuadro_texto(page, x + 280, y - 3, 80, 14, "Teléfono celular:")
        for i in range(10):
            char = movil_prof[i] if i < len(movil_prof) else ''
            self._casilla(page, x + 360 + (i * 12), y - 3, char, 12, 14)
        
        return y + 20
    
    # =========================================================================
    # HELPERS DE DIBUJO
    # =========================================================================
    
    def _titulo_seccion(self, page, x: float, y: float, ancho: float, texto: str):
        """Dibuja título de sección con fondo gris"""
        rect = fitz.Rect(x, y, x + ancho, y + 12)
        page.draw_rect(rect, color=self.COLOR_NEGRO, fill=self.COLOR_GRIS, width=0.5)
        page.insert_textbox(rect, texto, fontsize=7, fontname=self.FONT_BOLD,
                           align=fitz.TEXT_ALIGN_LEFT, color=self.COLOR_NEGRO)
    
    def _casilla(self, page, x: float, y: float, char: str, 
                 ancho: float = None, alto: float = None):
        """Dibuja una casilla individual con un carácter"""
        if ancho is None:
            ancho = self.CELL_SIZE
        if alto is None:
            alto = self.CELL_HEIGHT
        
        rect = fitz.Rect(x, y, x + ancho, y + alto)
        page.draw_rect(rect, color=self.COLOR_NEGRO, width=0.5)
        
        if char and char.strip():
            # Centrar carácter
            tx = x + (ancho - 5) / 2
            ty = y + alto - 2
            page.insert_text((tx, ty), str(char), fontsize=7,
                            fontname=self.FONT_NORMAL, color=self.COLOR_NEGRO)
    
    def _checkbox_con_texto(self, page, x: float, y: float, checked: bool, texto: str):
        """Dibuja checkbox con texto a la derecha, alineado verticalmente"""
        size = 8
        rect = fitz.Rect(x, y, x + size, y + size)
        page.draw_rect(rect, color=self.COLOR_NEGRO, width=0.5)
        
        if checked:
            # Dibujar X dentro del checkbox
            page.draw_line((x + 1, y + 1), (x + size - 1, y + size - 1),
                          color=self.COLOR_NEGRO, width=1)
            page.draw_line((x + size - 1, y + 1), (x + 1, y + size - 1),
                          color=self.COLOR_NEGRO, width=1)
        
        # Texto alineado verticalmente con el centro del checkbox
        # y + size/2 + fontsize/2 para centrar
        page.insert_text((x + size + 3, y + 6), str(texto), fontsize=6,
                        fontname=self.FONT_NORMAL, color=self.COLOR_NEGRO)
    
    def _texto(self, page, x: float, y: float, texto: str, 
               fontsize: float = 7, bold: bool = False):
        """Escribe texto"""
        font = self.FONT_BOLD if bold else self.FONT_NORMAL
        page.insert_text((x, y + fontsize), str(texto), fontsize=fontsize,
                        fontname=font, color=self.COLOR_NEGRO)
    
    def _texto_centrado(self, page, x: float, y: float, ancho: float, texto: str,
                        fontsize: float = 8, bold: bool = False):
        """Escribe texto centrado"""
        rect = fitz.Rect(x, y, x + ancho, y + 15)
        font = self.FONT_BOLD if bold else self.FONT_NORMAL
        page.insert_textbox(rect, str(texto), fontsize=fontsize, fontname=font,
                           align=fitz.TEXT_ALIGN_CENTER, color=self.COLOR_NEGRO)
    
    def _cuadro_texto(self, page, x: float, y: float, ancho: float, alto: float, texto: str):
        """Dibuja un cuadro con texto dentro (para nombres, direcciones, etc.)"""
        rect = fitz.Rect(x, y, x + ancho, y + alto)
        page.draw_rect(rect, color=self.COLOR_NEGRO, width=0.5)
        # Texto con un poco de padding
        page.insert_text((x + 3, y + alto - 3), str(texto), fontsize=7,
                        fontname=self.FONT_NORMAL, color=self.COLOR_NEGRO)
    
    def _cuadro_con_etiqueta(self, page, x: float, y: float, ancho: float, alto: float, 
                              etiqueta: str, valor: str):
        """Dibuja un cuadro con etiqueta en negrita y valor pegado dentro del mismo cuadro"""
        rect = fitz.Rect(x, y, x + ancho, y + alto)
        page.draw_rect(rect, color=self.COLOR_NEGRO, width=0.5)
        # Etiqueta en negrita
        page.insert_text((x + 3, y + alto - 3), str(etiqueta), fontsize=7,
                        fontname=self.FONT_BOLD, color=self.COLOR_NEGRO)
        # Valor pegado después de la etiqueta
        etiqueta_ancho = len(etiqueta) * 4  # Aproximar ancho de etiqueta
        page.insert_text((x + 5 + etiqueta_ancho, y + alto - 3), str(valor), fontsize=7,
                        fontname=self.FONT_NORMAL, color=self.COLOR_NEGRO)
