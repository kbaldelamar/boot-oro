"""
Ejecución de casos de Finalización - Módulo Finalizar Casos Laboratorio.
Migrado de Selenium a Playwright.
Clase independiente: NO depende de autorizar_anexo3 ni laboratorio.
"""
import os
import time
from typing import Tuple, Optional, Callable
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from config.config import Config
from modules.finalizar_casos.playwright.helpers_playwright_fc import PlaywrightHelperFC
from modules.finalizar_casos.services.finalizar_casos_service import FinalizarCasosService
from modules.finalizar_casos.services.pdf_generator_fc import PDFGeneratorFC
from modules.finalizar_casos.services.smb_service_fc import SMBServiceFC


class EjecutarCasosFC:
    """
    Ejecuta la lógica de finalización de casos en el portal de salud.
    
    Flujo por caso:
      1. Marcar en proceso (estado 2)
      2. Buscar caso en el portal
      3. Detectar estado (calendar / check / finalizado / ninguno)
      4. Actuar según estado
      5. Actualizar resultado
    """

    def __init__(
        self,
        page: Page,
        api_service: FinalizarCasosService,
        log_function: Optional[Callable[[str], None]] = None,
        pause_callback: Optional[Callable[[], bool]] = None,
    ):
        """
        Args:
            page: Página de Playwright (ya logueada y en Referencia Ambulatoria)
            api_service: Servicio API para consultas y actualizaciones
            log_function: Callback para logs (se envía a UI)
            pause_callback: Retorna True si el worker está pausado
        """
        self.page = page
        self.helper = PlaywrightHelperFC(page)
        self.api_service = api_service
        self.log_function = log_function or print
        self.pause_callback = pause_callback

        # Configuración desde .env
        config = Config()
        self.profesional = config.fc_profesional
        self.direccion = config.fc_direccion
        self.texto_observacion = config.fc_observacion

        # Generador de PDF
        self.pdf_generator = PDFGeneratorFC(log_function=self.log_function)

        # Servicio SMB para subir evidencias
        self.smb_service = SMBServiceFC(log_function=self.log_function)

        # Rutas de evidencias desde .env
        self.ruta_evidencia = config.ruta_evidencia
        self.ruta_genera_evidencia = config.ruta_genera_evidencia

    # ==================================================================
    # Verificación de pausa
    # ==================================================================

    def _verificar_pausa(self):
        """Verifica si el worker está pausado y lanza excepción si es así."""
        if self.pause_callback and self.pause_callback():
            self._log("⏸️ Ejecución pausada por el usuario")
            raise PausedException("Worker pausado durante ejecución")

    # ==================================================================
    # Método principal
    # ==================================================================

    def ejecutar_ingreso(self, data: dict) -> Tuple[bool, Optional[str]]:
        """
        Método principal: procesa un caso completo.
        
        Args:
            data: Dict con campos: caso, fecha, idOrden, idRecepcion, idIngreso, remision
            
        Returns:
            (True, None) si éxito, (False, error_msg) si falla
        """
        caso = str(data.get('caso', ''))
        id_orden = data.get('idOrden')
        self._log(f"📋 Iniciando ingreso caso: {caso}")

        try:
            self._verificar_pausa()

            # 1. Marcar en proceso
            self.api_service.marcar_en_proceso(id_orden)
            self._log(f"🔄 Caso {caso} marcado en proceso (estado 2)")

            time.sleep(1)

            # 2. Buscar caso
            self._buscar_caso(caso)
            time.sleep(3)
            self._clic_lupa()
            time.sleep(3)

            # 3. Detectar estado
            self._verificar_pausa()
            estado = self._detectar_estado(caso)
            self._log(f"🔍 Estado detectado: {estado}")
            time.sleep(2)

            # 4. Actuar según estado
            if estado == 'calendar':
                self._log("🗓️ Componente 'calendar' encontrado")
                try:
                    time.sleep(3)
                    self._metodo_boton_calendar(data)
                    time.sleep(3)
                    self._reiniciar_completo()
                    time.sleep(5)
                    self._verificar_pausa()
                    self._buscar_caso(caso)
                    time.sleep(2)
                    self._clic_lupa()
                    time.sleep(3)
                    self._metodo_boton_check(data)
                    time.sleep(2)
                    self._reiniciar()
                    time.sleep(2)
                except Exception as e:
                    self._log(f"❌ Error en flujo calendar: {e}")
                    raise

            elif estado == 'check':
                self._log("✅ Componente 'check' encontrado")
                try:
                    self._verificar_pausa()
                    self._metodo_boton_check(data)
                    time.sleep(2)
                    self._cerrar_panel_x()
                    time.sleep(2)
                    self._reiniciar()
                    time.sleep(2)
                except Exception as e:
                    self._log(f"❌ Error en flujo check: {e}")
                    raise

            elif estado == 'finalizado':
                self._log(f"🏁 El caso {caso} ya está en estado 'Finalizado'")
                try:
                    # Clic en ícono eye para abrir detalle del caso
                    eye_xpath = f"//td[contains(.,'{caso}')]/preceding-sibling::td/div//span[contains(@aria-label,'eye')]"
                    self.helper.click_element(eye_xpath, timeout=10000)
                    self._log("👁️ Clic en ícono eye para ver caso finalizado")
                    time.sleep(3)

                    # Capturar evidencia y subir a SMB
                    self._guardar_evidencia_y_subir(data)

                    # Marcar como exitoso (estado 1)
                    self.api_service.marcar_exitoso(id_orden)
                    self._log(f"✅ Caso {caso} finalizado — evidencia capturada (estado 1)")

                    self._cerrar_panel_x()
                    time.sleep(1)
                    self._reiniciar()
                    time.sleep(1)
                except Exception as e:
                    self._log(f"❌ Error procesando caso finalizado: {e}")
                    raise

            else:
                self._log("⚠️ Ningún componente encontrado")
                self.api_service.marcar_error(id_orden)
                time.sleep(1)
                self._reiniciar()
                time.sleep(1)

            return True, None

        except PausedException:
            raise
        except Exception as e:
            self._log(f"❌ Error en ejecutar_ingreso: {e}")
            # Intentar marcar como error crítico
            try:
                self.api_service.marcar_error_critico(id_orden)
            except Exception:
                pass
            return False, str(e)

    # ==================================================================
    # Búsqueda de caso
    # ==================================================================

    def _buscar_caso(self, caso: str):
        """Escribe el ID del caso en el input de búsqueda."""
        input_caso = self.page.wait_for_selector(
            "//input[contains(@name,'caseId')]", timeout=10000
        )
        if input_caso:
            input_caso.click()
            self.helper.ingresar_texto(input_caso, str(caso))
            self._log(f"📝 Ingresó caso: {caso}")
        else:
            raise Exception("Input caseId no encontrado")

    def _clic_lupa(self):
        """Clic en el botón de búsqueda (lupa)."""
        self.helper.click_element("//button[contains(@type,'submit')]", timeout=10000)
        self._log("🔍 Clic en botón lupa")

    # ==================================================================
    # Detección de estado
    # ==================================================================

    def _detectar_estado(self, caso: str) -> str:
        """
        Detecta el estado del caso buscando 3 componentes XPath.
        
        Returns:
            'calendar', 'check', 'finalizado' o 'ninguno'
        """
        xpaths = {
            'calendar': f"//td[contains(.,'{caso}')]/preceding-sibling::td/div//span[contains(@aria-label,'calendar')]",
            'check': f"//td[contains(.,'{caso}')]/preceding-sibling::td/div//span[contains(@aria-label,'check')]",
            'finalizado': f"//tr[@data-row-key='{caso}']//span[normalize-space()='Finalizado']",
        }

        for nombre, xpath in xpaths.items():
            if self._elemento_existe(xpath, timeout=10000):
                return nombre

        return 'ninguno'

    def _elemento_existe(self, xpath: str, timeout: int = 10000) -> bool:
        """Verifica si un elemento existe y es visible."""
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='visible', timeout=timeout)
            return locator.count() > 0
        except (PlaywrightTimeout, Exception):
            return False

    # ==================================================================
    # Botón Calendar: Asignar Cita
    # ==================================================================

    def _metodo_boton_calendar(self, data: dict) -> Tuple[bool, Optional[str]]:
        """
        Flujo del botón calendar: asignar cita al caso.
        - Profesional y dirección vienen del .env
        - Fecha viene de data
        """
        caso = str(data.get('caso', ''))
        fecha = str(data.get('fecha', ''))
        self._log("🗓️ Iniciando asignación de cita...")

        try:
            # Clic en ícono calendar
            xpath_calendar = f"//td[contains(.,'{caso}')]/preceding-sibling::td/div//span[contains(@aria-label,'calendar')]"
            self.helper.click_element(xpath_calendar)
            self._log("Clic en ícono calendar")
            time.sleep(1)

            # Clic en "Asignar Cita"
            self.helper.click_element("//span[contains(.,'Asignar Cita')]")
            self._log("Clic en 'Asignar Cita'")
            time.sleep(1)

            # Profesional (desde .env)
            input_profesional = self.page.wait_for_selector(
                "//input[contains(@name,'appointmentProfessionalName')]", timeout=10000
            )
            if input_profesional:
                input_profesional.click()
                self.helper.ingresar_texto(input_profesional, self.profesional)
                self._log(f"Ingresó profesional: {self.profesional}")
            time.sleep(1)

            # Fecha (desde data)
            input_fecha = self.page.wait_for_selector(
                "//input[contains(@placeholder,'YYYY-MM-DD HH:mm:ss')]", timeout=10000
            )
            if input_fecha:
                input_fecha.click()
                self.helper.ingresar_texto(input_fecha, fecha)
                self._log(f"Ingresó fecha: {fecha}")
            time.sleep(1)

            # Clic OK de fecha
            self.helper.click_element("//span[contains(.,'OK')]")
            self._log("Clic en OK de fecha")

            # Dirección (desde .env)
            input_direccion = self.page.wait_for_selector(
                "//input[contains(@name,'attentionHqIpsAddress')]", timeout=10000
            )
            if input_direccion:
                input_direccion.click()
                self.helper.ingresar_texto(input_direccion, self.direccion)
                self._log(f"Ingresó dirección: {self.direccion}")
            time.sleep(1)

            # Observación
            self._llenar_observacion()

            # Guardar
            self.helper.click_element("//span[contains(.,'Guardar')]")
            self._log("Clic en Guardar")

            # Esperar cierre del modal
            try:
                modals = self.page.locator("div.ant-modal-wrap")
                count = modals.count()
                for i in range(count):
                    modals.nth(i).wait_for(state='hidden', timeout=30000)
                self._log("✅ Modal de Asignar Cita cerrado correctamente")
            except PlaywrightTimeout:
                self._log("⚠️ El modal no se cerró a tiempo. Puede causar problemas después.")

            return True, None

        except Exception as e:
            self._log(f"❌ Error en metodo_boton_calendar: {e}")
            return False, str(e)

    # ==================================================================
    # Botón Check: Finalizar caso
    # ==================================================================

    def _metodo_boton_check(self, data: dict) -> Tuple[bool, Optional[str]]:
        """
        Flujo del botón check: finalizar caso.
        - Llena observación + clic "Asistida"
        - Si remision == 1: valida PDF remisión
        - Consulta encabezado para generar PDF
        - Sube PDF al portal
        """
        caso = str(data.get('caso', ''))
        id_orden = data.get('idOrden')
        id_recepcion = data.get('idRecepcion')
        remision = data.get('remision', 0)

        self._log(f"✅ Iniciando flujo check para caso {caso}...")

        try:
            # Clic en ícono check
            xpath_check = f"//td[contains(.,'{caso}')]/preceding-sibling::td/div//span[contains(@aria-label,'check')]"
            self.helper.click_element(xpath_check)
            self._log("Clic en ícono check")

            # Observación
            self._llenar_observacion()

            # Clic en "Asistida"
            self.helper.click_element("//span[contains(.,'Asistida')]")
            self._log("Clic en 'Asistida'")

            # --- Validar PDF de remisión si aplica ---
            archivo_remision = None
            path_remision_local = None

            if remision == 1:
                self._log(f"🔍 Verificando PDF de remisión para idRecepcion={id_recepcion}")
                response = self.api_service.buscar_pdf_remision(id_recepcion)

                if response is None:
                    # API no respondió en absoluto → error de API, saltar caso
                    self._log("❌ ERROR: API /buscar-pdf-remision no respondió (estado 15)")
                    self.api_service.marcar_error_api_remision(id_orden)
                    self._cerrar_panel_x()
                    time.sleep(1)
                    return True, None

                status_code = response.get('statusCode', 0)

                if status_code == 200:
                    # API respondió OK — extraer nombre del archivo
                    data_resp = response.get('data', {})
                    pdfs = data_resp.get('pdfs', [])
                    archivo_remision = pdfs[0].get('archivoResultadoExterno', '') if pdfs else ''

                    if archivo_remision:
                        # Tiene nombre de archivo → buscar y descargar desde SMB
                        self._log(f"📄 PDF remisión indicado por API: {archivo_remision}")
                        path_remision_local = self.smb_service.descargar_archivo_smb(
                            remote_filename=archivo_remision,
                            local_dest_path=self.ruta_genera_evidencia,
                        )

                        if not path_remision_local:
                            # Archivo no encontrado en SMB → estado 14, saltar caso
                            self._log(f"❌ PDF remisión no encontrado en servidor SMB (estado 14)")
                            self.api_service.marcar_remision_no_encontrada_smb(id_orden)
                            self._cerrar_panel_x()
                            time.sleep(1)
                            return True, None

                        self._log(f"✅ PDF remisión descargado: {archivo_remision}")
                    else:
                        # API 200 pero sin nombre de archivo → continuar normalmente sin remisión
                        self._log("ℹ️ API 200 pero sin nombre de PDF remisión. Continuando con PDF de resultados.")

                elif status_code == 404:
                    # No existe PDF de remisión para esta recepción → continuar normalmente
                    self._log(f"ℹ️ No hay PDF de remisión para idRecepcion={id_recepcion} (404). Continuando con PDF de resultados.")

                else:
                    # Error HTTP (400, 500, etc.) → error de API, saltar caso
                    self._log(f"❌ ERROR: API /buscar-pdf-remision respondió con status {status_code} (estado 15)")
                    self.api_service.marcar_error_api_remision(id_orden)
                    self._cerrar_panel_x()
                    time.sleep(1)
                    return True, None

            # --- Consultar encabezado para generar PDF ---
            self._log(f"📄 Consultando encabezado para idRecepcion={id_recepcion}")
            encabezado = self.api_service.consulta_encabezado(id_recepcion)

            if encabezado is None:
                self._log("❌ ERROR: consulta_encabezado no respondió")
                self.api_service.marcar_sin_pdf_resultados(id_orden)
                self._cerrar_panel_x()
                time.sleep(1)
                return True, None

            encabezado_status = encabezado.get('statusCode', 0)
            encabezado_data = encabezado.get('data', None)

            if encabezado_status != 200 or not encabezado_data:
                self._log(f"❌ ERROR: encabezado sin datos (status {encabezado_status})")
                self.api_service.marcar_sin_pdf_resultados(id_orden)
                self._cerrar_panel_x()
                time.sleep(1)
                return True, None

            self._log("✅ Datos de encabezado obtenidos correctamente")

            # --- Generar PDF ---
            # TODO: Implementar generación de PDF a partir de encabezado_data
            # El usuario proporcionará el código para esta parte
            pdf_path = self._generar_pdf(id_recepcion, encabezado_data)

            if pdf_path:
                # Subir PDF(s) al portal (resultados + remisión si aplica)
                if remision == 1 and path_remision_local:
                    self._subir_pdfs_portal([pdf_path, path_remision_local])
                    self._log(f"📤 PDFs cargados al portal: resultados + remisión")
                else:
                    self._subir_pdf_portal(pdf_path)
                time.sleep(2)

                # Guardar
                self.helper.click_element(
                    "//button[@type='button'][contains(.,'Guardar')]", timeout=20000
                )
                self._log("Clic en Guardar")
                time.sleep(3)

                # Confirmar modal swal2
                self.helper.click_element(
                    "//button[contains(@class,'swal2-confirm swal2-styled swal2-default-outline')]",
                    timeout=10000
                )
                self._log("Confirmación OK")
                time.sleep(2)

                # Marcar exitoso
                self.api_service.marcar_exitoso(id_orden)
                self._log(f"✅ Caso {caso} finalizado exitosamente (estado 1)")

                # Guardar evidencia y subir a SMB
                self._guardar_evidencia_y_subir(data)
            else:
                self._log(f"❌ No se pudo generar PDF para caso {caso}")
                self.api_service.marcar_sin_pdf_resultados(id_orden)

            return True, None

        except Exception as e:
            self._log(f"❌ Error en metodo_boton_check: {e}")
            self.api_service.marcar_error(id_orden)
            return False, str(e)

    # ==================================================================
    # Generación de PDF (PENDIENTE)
    # ==================================================================

    def _generar_pdf(self, id_recepcion: int, encabezado_data: dict) -> Optional[str]:
        """
        Genera el PDF de resultados delegando a PDFGeneratorFC.

        Args:
            id_recepcion: ID de la recepción
            encabezado_data: Datos completos del paciente y resultados

        Returns:
            Ruta del PDF generado, o None si no se pudo generar
        """
        self._log(f"📄 Generando PDF para idRecepcion={id_recepcion}")
        return self.pdf_generator.generar_pdf(id_recepcion, encabezado_data)

    # ==================================================================
    # Subir PDF al portal
    # ==================================================================

    def _subir_pdf_portal(self, pdf_path: str):
        """Sube un archivo PDF al portal vía input type='file'."""
        try:
            file_input = self.page.locator("//input[contains(@type,'file')]")
            file_input.set_input_files(pdf_path)
            self._log(f"📤 PDF cargado al portal: {pdf_path}")
            time.sleep(1)
        except Exception as e:
            self._log(f"❌ Error subiendo PDF al portal: {e}")
            raise

    def _subir_pdfs_portal(self, pdf_paths: list):
        """Sube múltiples archivos PDF al portal vía input type='file'."""
        try:
            file_input = self.page.locator("//input[contains(@type,'file')]")
            file_input.set_input_files(pdf_paths)
            self._log(f"📤 {len(pdf_paths)} PDFs cargados al portal")
            time.sleep(1)
        except Exception as e:
            self._log(f"❌ Error subiendo PDFs al portal: {e}")
            raise

    # ==================================================================
    # Guardar evidencia y subir a SMB
    # ==================================================================

    def _guardar_evidencia_y_subir(self, data: dict):
        """
        Captura evidencia de la página finalizada y la sube al servidor SMB.

        Flujo:
          1. Screenshot completa de la página (PNG)
          2. Convertir PNG → PDF
          3. POST /ingreso-documento → obtener Id
          4. Renombrar PDF: {Id}_{idIngreso}_EvidenciaExitoCaso.pdf
          5. Copiar PDF al servidor SMB
          6. PUT /ingreso-documento/{Id} → actualizar Ruta

        Si algún paso falla, marca el estado correspondiente (8-13)
        y continúa con el siguiente caso.
        """
        id_ingreso = data.get('idIngreso')
        id_orden = data.get('idOrden')

        self._log(f"📸 Iniciando captura de evidencia para idIngreso={id_ingreso}")

        # Asegurar que las carpetas locales existan
        os.makedirs(self.ruta_evidencia, exist_ok=True)
        os.makedirs(self.ruta_genera_evidencia, exist_ok=True)

        # ----- Paso 1: Captura de pantalla completa -----
        try:
            nombre_img = f"{id_ingreso}_EvidenciaExitoCaso.png"
            path_img = os.path.join(self.ruta_evidencia, nombre_img)
            self.page.screenshot(path=path_img, full_page=True)
            self._log(f"✅ Screenshot capturada: {path_img}")
        except Exception as e:
            self._log(f"❌ Error capturando screenshot (estado 8): {e}")
            self.api_service.marcar_error_captura_evidencia(id_orden)
            return

        # ----- Paso 2: Convertir PNG → PDF -----
        try:
            nombre_pdf_temp = f"{id_ingreso}_EvidenciaExitoCaso.pdf"
            path_pdf_temp = os.path.join(self.ruta_genera_evidencia, nombre_pdf_temp)

            from fpdf import FPDF
            from PIL import Image as PILImage

            img = PILImage.open(path_img)
            img_w, img_h = img.size

            pdf = FPDF()
            pdf.add_page()
            # Ajustar imagen al ancho de la página con margen
            page_w = pdf.w - 20  # 10mm margen cada lado
            ratio = page_w / img_w
            page_h = img_h * ratio

            # Si la imagen es muy alta, paginar
            if page_h > (pdf.h - 20):
                page_h = pdf.h - 20

            pdf.image(path_img, x=10, y=10, w=page_w, h=page_h)
            pdf.output(path_pdf_temp, "F")

            self._log(f"✅ PDF temporal generado: {path_pdf_temp}")
        except Exception as e:
            self._log(f"❌ Error generando PDF de evidencia (estado 9): {e}")
            self.api_service.marcar_error_pdf_evidencia(id_orden)
            return

        # ----- Paso 3: POST /ingreso-documento -----
        try:
            response = self.api_service.crear_ingreso_documento(id_ingreso)

            if response is None:
                raise Exception("API no respondió")

            status_code = response.get('statusCode', 0)
            if status_code != 201:
                raise Exception(f"Status inesperado: {status_code}")

            id_generado = response.get('data', {}).get('Id')
            if not id_generado:
                raise Exception("No se recibió Id en la respuesta")

            self._log(f"✅ Registro creado en BD, Id={id_generado}")
        except Exception as e:
            self._log(f"❌ Error creando registro en BD (estado 10): {e}")
            self.api_service.marcar_error_crear_registro(id_orden)
            return

        # ----- Paso 4: Renombrar PDF -----
        try:
            nombre_final = f"{id_generado}_{id_ingreso}_EvidenciaExitoCaso.pdf"
            path_pdf_final = os.path.join(self.ruta_genera_evidencia, nombre_final)

            os.rename(path_pdf_temp, path_pdf_final)
            self._log(f"✅ PDF renombrado: {nombre_final}")
        except Exception as e:
            self._log(f"❌ Error renombrando PDF (estado 11): {e}")
            self.api_service.marcar_error_renombrar(id_orden)
            return

        # ----- Paso 5: Subir a SMB -----
        try:
            exito_smb = self.smb_service.subir_evidencia(path_pdf_final, nombre_final)

            if not exito_smb:
                raise Exception("subir_evidencia retornó False")

            metodo = self.smb_service.ultimo_metodo or 'desconocido'
            if metodo == 'smb':
                self._log(f"✅ PDF subido a SMB: {nombre_final}")
            else:
                self._log(f"⚠️ PDF guardado en FALLBACK LOCAL (SMB no disponible): {nombre_final}")
        except Exception as e:
            self._log(f"❌ Error subiendo a SMB (estado 12): {e}")
            self.api_service.marcar_error_smb(id_orden)
            return

        # ----- Paso 6: PUT /ingreso-documento/{Id} -----
        try:
            exito_ruta = self.api_service.actualizar_ruta_documento(
                id_generado, nombre_final
            )

            if not exito_ruta:
                raise Exception("actualizar_ruta_documento retornó False")

            self._log(f"✅ Ruta actualizada en BD: {nombre_final}")
        except Exception as e:
            self._log(f"❌ Error actualizando ruta en BD (estado 13): {e}")
            self.api_service.marcar_error_actualizar_ruta(id_orden)
            return

        self._log(f"🎉 Evidencia completa para idIngreso={id_ingreso}: {nombre_final}")

    # ==================================================================
    # Observación
    # ==================================================================

    def _llenar_observacion(self):
        """Escribe el texto de observación en el textarea."""
        input_obs = self.page.wait_for_selector(
            "//textarea[contains(@rows,'4')]", timeout=10000
        )
        if input_obs:
            input_obs.click()
            self.helper.ingresar_texto(input_obs, self.texto_observacion)
            self._log(f"📝 Observación ingresada: {self.texto_observacion}")

    # ==================================================================
    # Navegación / Reinicio
    # ==================================================================

    def _reiniciar(self):
        """Reinicia navegando a Referencia urgente → Referencia Ambulatoria."""
        self._clic_menu("//span[@class='ant-menu-title-content'][contains(.,'Referencia urgente')]")
        time.sleep(3)
        self._clic_menu("//span[@class='ant-menu-title-content'][contains(.,'Referencia Ambulatoria')]")
        self._log("🔄 Reinicio completado")

    def _reiniciar_completo(self):
        """Reinicio completo: Servicios de salud x2 → Ref. urgente → Ref. Ambulatoria."""
        time.sleep(2)
        self._clic_menu("//div[@role='menuitem'][contains(.,'Servicios de salud')]")
        time.sleep(2)
        self._clic_menu("//div[@role='menuitem'][contains(.,'Servicios de salud')]")
        time.sleep(2)
        self._clic_menu("//span[@class='ant-menu-title-content'][contains(.,'Referencia urgente')]")
        time.sleep(2)
        self._clic_menu("//span[@class='ant-menu-title-content'][contains(.,'Referencia Ambulatoria')]")
        time.sleep(3)
        self._log("🔄 Reinicio completo finalizado")

    # ==================================================================
    # Cerrar modal
    # ==================================================================

    def _cerrar_panel_x(self):
        """Cierra el modal (X) si está presente."""
        xpath_x = "//span[contains(@class,'ant-modal-close-x')]"
        if self._elemento_existe(xpath_x, timeout=3000):
            self._clic_menu(xpath_x)
            self._log("❌ Panel cerrado con X")
            time.sleep(1)

    # ==================================================================
    # Helpers internos
    # ==================================================================

    def _clic_menu(self, xpath: str):
        """Clic genérico en un elemento por XPath."""
        self.helper.click_element(xpath, timeout=15000)

    def _log(self, mensaje: str):
        """Envía log al callback."""
        if self.log_function:
            self.log_function(mensaje)
        print(f"[EjecutarCasosFC] {mensaje}")


# ==================================================================
# Excepciones propias del módulo
# ==================================================================

class PausedException(Exception):
    """Excepción lanzada cuando el worker está en pausa."""
    def __init__(self, message="Ejecución pausada por el usuario"):
        self.message = message
        super().__init__(self.message)
