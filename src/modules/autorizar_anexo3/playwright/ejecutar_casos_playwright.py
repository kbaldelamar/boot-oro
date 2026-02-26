"""
Ejecución de casos completos con Playwright
Migración desde ejecutarCasos.py de Selenium
USANDO XPATHS EXACTOS DE SELENIUM QUE FUNCIONAN
"""
import time
import os
import datetime
import re
import requests
from typing import Dict, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from utils.logger import AdvancedLogger
from modules.autorizar_anexo3.playwright.helpers_playwright import PlaywrightHelper
from modules.autorizar_anexo3.playwright.ingreso_items_playwright import IngresoItemsPlaywright
from modules.autorizar_anexo3.services.pdf_anexo3_service import PDFAnexo3Service
from config.config import config  # Usar el singleton de config existente


class SessionLostException(Exception):
    """Excepción personalizada para cuando se pierde la sesión del navegador"""
    def __init__(self, message="La sesión del navegador se ha perdido"):
        self.message = message
        super().__init__(self.message)


class PausedException(Exception):
    """Excepción lanzada cuando el worker está en pausa y debe detener la ejecución actual"""
    def __init__(self, message="Ejecución pausada por el usuario"):
        self.message = message
        super().__init__(self.message)


class EjecutarCasosPlaywright:
    """Servicio para ejecutar casos completos de pacientes - USANDO XPATHS DE SELENIUM"""
    
    def __init__(self, page: Page, logger: AdvancedLogger, pause_callback=None):
        """
        Args:
            page: Página de Playwright
            logger: Logger
            pause_callback: Función que retorna True si el worker está pausado
        """
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelper(page)
        self.ingreso_items = IngresoItemsPlaywright(page, logger)
        self.pdf_service = PDFAnexo3Service(logger, config)
        self.modo_actual = config.get('MODE', 'REGULAR')  # CAPITATED o REGULAR
        self.pause_callback = pause_callback  # Callback para verificar pausa
        print(f"Modo actual de operación: {self.modo_actual}")
    
    def _verificar_pausa(self):
        """Verifica si el worker está pausado y lanza excepción si es así"""
        if self.pause_callback and self.pause_callback():
            self.logger.info('EjecutarCaso', '⏸️ Ejecución pausada por el usuario')
            raise PausedException("Worker pausado durante ejecución")
    
    @staticmethod
    def _es_telefono_valido(telefono: str) -> bool:
        """Valida que un teléfono tenga 10 dígitos y empiece con 3."""
        return bool(telefono) and len(telefono) == 10 and telefono.startswith('3') and telefono.isdigit()
    
    def inicio_casos(self, data) -> bool:
        """
        MÉTODO PRINCIPAL - Migrado de Selenium
        Ejecuta el caso completo de un paciente.
        """
        telefono_value = None
        telefono_value1 = None
        texto = None
        telefono_final = None  # Se determinará después de leer el formulario
        
        try:
            self._verificar_pausa()  # Verificar pausa al inicio
            self.verificar_sesion_activa(data, "Error: Sesión del navegador no está activa al inicio del proceso de casos")
            
            self.logger.info('EjecutarCaso', f"tipoIdentificacion: {data.tipoIdentificacion}")
            print(data.tipoIdentificacion)
            
            # ====== SELECCIÓN DE TIPO DE IDENTIFICACIÓN ======
            if data.tipoIdentificacion == "Cédula de Ciudadanía":
                # Cédula es la opción por defecto o está visible sin scroll
                self.comboIdentidad()
                dynamic_xpath = f"//div[@class='ant-select-item-option-content'][contains(.,'{data.tipoIdentificacion}')]"
                combo_tipo_identidad = self.esperar_y_clickear(dynamic_xpath)
                if not combo_tipo_identidad:
                    for i in range(4):
                        self.verificar_sesion_activa(data, "DURANTE SCROLL DE IDENTIFICACIÓN")
                        self.scroll_list_to(100 * (i + 1))
                        combo_tipo_identidad = self.esperar_y_clickear(dynamic_xpath)
                        if combo_tipo_identidad:
                            break
                if combo_tipo_identidad:
                    self.logger.info('EjecutarCaso', f"Clicked on combo tipo identidad dinámico: {data.tipoIdentificacion}")
                else:
                    self.logger.warning('EjecutarCaso', f"Elemento no fue clickeable después de intentar scroll.")
            else:
                # Para otros tipos: abrir combo y buscar directo con scroll (como Selenium)
                self.comboIdentidad()
                self.page.wait_for_selector('.rc-virtual-list-holder', timeout=5000)
                option = self.scroll_list_and_find_option(data.tipoIdentificacion)
                time.sleep(1)
                if option:
                    self.click_option(option)
                    self.logger.info('EjecutarCaso', f"Opción '{data.tipoIdentificacion}' seleccionada con éxito.")
                else:
                    self.logger.warning('EjecutarCaso', f"No se pudo encontrar la opción: {data.tipoIdentificacion}")
            
            # ====== VERIFICACIÓN DE SESIÓN ANTES DE CONTINUAR ======
            self._verificar_pausa()  # Verificar pausa
            self.verificar_sesion_activa(data, "DESPUÉS DE SELECCIÓN DE IDENTIFICACIÓN")
            
            # ====== INGRESO DE NÚMERO DE IDENTIFICACIÓN ====== (XPATH SELENIUM EXACTO)
            input_identidad_inicio = self.page.wait_for_selector("//input[contains(@name,'numeroDocumento')]", timeout=5000)
            self.helper.ingresar_texto(input_identidad_inicio, str(data.identificacion))
            self.logger.info('EjecutarCaso', f"ingreso input : {data.identificacion}")
            
            time.sleep(1)
            # XPATH SELENIUM EXACTO para botón buscar
            boton_buscar = self.page.wait_for_selector("//button[@width='100%'][contains(.,'Buscar')]", timeout=5000)
            boton_buscar.click()
            self.logger.info('EjecutarCaso', "Clicked on buton buscar")
            time.sleep(2)
            
            # ====== VERIFICACIÓN DE ERRORES DESPUÉS DE BÚSQUEDA ======
            componentes = ["//div/h2[contains(.,'Error')]"]
            for componente in componentes:
                texto = self.obtener_texto_componente(componente)
                if texto is not None:
                    print(texto)
                    break
            
            if texto is not None:
                # Verificar sesión antes de manejar error
                self.verificar_sesion_activa(data, "AL MANEJAR ERROR DE BÚSQUEDA")
                
                # XPATH SELENIUM EXACTO para botón OK
                bonton_ok = self.page.wait_for_selector("body > div.swal2-container.swal2-center.swal2-backdrop-show > div > div.swal2-actions > button.swal2-confirm.swal2-styled", timeout=5000)
                print("bonton_ok")
                bonton_ok.click()
                self.logger.info('EjecutarCaso', f"clic boton bonton_ok")
                self.actualizar(data, "4", "") # error al encontrar el tipo de docuemento 
                self.reinicio()
                return False  # ERROR: tipo de documento incorrecto
            else:
                # ====== LLENADO DE FORMULARIO PRINCIPAL ======
                self._verificar_pausa()  # Verificar pausa
                self.verificar_sesion_activa(data, "ANTES DE LLENAR FORMULARIO")
                
                # Correo (XPATH SELENIUM EXACTO)
                input_correo = self.page.wait_for_selector("#email", timeout=5000)
                input_correo.click()
                self.logger.info('EjecutarCaso', "Clicked on email input")
                input_correo.fill("")
                # Usar email del paciente si existe, sino usar fallback
                email_paciente = getattr(data, 'email', None) or getattr(data, 'correo', None) or "Notiene@gmail.com"
                self.helper.ingresar_texto(input_correo, email_paciente)
                self.logger.info('EjecutarCaso', f"Ingresó {email_paciente}")
                
                # Nombre de emergencia (XPATH SELENIUM EXACTO)
                input_nombre_e = self.page.wait_for_selector("#emergencyContactName", timeout=5000)
                input_nombre_e.click()
                input_nombre_e.fill("")
                self.helper.ingresar_texto(input_nombre_e, "emergencia")
                self.logger.info('EjecutarCaso', f"Ingresó emergencia")
                
                # === TELÉFONO PRINCIPAL - Lógica 3 niveles ===
                # 1) Leer valor actual del campo en el formulario (RAW y limpio)
                input_telefono = self.page.wait_for_selector("#telefono", timeout=5000)
                telefono_form_raw = input_telefono.get_attribute('value') or ''
                telefono_form = telefono_form_raw.strip()
                telefono_data = str(data.telefono).strip() if hasattr(data, 'telefono') else ''

                if self._es_telefono_valido(telefono_form):
                    # El formulario tiene un teléfono válido (después de strip)
                    telefono_final = telefono_form
                    if telefono_form_raw != telefono_form:
                        # Valor válido pero con espacios/basura → limpiar campo
                        input_telefono.click()
                        input_telefono.fill("")
                        self.helper.ingresar_texto(input_telefono, telefono_final)
                        self.logger.info('EjecutarCaso', f"✅ Teléfono del formulario limpiado: '{telefono_form_raw}' → '{telefono_final}'")
                    else:
                        self.logger.info('EjecutarCaso', f"✅ Teléfono del formulario válido, se conserva: {telefono_form}")
                elif self._es_telefono_valido(telefono_data):
                    # El formulario no tiene válido, pero la data sí → colocar
                    telefono_final = telefono_data
                    input_telefono.click()
                    input_telefono.fill("")
                    self.helper.ingresar_texto(input_telefono, telefono_final)
                    self.logger.info('EjecutarCaso', f"✅ Teléfono corregido desde data: '{telefono_form_raw}' → '{telefono_final}'")
                else:
                    # Ninguno tiene teléfono válido → saltar
                    self.logger.warning('EjecutarCaso', f"⚠️ TELÉFONO INVÁLIDO - formulario: '{telefono_form_raw}', data: '{telefono_data}' (debe ser 10 dígitos, empezar con 3)")
                    self.logger.warning('EjecutarCaso', f"   Paciente: {data.identificacion} - Orden: {data.idItemOrden}")
                    self.actualizar(data, "20", "")
                    self.reinicio()
                    return False

                # Teléfono de emergencia - usar el teléfono final determinado
                input_telefono_1 = self.page.wait_for_selector("#emergencyContactPhone", timeout=5000)
                telefono_emer_raw = input_telefono_1.get_attribute('value') or ''
                telefono_emer = telefono_emer_raw.strip()

                if not self._es_telefono_valido(telefono_emer):
                    # No válido → reemplazar con el teléfono final
                    input_telefono_1.click()
                    input_telefono_1.fill("")
                    self.helper.ingresar_texto(input_telefono_1, telefono_final)
                    self.logger.info('EjecutarCaso', f"✅ Teléfono emergencia corregido: '{telefono_emer_raw}' → '{telefono_final}'")
                elif telefono_emer_raw != telefono_emer:
                    # Válido pero con espacios → limpiar
                    input_telefono_1.click()
                    input_telefono_1.fill("")
                    self.helper.ingresar_texto(input_telefono_1, telefono_emer)
                    self.logger.info('EjecutarCaso', f"✅ Teléfono emergencia limpiado: '{telefono_emer_raw}' → '{telefono_emer}'")
                else:
                    self.logger.info('EjecutarCaso', f"✅ Teléfono emergencia válido, se conserva: {telefono_emer}")
                
                # Dirección principal (XPATH SELENIUM EXACTO)
                dirreccion = self.page.wait_for_selector("#root > div > section > section > section > main > div.w-100.col > div > div > div > form > div > div > div > div:nth-child(3) > div:nth-child(2) > input", timeout=5000)
                dirreccion_value1 = dirreccion.get_attribute('value')
                self.logger.info('EjecutarCaso', f"Valor actual del campo dirrecion: {dirreccion_value1}")
                
                if dirreccion_value1:
                    self.logger.info('EjecutarCaso', "El campo de dirección tiene un valor.")
                else:
                    self.logger.info('EjecutarCaso', "El campo de dirección está vacío.")
                    dirreccion.click()
                    dirreccion.fill("")
                    self.helper.ingresar_texto(dirreccion, "calle 10")
                    self.logger.info('EjecutarCaso', f"Ingresó dirrecion")
                
                # Dirección alternativa (XPATH SELENIUM EXACTO)
                dirreccionAlter = self.page.wait_for_selector("#alternativeDirectionForCare", timeout=5000)
                dirreccion_value2 = dirreccionAlter.get_attribute('value')
                self.logger.info('EjecutarCaso', f"Valor actual del campo dirrecionAlt: {dirreccion_value2}")
                
                if dirreccion_value2:
                    self.logger.info('EjecutarCaso', "El campo de dirección alternativa tiene un valor.")
                else:
                    self.logger.info('EjecutarCaso', "El campo de dirección alternativa está vacío.")
                    dirreccionAlter.click()
                    dirreccionAlter.fill("")
                    self.helper.ingresar_texto(dirreccionAlter, "calle 10")
                    self.logger.info('EjecutarCaso', f"Ingresó dirrecion")
                
                # ====== VERIFICACIÓN DE SESIÓN ANTES DE CONTINUAR CON FECHA ======
                self._verificar_pausa()  # Verificar pausa
                self.verificar_sesion_activa(data, "ANTES DE INGRESAR FECHA")
                
                # Fecha de orden (XPATH SELENIUM EXACTO)
                self.page.evaluate("window.scrollBy(0, 400);")
                time.sleep(1)
                input_fecha_orden = self.page.wait_for_selector("//input[contains(@placeholder,'Select date')]", timeout=5000)
                input_fecha_orden.click()
                self.logger.info('EjecutarCaso', "Clicked on date input")
                input_fecha_orden.fill("")
                self.helper.ingresar_texto(input_fecha_orden, data.fechaFacturaEvento)
                input_fecha_orden.press("Enter")
                self.logger.info('EjecutarCaso', f"Ingresó la fecha: {data.fechaFacturaEvento}")
                time.sleep(0.5)
                
                # IPS REMITENTE (XPATH SELENIUM EXACTO CON MÚLTIPLES CANDIDATOS)
                try:
                    input_IPSREMITE = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* IPS Remitente:')]/parent::div/div/div", timeout=5000)
                    input_IPSREMITE.click()
                    self.logger.info('EjecutarCaso', "Clicked on IPS Remitente input")
                    time.sleep(0.5)
                    
                    # IPS Remitente: construir CANDIDATOS igual que Selenium
                    nit_config = (config.nit_ips or "").strip()
                    nombre_config = (config.nombre_ips or "").strip()
                    
                    # Construir lista de candidatos (igual que Selenium para máxima compatibilidad)
                    candidatos = []
                    if nit_config:
                        candidatos.append(nit_config)
                    if nit_config and nombre_config:
                        candidatos.append(f"{nit_config} - {nombre_config}")
                        candidatos.append(f"{nit_config}-{nombre_config}")
                    if nombre_config:
                        candidatos.append(nombre_config)
                    
                    if not candidatos:
                        raise Exception("No se encontró NITIPS/NOMBREIPS en configuración")
                    
                    self.logger.info('EjecutarCaso', f"Candidatos para búsqueda: {candidatos}")
                    
                    # Intentar con cada candidato hasta encontrar la opción
                    seleccion_realizada = False
                    ultima_excepcion = None
                    
                    for search_text in candidatos:
                        try:
                            self.logger.info('EjecutarCaso', f"Intentando con candidato: '{search_text}'")
                            
                            # Limpiar input y escribir nuevo texto
                            input_IPSREMITE.click()
                            time.sleep(0.3)
                            
                            if not self.helper.ingresar_texto_secuencial(input_IPSREMITE, search_text):
                                self.logger.info('EjecutarCaso', f"No se pudo ingresar texto: '{search_text}'")
                                continue
                            
                            time.sleep(2)
                            try:
                                # Esperar el dropdown específico de ipsSender
                                self.page.wait_for_selector("//div[@id='ipsSender_list']", timeout=5000)
                                self.logger.info('EjecutarCaso', f"Dropdown ipsSender_list detectado")
                            except:
                                self.logger.info('EjecutarCaso', "Dropdown no apareció, reintentando")
                                input_IPSREMITE.click()
                                time.sleep(1)
                            
                            # Buscar opción con XPath MÁS SIMPLE - buscar en CUALQUIER dropdown visible
                            # Esto funciona porque el dropdown de ipsSender es el único abierto en este momento
                            opciones_a_buscar = [
                                f"//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]//div[@class='ant-select-item-option-content'][contains(.,'{search_text}')]",
                                f"//div[@class='ant-select-item-option-content'][contains(.,'{search_text}')]"
                            ]
                            
                            option = None
                            for xpath_opcion in opciones_a_buscar:
                                try:
                                    option = self.page.wait_for_selector(xpath_opcion, timeout=3000)
                                    self.logger.info('EjecutarCaso', f"Opción encontrada: {xpath_opcion}")
                                    break
                                except:
                                    continue
                            
                            if option:
                                option.click()
                                self.logger.info('EjecutarCaso', f"✅ IPS Remitente seleccionada con: '{search_text}'")
                                seleccion_realizada = True
                                break
                            else:
                                self.logger.info('EjecutarCaso', f"No encontrada con '{search_text}', probando siguiente...")
                                
                        except Exception as inner_e:
                            ultima_excepcion = inner_e
                            self.logger.info('EjecutarCaso', f"Error con candidato '{search_text}': {inner_e}")
                            continue
                    
                    if not seleccion_realizada:
                        # Listar opciones disponibles para debug
                        try:
                            # Usar el mismo XPath simple para listar opciones
                            opciones_disponibles = self.page.query_selector_all("//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]//div[@class='ant-select-item-option-content']")
                            self.logger.info('EjecutarCaso', f"Opciones disponibles en dropdown visible: {len(opciones_disponibles)}")
                            for i, opcion in enumerate(opciones_disponibles[:10]):
                                self.logger.info('EjecutarCaso', f"Opción {i+1}: {opcion.text_content()}")
                        except Exception as e:
                            self.logger.info('EjecutarCaso', f"Error al listar opciones: {e}")
                        
                        if ultima_excepcion:
                            raise ultima_excepcion
                        raise Exception(f"No se encontró IPS Remitente después de {len(candidatos)} intentos")
                
                except Exception as e:
                    print(f"Error detallado en IPS REMITENTE: {str(e)}")
                    self.logger.error('EjecutarCaso', f"Error al manejar IPS Remitente: {str(e)}", e)
                    try:
                        self.page.evaluate("document.body.click();")
                        time.sleep(1)
                    except:
                        pass
                    raise
                
                # Causa (XPATH SELENIUM EXACTO)
                try:
                    input_causa = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* Causa que Motiva la Atención:')]/parent::div/div/div", timeout=5000)
                    input_causa.click()
                    self.logger.info('EjecutarCaso', "Clicked on Causa input")
                    
                    search_text = "Enfermedad"
                    if self.helper.ingresar_texto_secuencial(input_causa, search_text):
                        self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                        time.sleep(0.5)
                        
                        # XPATH SELENIUM EXACTO
                        option_xpath = "//div[@class='ant-select-item-option-content'][contains(.,'38 - Enfermedad general')]"
                        option = self.page.wait_for_selector(option_xpath, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionada Causa correctamente")
                    else:
                        raise Exception("No se pudo ingresar el texto en el campo Causa")
                
                except Exception as e:
                    print(f"Error detallado en Causa: {str(e)}")
                    self.logger.error('EjecutarCaso', f"Error al manejar Causa: {str(e)}", e)
                    raise
                
                # Scroll y prioridad (XPATH SELENIUM EXACTO)
                self.page.evaluate("window.scrollBy(0, 300)")
                element = self.page.query_selector("//label[@class='form-label'][contains(.,'* Prioridad de la atención')]/parent::div/div")
                if element:
                    # Playwright usa funciones de flecha, no arguments
                    element.evaluate("el => el.style.visibility = 'visible'")
                input_prioridad = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* Prioridad de la atención')]/parent::div/div", timeout=5000)
                input_prioridad.click()
                self.logger.info('EjecutarCaso', "Clicked prioridad")
                
                # XPATH SELENIUM EXACTO
                clic_prioridad = self.page.wait_for_selector("//div[@class='ant-select-item-option-content'][contains(.,'No prioritaria')]", timeout=5000)
                clic_prioridad.click()
                self.logger.info('EjecutarCaso', "Clicked prioritaria combo")
                time.sleep(0.3)
                
                # ====== VERIFICACIÓN DE SESIÓN ANTES DE DIAGNÓSTICO ======
                self.verificar_sesion_activa(data, "ANTES DE INGRESAR DIAGNÓSTICO")
                
                # Diagnóstico (XPATH SELENIUM EXACTO)
                try:
                    input_dx = self.page.wait_for_selector("//input[contains(@aria-owns,'diagnostico_list')]", timeout=5000)
                    input_dx.click()
                    self.logger.info('EjecutarCaso', "Clicked on Diagnóstico input")
                    
                    if self.helper.ingresar_texto_secuencial(input_dx, data.diagnostico):
                        self.logger.info('EjecutarCaso', f"Texto ingresado correctamente: {data.diagnostico}")
                        time.sleep(0.5)
                        
                        # XPATH SELENIUM EXACTO
                        dynamic_xpath_dx = f"//div[@class='ant-select-item-option-content'][contains(.,'{data.diagnostico}')]"
                        option = self.page.wait_for_selector(dynamic_xpath_dx, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionado Diagnóstico correctamente")
                        time.sleep(0.3)
                    else:
                        raise Exception("No se pudo ingresar el texto en el campo Diagnóstico")
                
                except Exception as e:
                    print(f"Error detallado en Diagnóstico: {str(e)}")
                    self.logger.error('EjecutarCaso', f"Error al manejar Diagnóstico: {str(e)}", e)
                    raise
                
                # Modalidad (XPATH SELENIUM EXACTO)
                try:
                    input_modalidad = self.page.query_selector("//label[@class='form-label'][contains(.,'* Modalidad de realización de la tecnologia de salud')]/parent::div/div/div")
                    if input_modalidad:
                        input_modalidad.scroll_into_view_if_needed()
                    time.sleep(0.3)
                    
                    input_modalidad = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* Modalidad de realización de la tecnologia de salud')]/parent::div/div/div", timeout=5000)
                    input_modalidad.click()
                    self.logger.info('EjecutarCaso', "Clicked on Modalidad input")
                    
                    search_text = "Intramural"
                    if self.helper.ingresar_texto_secuencial(input_modalidad, search_text):
                        self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                        time.sleep(0.5)
                        
                        # XPATH SELENIUM EXACTO
                        option_xpath = "//div[@class='ant-select-item-option-content'][contains(.,'Intramural')]"
                        option = self.page.wait_for_selector(option_xpath, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionada Modalidad Intramural")
                        time.sleep(0.3)
                    else:
                        raise Exception("No se pudo ingresar el texto en el campo Modalidad")
                
                except Exception as e:
                    print(f"Error detallado en Modalidad: {str(e)}")
                    self.logger.error('EjecutarCaso', f"Error al manejar Modalidad: {str(e)}", e)
                    raise
                
                # ====== INGRESO DE SERVICIOS (método sobrescribible) ======
                self._verificar_pausa()  # Verificar pausa antes de ingresar servicios
                self._ingresar_servicios(data)
                
                time.sleep(1)
                self.page.evaluate("window.scrollBy(0, 100)")
                time.sleep(1)
                
                # Condición y Destino (XPATH SELENIUM EXACTO)
                try:
                    input_condicion = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* Condición y destino de la persona')]/parent::div/div/div", timeout=5000)
                    time.sleep(1)
                    input_condicion.click()
                    self.logger.info('EjecutarCaso', "Clicked on Condición y Destino input")
                    
                    search_text = "Paciente"
                    if self.helper.ingresar_texto_secuencial(input_condicion, search_text):
                        self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                        time.sleep(0.5)
                        
                        # XPATH SELENIUM EXACTO
                        option_xpath = "//div[@class='ant-select-item-option-content'][contains(.,'Paciente con destino a su domicilio')]"
                        option = self.page.wait_for_selector(option_xpath, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionada Condición: Paciente con destino a su domicilio")
                        time.sleep(0.3)
                    else:
                        raise Exception("No se pudo ingresar el texto en el campo Condición y Destino")
                
                except Exception as e:
                    print(f"Error detallado en Condición y Destino: {str(e)}")
                    self.logger.error('EjecutarCaso', f"Error al manejar Condición y Destino: {str(e)}", e)
                    raise
                
                # Finalidad (XPATH SELENIUM EXACTO)
                input_cFinalidad = self.page.wait_for_selector("#finality", timeout=5000)
                input_cFinalidad.fill("")
                print(input_cFinalidad)
                input_cFinalidad.click()
                self.logger.info('EjecutarCaso', f"clic condicion")
                
                # XPATH SELENIUM EXACTO
                clic_Finalidad = self.page.wait_for_selector("//div[@class='ant-select-item-option-content'][contains(.,'15 - Diagnostico')]", timeout=5000)
                self.page.evaluate("window.scrollBy(0, 100)")
                time.sleep(0.3)
                clic_Finalidad.click()
                self.logger.info('EjecutarCaso', f"Clicked on combo finalidad")
                
                # ====== VERIFICACIÓN DE SESIÓN ANTES DE IPS ======
                self.verificar_sesion_activa(data, "ANTES DE SELECCIÓN DE IPS")
                
                # Buscar y clickear IPS de atención y sede (desde JSON)
                nombre_ips_atencion = getattr(data, 'nombreIps', '') or ''
                sede_atencion = getattr(data, 'sede', '') or ''
                resultado = self.buscar_y_clickear_ips(nombre_ips_atencion)
                if resultado:
                    self.buscar_y_clickear_ips_sede(sede_atencion)
                else:
                    nombre_archivo = "archivo.txt"
                    with open(nombre_archivo, 'a') as archivo:
                        archivo.write(f"combo ips atiende  ,no se encontro,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
                    self.actualizar(data, "11", "")
                    self.reinicio()
                    return False  # ERROR: IPS no encontrada
                
                # ====== OBTENCIÓN DE ARCHIVO PDF (método sobrescribible) ======
                self._verificar_pausa()  # Verificar pausa antes de generar/obtener PDF
                file_path = self._obtener_archivo_pdf(data)
                if not file_path:
                    return False  # El método ya manejó el error y reinicio
                
                # Verificar sesión antes de subir archivos
                self.verificar_sesion_activa(data, "ANTES DE SUBIR ARCHIVOS")
                
                try:
                    # === SUBIR ARCHIVO A ORDEN MÉDICA ===
                    # Usar expect_file_chooser para simular flujo real (como Selenium send_keys)
                    boton_orden = self.page.locator("#fileListOrdenMedica").locator("xpath=..").locator("button")
                    with self.page.expect_file_chooser() as fc_info:
                        boton_orden.click(timeout=5000)
                    file_chooser = fc_info.value
                    file_chooser.set_files(file_path)
                    time.sleep(1)
                    self.logger.info('EjecutarCaso', f"✅ Archivo cargado en Orden Médica")
                    
                    # === SUBIR ARCHIVO A HISTORIA CLÍNICA ===
                    boton_hc = self.page.locator("#fileListHistoriaClinica").locator("xpath=..").locator("button")
                    with self.page.expect_file_chooser() as fc_info2:
                        boton_hc.click(timeout=5000)
                    file_chooser2 = fc_info2.value
                    file_chooser2.set_files(file_path)
                    time.sleep(1)
                    self.logger.info('EjecutarCaso', f"✅ Archivo cargado en Historia Clínica")
                    
                    time.sleep(1)
                except Exception as e:
                    error_msg = f"Error al cargar archivo en campos de entrada: {e}"
                    self.logger.error('EjecutarCaso', f"❌ {error_msg}", e)
                    self.crear_archivo_error(data, "ERROR_CARGA_ARCHIVO", error_msg, file_path)
                    raise
                
                self.page.evaluate("window.scrollBy(0, 100)")
                time.sleep(0.5)
                
                # XPATH SELENIUM EXACTO - Usar justificación del JSON
                txt_area = self.page.wait_for_selector("#descripcion", timeout=5000)
                txt_area.fill("")
                print("area")
                justificacion_texto = getattr(data, 'justificacion', '') or 'Orden de autorización'
                # Limpiar comillas extra si las hay
                justificacion_texto = justificacion_texto.strip('"').strip()
                self.helper.ingresar_texto(txt_area, justificacion_texto)
                self.logger.info('EjecutarCaso', f"ingreso input justificación: {justificacion_texto[:50]}...")
                time.sleep(1)
                
                self.page.evaluate("window.scrollBy(0, 400)")
                time.sleep(1)
                
                # ====== VERIFICACIÓN DE SESIÓN ANTES DE GUARDAR ======
                self.verificar_sesion_activa(data, "ANTES DE GUARDAR")
                
                # ====== CERRAR DROPDOWNS ABIERTOS Y PREPARAR BOTÓN GUARDAR ======
                # Cerrar cualquier dropdown de Ant Design que haya quedado abierto
                try:
                    dropdowns_abiertos = self.page.query_selector_all("div.ant-select-dropdown:not(.ant-select-dropdown-hidden)")
                    if dropdowns_abiertos:
                        self.logger.info('EjecutarCaso', f"⚠️ {len(dropdowns_abiertos)} dropdown(s) abierto(s) detectado(s), cerrando...")
                        self.page.evaluate("document.body.click();")
                        time.sleep(1)
                except Exception as e:
                    self.logger.warning('EjecutarCaso', f"⚠️ Error al verificar dropdowns: {e}")
                
                # Buscar el botón Guardar con múltiples estrategias
                self._verificar_pausa()  # Verificar pausa antes de guardar
                time.sleep(1)
                bonton_guardar = None
                
                # Estrategia 1: CSS selector (más rápido que XPath)
                try:
                    bonton_guardar = self.page.wait_for_selector("button[type='submit'].ant-btn-primary", timeout=5000)
                    self.logger.info('EjecutarCaso', "✅ Botón Guardar encontrado por CSS selector")
                except Exception:
                    pass
                
                # Estrategia 2: XPath como fallback
                if not bonton_guardar:
                    try:
                        bonton_guardar = self.page.wait_for_selector("//button[@type='submit'][contains(.,'Guardar')]", timeout=5000)
                        self.logger.info('EjecutarCaso', "✅ Botón Guardar encontrado por XPath")
                    except Exception:
                        pass
                
                # Estrategia 3: query_selector directo (sin esperas)
                if not bonton_guardar:
                    try:
                        bonton_guardar = self.page.query_selector("button[type='submit'].ant-btn-primary")
                        if not bonton_guardar:
                            bonton_guardar = self.page.query_selector("button.ant-btn-primary.btn-primary")
                        if bonton_guardar:
                            self.logger.info('EjecutarCaso', "✅ Botón Guardar encontrado por query_selector")
                    except Exception:
                        pass
                
                if not bonton_guardar:
                    raise Exception("No se encontró el botón Guardar con ninguna estrategia")
                
                print("bonton_guardar")
                
                # Limpiar residuo de animación del clic anterior (2do paciente en adelante)
                try:
                    self.page.evaluate("""(btn) => {
                        btn.removeAttribute('ant-click-animating-without-extra-node');
                        btn.classList.remove('ant-click-animating');
                    }""", bonton_guardar)
                except Exception:
                    pass
                
                # Scroll al botón y clic con force=True (como Selenium, sin actionability checks)
                try:
                    bonton_guardar.scroll_into_view_if_needed()
                except Exception:
                    self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                bonton_guardar.click(force=True)
                
                self.logger.info('EjecutarCaso', f"clic boton guardar")
                time.sleep(3)
                
                try:
                    # ====== DETECCIÓN ROBUSTA DEL MODAL DE RESPUESTA ======
                    # Esperar directamente por el h2 FINAL (Error o Correcto)
                    # NO esperar por swal2-title genérico (puede ser modal de "cargando")
                    tipo_resultado = None
                    h2_element = None
                    max_espera_total = 60  # 60 segundos máximo esperando respuesta del servidor
                    intervalo_polling = 2  # cada 2 segundos
                    intentos_totales = max_espera_total // intervalo_polling
                    
                    self.logger.info('EjecutarCaso', f"⏳ Esperando respuesta del servidor (máx {max_espera_total}s)...")
                    
                    for intento in range(intentos_totales):
                        # Buscar Error
                        error_title = self.page.query_selector("//h2[contains(.,'Error')]")
                        if error_title and error_title.is_visible():
                            tipo_resultado = 'error'
                            h2_element = error_title
                            self.logger.info('EjecutarCaso', f"🔍 Modal tipo 'Error' detectado ({intento * intervalo_polling}s)")
                            break
                        
                        # Buscar Correcto
                        success_title = self.page.query_selector("//h2[contains(.,'Correcto')]")
                        if success_title and success_title.is_visible():
                            tipo_resultado = 'correcto'
                            h2_element = success_title
                            self.logger.info('EjecutarCaso', f"🔍 Modal tipo 'Correcto' detectado ({intento * intervalo_polling}s)")
                            break
                        
                        if intento < intentos_totales - 1:
                            if intento % 5 == 0 and intento > 0:
                                self.logger.info('EjecutarCaso', f"⏳ Aún esperando respuesta... ({intento * intervalo_polling}s)")
                            time.sleep(intervalo_polling)
                    
                    # ====== CAPTURAR TEXTOS ANTES DE CERRAR ======
                    success_text = None
                    error_text = None
                    
                    if tipo_resultado == 'correcto':
                        success_text = h2_element.text_content()
                        self.logger.info('EjecutarCaso', f"📝 Texto éxito capturado: {success_text}")
                    elif tipo_resultado == 'error':
                        error_text = "Error sin detalle"
                        try:
                            error_el = self.page.query_selector("//div[contains(@class,'swal2-html-container') or @id='swal2-html-container']")
                            if error_el:
                                error_text = (error_el.text_content() or "").strip() or error_text
                                self.logger.info('EjecutarCaso', f"📝 Texto error capturado: {error_text[:100]}...")
                            else:
                                self.logger.warning('EjecutarCaso', f"⚠️ Elemento swal2-html-container no encontrado")
                        except Exception as e:
                            self.logger.warning('EjecutarCaso', f"⚠️ No se pudo leer swal2-html-container: {e}")
                    
                    # Cerrar el modal SweetAlert2 DESPUÉS de capturar los textos
                    self._cerrar_swal2()
                    
                    # ====== PROCESAR SEGÚN TIPO DE RESULTADO ======
                    if tipo_resultado == 'correcto':
                        # ====== ÉXITO ======
                        print(f"ÉXITO: {success_text}")
                        
                        numbers = re.findall(r'\d+', success_text)
                        numbers_str = ''.join(numbers)
                        
                        with open("archivo.txt", 'a', encoding='utf-8') as archivo:
                            archivo.write(f"caso,{success_text},paciente,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
                        
                        self._hacer_clic_ok()
                        self.actualizar(data, "1", numbers_str)  # Estado 1 = Exitoso
                        self.reinicio()
                        time.sleep(2)
                        self.alerta()
                        return True  # ÉXITO: Caso completado correctamente
                    
                    elif tipo_resultado == 'error':
                        # ====== ERROR - Procesar detalle ya capturado ======
                        
                        # Verificar si es solicitud activa (método sobrescribible por clases hijas)
                        if "solicitud activa" in error_text.lower() and "número de radicado" in error_text.lower():
                            return self._manejar_solicitud_activa(data, error_text)
                        
                        # Error normal - extraer fragmento
                        fragment = None
                        m = re.search(r"(servicio\s*\d+\s*con el número de radicado\s*#\s*\d+)", error_text, re.IGNORECASE)
                        if m:
                            fragment = m.group(1).strip()
                        else:
                            m1 = re.search(r"servicio\s*(\d+)", error_text, re.IGNORECASE)
                            m2 = re.search(r"#\s*(\d+)", error_text)
                            if m1 and m2:
                                fragment = f"servicio {m1.group(1)} con el número de radicado #{m2.group(1)}"
                            else:
                                fragment = (error_text or "Error sin detalle").strip()[:250]
                        
                        print(f"ERROR (capturado): {fragment}")
                        try:
                            with open("archivo.txt", 'a', encoding='utf-8') as archivo:
                                archivo.write(f"caso,{fragment},paciente,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
                        except Exception as e:
                            self.logger.warning('EjecutarCaso', f"⚠️ No se pudo escribir archivo.txt: {e}")
                        
                        try:
                            self.actualizar(data, "3", "")
                        except Exception as e:
                            self.logger.warning('EjecutarCaso', f"⚠️ Falló actualizar con mensaje de error: {e}")
                        
                        try:
                            self._hacer_clic_ok()
                        except Exception as e:
                            self.logger.warning('EjecutarCaso', f"⚠️ Falló al hacer clic en OK del modal: {e}")
                        
                        self.reinicio()
                        return False  # ERROR: Servicio duplicado/ya reportado
                    
                    else:
                        # No se encontró ni Error ni Correcto después de todos los intentos
                        self.logger.warning('EjecutarCaso', f"⚠️ Modal visible pero sin título Error/Correcto después de {max_espera_total}s")
                        self._hacer_clic_ok()
                        self.actualizar(data, "19", "")
                        self.reinicio()
                        return False  # ERROR: No se pudo determinar resultado
                except Exception as e:
                    print(f"Error en manejo de respuesta: {e}")
                    self.actualizar(data, "11", "")
                    self.reinicio()
                    return False  # ERROR: Fallo en manejo de respuesta del servidor
                
        except Exception as e:
            error_message = str(e).lower()
            
            # Clasificar errores
            if any(keyword in error_message for keyword in ["invalid session", "session not created", "no such session", "chrome not reachable"]):
                self.logger.error('EjecutarCaso', f"❌ SESIÓN DEL NAVEGADOR PERDIDA", e)
                print(f"[SESIÓN PERDIDA] Paciente {data.identificacion} - Navegador desconectado")
                self.actualizar(data, "12", "")
            elif "timeout" in error_message:
                self.logger.error('EjecutarCaso', f"⏰ TIMEOUT - ELEMENTO NO RESPONDIÓ A TIEMPO", e)
                print(f"[TIMEOUT] Paciente {data.identificacion} - Página no respondió a tiempo")
                self.actualizar(data, "13", "")
            elif any(keyword in error_message for keyword in ["element not found", "no such element", "element not interactable"]):
                self.logger.error('EjecutarCaso', f"🎯 ELEMENTO NO ENCONTRADO EN LA PÁGINA", e)
                print(f"[ELEMENTO FALTANTE] Paciente {data.identificacion} - Campo o botón no encontrado")
                self.actualizar(data, "14", "")
            elif any(keyword in error_message for keyword in ["stale element", "element is not attached"]):
                self.logger.error('EjecutarCaso', f"🔄 ELEMENTO OBSOLETO - PÁGINA SE ACTUALIZÓ", e)
                print(f"[ELEMENTO OBSOLETO] Paciente {data.identificacion} - Página se actualizó")
                self.actualizar(data, "15", "")
            elif any(keyword in error_message for keyword in ["network", "connection", "dns", "resolve"]):
                self.logger.error('EjecutarCaso', f"🌐 ERROR DE CONEXIÓN A INTERNET", e)
                print(f"[SIN INTERNET] Paciente {data.identificacion} - Problemas de conexión")
                self.actualizar(data, "16", "")
            elif any(keyword in error_message for keyword in ["no se pudo encontrar", "pdf no encontrado", "pdf no existe", "pdf faltante"]):
                self.logger.error('EjecutarCaso', f"📄 ARCHIVO PDF NO ENCONTRADO", e)
                print(f"[PDF FALTANTE] Paciente {data.identificacion} - Documento no encontrado")
                self.actualizar(data, "5", "")
            elif any(keyword in error_message for keyword in ["permission", "access denied", "forbidden"]):
                self.logger.error('EjecutarCaso', f"🔒 ERROR DE PERMISOS O ACCESO DENEGADO", e)
                print(f"[SIN PERMISOS] Paciente {data.identificacion} - Acceso denegado")
                self.actualizar(data, "18", "")
            else:
                error_corto = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
                self.logger.error('EjecutarCaso', f"❓ ERROR NO CLASIFICADO: {error_corto}", e)
                print(f"[ERROR DESCONOCIDO] Paciente {data.identificacion} - {error_corto}")
                self.actualizar(data, "11", "")
            
            self.logger.info('EjecutarCaso', f"⏰ Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.reinicio()
            return False
        
        # Si llegamos aquí es porque no hubo excepciones pero tampoco retornó explícitamente
        # Esto NO debería pasar en flujo normal (todos los caminos deben retornar explícitamente)
        self.logger.warning('EjecutarCaso', "⚠️ Flujo inesperado - llegó al final sin retorno explícito")
        return False
    
    # ============ MÉTODOS AUXILIARES - XPATHS SELENIUM EXACTOS ============
    
    def comboIdentidad(self) -> bool:
        """Método para manejar el combo de identidad - XPATH SELENIUM EXACTO"""
        try:
            try:
                self.page.title()
            except Exception as session_error:
                if "invalid session id" in str(session_error).lower():
                    self.logger.error('EjecutarCaso', "Error: Sesión de navegador inválida o cerrada", session_error)
                    raise Exception("Sesión de navegador perdida")
                else:
                    raise session_error
            
            time.sleep(1)
            # XPATH SELENIUM EXACTO
            combo_selector = "//span[@class='ant-select-selection-item'][contains(.,'Adulto sin Identificación')]"
            
            try:
                combo_element = self.page.wait_for_selector(combo_selector, timeout=5000)
                combo_element.click()
                self.logger.info('EjecutarCaso', "Combo de identidad abierto correctamente")
            except:
                combo_selector_alt = "//div[contains(@class,'ant-select-selector')]"
                combo_element = self.page.wait_for_selector(combo_selector_alt, timeout=5000)
                combo_element.click()
                self.logger.info('EjecutarCaso', "Combo abierto con selector alternativo")
            
            self.page.wait_for_selector(".ant-select-dropdown", timeout=5000)
            time.sleep(1)
            
            return True
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error en comboIdentidad: {e}", e)
            return False
    
    def esperar_y_clickear(self, xpath: str):
        """Espera y hace clic en un elemento"""
        try:
            element = self.page.wait_for_selector(xpath, timeout=5000)
            element.click()
            return element
        except:
            return None
    
    def scroll_list_to(self, position: int):
        """Hace scroll en la lista virtual"""
        try:
            self.page.evaluate(f"""
                const container = document.querySelector('.rc-virtual-list-scrollbar-vertical');
                const thumb = document.querySelector('.rc-virtual-list-scrollbar-thumb');
                if (container && thumb) {{
                    container.style.visibility = 'visible';
                    thumb.style.top = '{position}px';
                    container.dispatchEvent(new Event('scroll'));
                }}
            """)
            time.sleep(0.5)
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error al hacer scroll: {e}", e)
    
    def scroll_list_and_find_option(self, option_text: str, max_attempts: int = 30):
        """Busca opción en virtual list haciendo scroll - IGUAL QUE SELENIUM"""
        attempts = 0
        found_options = set()
        scroll_position = 0
        scroll_increment = 100
        
        self.logger.info('EjecutarCaso', f"Buscando opción: '{option_text}'")
        
        while attempts < max_attempts:
            try:
                time.sleep(0.3)
                
                options = self.page.query_selector_all("//div[contains(@class, 'ant-select-item-option-content')]")
                
                for option in options:
                    try:
                        option_content = option.text_content().strip()
                        if option_content:
                            found_options.add(option_content)
                            
                            if option_content == option_text:
                                self.logger.info('EjecutarCaso', f"Opción encontrada: {option_content}")
                                option.scroll_into_view_if_needed()
                                time.sleep(0.3)
                                return option
                    except:
                        continue
                
                scroll_position += scroll_increment
                self.page.evaluate(f"""
                    const container = document.querySelector('.rc-virtual-list-holder');
                    if (container) container.scrollTop = {scroll_position};
                """)
                
                current_scroll = self.page.evaluate("""
                    (() => {
                        const container = document.querySelector('.rc-virtual-list-holder');
                        return container ? container.scrollTop : 0;
                    })()
                """)
                
                max_scroll = self.page.evaluate("""
                    (() => {
                        const container = document.querySelector('.rc-virtual-list-holder');
                        return container ? container.scrollHeight - container.clientHeight : 0;
                    })()
                """)
                
                if current_scroll >= max_scroll and attempts > 5:
                    self.logger.info('EjecutarCaso', "Llegamos al final de la lista")
                    break
            except Exception as e:
                self.logger.error('EjecutarCaso', f"Error en intento {attempts + 1}: {e}", e)
            
            attempts += 1
        
        self.logger.warning('EjecutarCaso', f"Opción '{option_text}' no encontrada después de {attempts} intentos")
        self.logger.info('EjecutarCaso', f"Opciones encontradas durante la búsqueda: {list(found_options)}")
        return None
    
    def click_option(self, option):
        """Hacer clic en una opción del dropdown"""
        try:
            option.scroll_into_view_if_needed()
            time.sleep(0.5)
            try:
                option.click()
            except:
                # Playwright usa funciones de flecha en vez de arguments
                option.evaluate("el => el.click()")
            time.sleep(0.5)
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error al hacer clic en la opción: {e}", e)
            raise
    
    def obtener_texto_componente(self, xpath: str):
        """Obtiene el texto de un componente si existe"""
        try:
            elemento = self.page.query_selector(xpath)
            if elemento and elemento.is_visible():
                return elemento.text_content().strip()
            return None
        except:
            return None
    
    def verificar_sesion_activa(self, data=None, contexto: str = "") -> bool:
        """Verifica si la sesión de Playwright sigue activa"""
        try:
            self.page.title()
            self.page.url
            self.page.evaluate("document.readyState;")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            session_errors = ['invalid session id', 'no such session', 'session not created',
                              'chrome not reachable', 'target window already closed', 'disconnected',
                              'session deleted because of page crash', 'chrome failed to start',
                              'session timed out', 'browser has been closed', 'context has been closed']
            
            if any(error_keyword in error_msg for error_keyword in session_errors):
                if contexto:
                    error_message = f"SESIÓN PERDIDA {contexto}: {e}"
                else:
                    error_message = f"SESIÓN DEL NAVEGADOR PERDIDA: {e}"
                
                self.logger.error('EjecutarCaso', f"❌ {error_message}", e)
                
                if data:
                    try:
                        self.actualizar(data, "12", "")
                    except:
                        pass
                
                raise SessionLostException(f"Sesión perdida {contexto.lower()}" if contexto else "Sesión del navegador perdida")
            else:
                self.logger.warning('EjecutarCaso', f"⚠️ Error al verificar sesión (pero continuando): {e}")
                return True
    
    def actualizar(self, data, estado: str, numero_autorizacion: str = ""):
        """
        Actualizar el estadoCaso en la base de datos usando la API.
        
        Mapeo de estados:
        - "1" = ✅ Completado/OK (envía numeroAutorizacion)
        - "3" = ⏳ En proceso (servicio duplicado/ya reportado)
        - "4" = ❌ Datos del paciente inválidos (documento inválido)
        - "5" = 📄 Archivo PDF no encontrado
        - "11" = ❓ Error no clasificado / No se encontró paciente
        - "12" = 🔌 Sesión del navegador perdida
        - "13" = ⏰ Timeout (elemento no respondió)
        - "14" = 🎯 Elemento no encontrado en la página
        - "15" = 🔄 Elemento obsoleto (página se actualizó)
        - "16" = 🌐 Error de conexión a internet
        - "17" = ❓ Otro error no especificado
        - "18" = 🔒 Permisos o acceso denegado
        - "19" = ❔ No se pudo determinar resultado del modal
        - "20" = 📞 Teléfono inválido o faltante (no cumple formato)
        """
        try:
            import requests
            
            self.logger.info('EjecutarCaso', f"🔄 Actualizando con modo: {self.modo_actual}")
            
            # Obtener el idItemOrden
            id_item = data.idItemOrden
            
            # Usar el endpoint correcto para actualizar estadoCaso
            url = f"{config.api_url_programacion_base.rstrip('/')}/h-itemordenesproced/{id_item}/estadoCaso"
            
            # Mapear el estado string a integer para estadoCaso
            estado_int = int(estado) if estado.isdigit() else 0
            
            # Construir payload - solo enviar numeroAutorizacion si estado es 1 (éxito)
            if estado == "1" and numero_autorizacion and numero_autorizacion.strip():
                payload = {
                    "estadoCaso": estado_int,
                    "numeroAutorizacion": numero_autorizacion.strip()
                }
                self.logger.info('EjecutarCaso', f"📝 Número de autorización: {numero_autorizacion}")
            else:
                payload = {
                    "estadoCaso": estado_int,
                    "numeroAutorizacion": ""
                }
            
            self.logger.info('EjecutarCaso', f"📊 Estado del caso: {estado}")
            self.logger.info('EjecutarCaso', f"📤 Enviando payload: {payload}")
            
            # Enviar request al API
            try:
                response = requests.put(url, json=payload, timeout=10)
                if response.status_code == 200:
                    self.logger.info('EjecutarCaso', f"✅ Estado actualizado correctamente para orden {id_item}")
                else:
                    self.logger.warning('EjecutarCaso', f"⚠️ API respondió con código: {response.status_code}")
            except Exception as req_error:
                self.logger.warning('EjecutarCaso', f"⚠️ Error enviando al API (worker lo manejará): {req_error}")
            
            self.logger.info('EjecutarCaso', f"⏰ Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error al actualizar estado: {e}", e)
            print(f"Error al actualizar estado: {e}")
    
    def actualizar_con_resultado_ejecucion(self, data, estado: str, numero_autorizacion: str = "", resultado_ejecucion: str = ""):
        """
        Actualizar tanto estadoCaso como resultado_ejecucion en la tabla programacion
        """
        try:
            # 1. Actualizar estadoCaso como siempre
            self.actualizar(data, estado, numero_autorizacion)
            
            # 2. NUEVO: Actualizar resultado_ejecucion en tabla programacion
            if resultado_ejecucion:
                url_programacion = f"{config.api_url_programacion_base.rstrip('/')}/programacion-ordenes/{data.idItemOrden}"
                payload_programacion = {
                    "resultado_ejecucion": resultado_ejecucion
                }
                
                try:
                    response = requests.put(url_programacion, json=payload_programacion, timeout=10)
                    if response.status_code == 200:
                        self.logger.info('EjecutarCaso', f"✅ resultado_ejecucion actualizado: {resultado_ejecucion[:50]}...")
                    else:
                        self.logger.warning('EjecutarCaso', f"⚠️ Error actualizando resultado_ejecucion: {response.status_code}")
                except Exception as e:
                    self.logger.warning('EjecutarCaso', f"⚠️ Error enviando resultado_ejecucion: {e}")
        
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error al actualizar con resultado_ejecucion: {e}", e)
    
    def _obtener_archivo_pdf(self, data) -> str:
        """
        Método para obtener el archivo PDF - puede ser sobrescrito en clases hijas.
        Por defecto genera el Anexo 3.
        
        Args:
            data: Datos del paciente con atributos idAtencion, idOrden, idProcedimiento
            
        Returns:
            Ruta del archivo PDF o cadena vacía si hay error
        """
        self.logger.info('EjecutarCaso', f"📄 === GENERANDO ANEXO 3 ===")
        
        try:
            # Generar PDF del Anexo 3 usando los datos de la orden
            file_path = self.pdf_service.generar_anexo3(
                id_atencion=data.idAtencion,
                id_orden=data.idOrden,
                id_procedimiento=data.idProcedimiento
            )
            
            self.logger.info('EjecutarCaso', f"✅ PDF generado: {file_path}")
            
            # Verificar que se generó correctamente
            if not os.path.exists(file_path):
                raise Exception("PDF del Anexo 3 no se generó correctamente")
            
            tamaño_archivo = os.path.getsize(file_path)
            self.logger.info('EjecutarCaso', f"📊 Tamaño del archivo: {tamaño_archivo} bytes")
            
            if tamaño_archivo == 0:
                raise Exception("PDF generado está vacío (0 bytes)")
            elif tamaño_archivo < 1024:
                self.logger.warning('EjecutarCaso', f"⚠️ ADVERTENCIA: El archivo es muy pequeño ({tamaño_archivo} bytes)")
            
            return file_path
            
        except Exception as e:
            error_msg = f"Error al generar PDF del Anexo 3: {e}"
            self.logger.error('EjecutarCaso', f"❌ {error_msg}", e)
            self.crear_archivo_error(data, "ERROR_GENERAR_PDF", error_msg, "")
            self.actualizar(data, "17", "")
            self.reinicio()
            return ""
    
    def _ingresar_servicios(self, data):
        """
        Método para ingresar servicios/CUPS - puede ser sobrescrito en clases hijas.
        Por defecto usa el método de un solo CUPS.
        
        Args:
            data: Datos del paciente con atributo 'cups'
        """
        # Servicios (XPATH SELENIUM EXACTO)
        clic_Boton_servicios = self.page.wait_for_selector("//button[@aria-required='true'][contains(.,'Seleccionar Servicio')]", timeout=5000)
        clic_Boton_servicios.click()
        self.logger.info('EjecutarCaso', "Clicked Servicios combo")
        
        # Verificación de sesión antes de ingreso de items
        self.verificar_sesion_activa(data, "ANTES DE INGRESO DE ITEMS")
        
        # Ingresar Items (un solo CUPS)
        self.ingreso_items.IntemsAndFor(data)
    
    def _manejar_solicitud_activa(self, data, error_text: str) -> bool:
        """
        Maneja el caso de 'solicitud activa' detectado en el modal de error.
        Este método puede ser sobrescrito por clases hijas (ej: Laboratorio) para comportamiento diferente.
        
        COMPORTAMIENTO POR DEFECTO (ANEXO 3):
        - Extrae solo el número de radicado
        - Actualiza con estado 1 (éxito)
        - Retorna True (caso completado)
        
        Args:
            data: Datos del paciente
            error_text: Texto completo del error con "solicitud activa"
            
        Returns:
            True para indicar éxito, False para error
        """
        self.logger.info('EjecutarCaso', f"✅ SOLICITUD ACTIVA DETECTADA - Tratando como éxito (Anexo 3)")
        
        # Extraer SOLO el número de radicado (comportamiento Anexo 3)
        numero_radicado = ""
        radicado_match = re.search(r'número de radicado\s*#?\s*(\d+)', error_text, re.IGNORECASE)
        if radicado_match:
            numero_radicado = radicado_match.group(1)
            self.logger.info('EjecutarCaso', f"📝 Número de radicado extraído: {numero_radicado}")
        else:
            numbers = re.findall(r'\d+', error_text)
            numero_radicado = ''.join(numbers) if numbers else ""
            self.logger.warning('EjecutarCaso', f"⚠️ Usando fallback para número: {numero_radicado}")
        
        # Registrar en archivo
        with open("archivo.txt", 'a', encoding='utf-8') as archivo:
            archivo.write(f"caso,SOLICITUD ACTIVA - {error_text},paciente,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
        
        # Cerrar modal y actualizar
        self._hacer_clic_ok()
        self.actualizar_con_resultado_ejecucion(data, "1", numero_radicado, error_text)
        self.reinicio()
        time.sleep(2)
        self.alerta()
        return True  # ÉXITO: Solicitud activa tratada como completada
    
    def _cerrar_swal2(self):
        """Cerrar cualquier modal SweetAlert2 abierto usando JavaScript"""
        try:
            cerrado = self.page.evaluate("""
                (() => {
                    const container = document.querySelector('.swal2-container');
                    if (container) {
                        // Intentar clic en botón OK/Confirm primero
                        const btn = container.querySelector('.swal2-confirm');
                        if (btn) { btn.click(); return 'btn'; }
                        // Si no hay botón, cerrar con Swal.close()
                        if (typeof Swal !== 'undefined' && Swal.close) { Swal.close(); return 'swal'; }
                        // Último recurso: remover el container
                        container.remove();
                        return 'remove';
                    }
                    return 'none';
                })()
            """)
            if cerrado != 'none':
                self.logger.info('EjecutarCaso', f"🧹 SweetAlert2 cerrado via JS ({cerrado})")
                time.sleep(0.5)
        except Exception as e:
            self.logger.warning('EjecutarCaso', f"⚠️ Error cerrando SweetAlert2: {e}")
    
    def reinicio(self):
        """Método de reinicio - XPATH SELENIUM EXACTO"""
        try:
            self.logger.info('EjecutarCaso', "🔄 Iniciando proceso de reinicio...")
            
            if not self.verificar_sesion_activa():
                self.logger.error('EjecutarCaso', "❌ Sesión no activa, no se puede realizar reinicio", None)
                raise SessionLostException("Sesión perdida durante reinicio")
            
            # Cerrar cualquier SweetAlert2 que esté bloqueando la página
            self._cerrar_swal2()
            
            # === CERRAR MODALES DE ANT DESIGN QUE PUEDAN ESTAR ABIERTOS ===
            try:
                self.logger.info('EjecutarCaso', "🧹 Verificando modales de Ant Design abiertos...")
                modales_cerrados = self.page.evaluate("""
                    (() => {
                        let count = 0;
                        // Cerrar todos los modales visibles
                        document.querySelectorAll('.ant-modal-wrap:not([style*="display: none"])').forEach(modal => {
                            modal.remove();
                            count++;
                        });
                        // Cerrar backdrops
                        document.querySelectorAll('.ant-modal-mask').forEach(mask => {
                            mask.remove();
                        });
                        // Cerrar dropdowns abiertos
                        document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').forEach(dd => {
                            dd.remove();
                        });
                        return count;
                    })()
                """)
                if modales_cerrados > 0:
                    self.logger.info('EjecutarCaso', f"✅ {modales_cerrados} modal(es) de Ant Design cerrado(s)")
                time.sleep(0.5)
            except Exception as e:
                self.logger.warning('EjecutarCaso', f"⚠️ Error al cerrar modales Ant Design: {e}")
            
            time.sleep(1)
            self.page.evaluate("window.scrollTo(0, 0);")
            time.sleep(1)
            
            url_actual = self.page.url
            if "portalsalud.coosalud.com" not in url_actual:
                self.logger.error('EjecutarCaso', f"❌ No estamos en la página correcta: {url_actual}", None)
                raise Exception("Página incorrecta para reinicio")
            
            # XPATH SELENIUM EXACTO - con force=True para evitar overlay intercepts
            try:
                bonton_urg = self.page.wait_for_selector("//span[contains(.,'Reportar')]/parent::div/following-sibling::ul/li/span[contains(.,'Urgencias')]", timeout=10000)
                try:
                    bonton_urg.click(force=True)
                except Exception:
                    self.page.evaluate("""(el) => el.click()""", bonton_urg)
                self.logger.info('EjecutarCaso', "✅ Clic en botón Urgencias")
                time.sleep(1)
            except Exception as e:
                self.logger.error('EjecutarCaso', f"❌ Error haciendo clic en Urgencias: {e}", e)
                raise
            
            # XPATH SELENIUM EXACTO - con force=True para evitar overlay intercepts
            try:
                bonton_amb = self.page.wait_for_selector("//span[contains(.,'Reportar')]/parent::div/following-sibling::ul/li/span[contains(.,'Ambulatoria')]", timeout=10000)
                try:
                    bonton_amb.click(force=True)
                except Exception:
                    self.page.evaluate("""(el) => el.click()""", bonton_amb)
                self.logger.info('EjecutarCaso', "✅ Clic en botón Ambulatoria")
                self.logger.info('EjecutarCaso', "✅ Reinicio completado exitosamente")
            except Exception as e:
                self.logger.error('EjecutarCaso', f"❌ Error haciendo clic en Ambulatoria: {e}", e)
                raise
        except Exception as e:
            self.logger.error('EjecutarCaso', f"❌ Error durante reinicio: {e}", e)
            raise
    
    def alerta(self):
        """Manejar alertas"""
        componentes = ["//div/h2[contains(.,'Alerta')]"]
        texto = None
        for componente in componentes:
            texto = self.obtener_texto_componente(componente)
            if texto is not None:
                print(texto)
                break
        
        if texto is not None:
            self._hacer_clic_ok()
            self.logger.info('EjecutarCaso', f"clic boton bonton_ok alerta")
            self.reinicio()
    
    def buscar_y_clickear_ips(self, nombre_ips_atencion: str) -> bool:
        """Buscar y clickear IPS de atención usando nombreIps del JSON"""
        try:
            print("🔍 === INICIANDO BÚSQUEDA DE IPS DE ATENCIÓN ===")
            
            print("📍 Paso 1: Localizando campo IPS de atención...")
            try:
                # XPATH SELENIUM EXACTO
                input_IPS = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'IPS de atención')]/parent::div/div/div", timeout=5000)
                print("✅ Campo encontrado por label")
            except:
                print("⚠️ No encontrado por label, buscando por ID...")
                input_IPS = self.page.wait_for_selector("#ipsAttentionCode", timeout=5000)
                print("✅ Campo encontrado por ID")
            
            print("🖱️ Paso 2: Haciendo clic en el campo...")
            input_IPS.click()
            self.logger.info('EjecutarCaso', "Clicked on IPS de atención input")
            time.sleep(0.5)
            
            nombre_ips_atencion = (nombre_ips_atencion or "").strip()
            if not nombre_ips_atencion:
                nit_cfg = (config.nit_ips or "").strip()
                nombre_cfg = (config.nombre_ips or "").strip()
                nombre_ips_atencion = f"{nit_cfg} - {nombre_cfg}" if nit_cfg and nombre_cfg else (nombre_cfg or nit_cfg)
            
            nit_busqueda = nombre_ips_atencion.split('-')[0].strip() if '-' in nombre_ips_atencion else nombre_ips_atencion
            search_text = nit_busqueda or (config.nit_ips or "")
            print(f"⌨️ Paso 3: Ingresando texto: '{search_text}'")
            
            if self.helper.ingresar_texto_secuencial(input_IPS, search_text):
                self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                print("✅ Texto ingresado correctamente")
                
                print("⏳ Paso 4: Esperando dropdown...")
                time.sleep(1)
                
                # Esperar opciones
                max_intentos = 10
                opciones_con_texto = []
                
                for intento in range(max_intentos):
                    try:
                        time.sleep(0.3)
                        selector = ".ant-select-dropdown:not([style*='display: none']) .ant-select-item-option"
                        opciones = self.page.query_selector_all(selector)
                        
                        opciones_con_texto = []
                        for opt in opciones:
                            try:
                                if opt.is_visible():
                                    texto = opt.text_content().strip() if opt.text_content() else ""
                                    if texto:
                                        opciones_con_texto.append((opt, texto))
                            except:
                                continue
                        
                        if opciones_con_texto:
                            print(f"✅ {len(opciones_con_texto)} opciones visibles encontradas")
                            break
                    except Exception as e:
                        print(f"  Error en intento {intento+1}: {e}")
                
                if not opciones_con_texto:
                    print("❌ No se encontraron opciones")
                    raise Exception("Opciones del dropdown no se renderizaron")
                
                print("🎯 Paso 6: Buscando opción específica...")
                option_encontrada = None
                
                nombre_ips_cfg = (config.nombre_ips or "").strip()
                nombres_ips = []
                if nombre_ips_atencion:
                    if '-' in nombre_ips_atencion:
                        nombre_parte = nombre_ips_atencion.split('-', 1)[1].strip()
                        if nombre_parte:
                            nombres_ips.append(nombre_parte)
                    else:
                        nombres_ips.append(nombre_ips_atencion)
                if nombre_ips_cfg:
                    nombres_ips.extend([n.strip() for n in nombre_ips_cfg.split("|") if n.strip()])
                
                for elemento, texto in opciones_con_texto:
                    print(f"  📝 Evaluando: '{texto}'")
                    if search_text in texto and (not nombres_ips or any(nombre in texto for nombre in nombres_ips)):
                        print(f"  ✅ Opción encontrada: '{texto}'")
                        option_encontrada = elemento
                        break
                
                if option_encontrada:
                    print("🖱️ Paso 7: Haciendo clic en la opción...")
                    try:
                        option_encontrada.scroll_into_view_if_needed()
                        time.sleep(0.3)
                    except:
                        pass
                    
                    clic_exitoso = False
                    try:
                        option_encontrada.click()
                        print("  ✅ Clic exitoso")
                        clic_exitoso = True
                    except:
                        try:
                            # Playwright usa funciones de flecha en vez de arguments
                            option_encontrada.evaluate("el => el.click()")
                            print("  ✅ JavaScript clic exitoso")
                            clic_exitoso = True
                        except:
                            pass
                    
                    if clic_exitoso:
                        self.logger.info('EjecutarCaso', "Opción seleccionada correctamente")
                        time.sleep(1.5)
                        print("🎉 ¡IPS de atención seleccionada correctamente!")
                        return True
                    else:
                        print("❌ Todos los métodos de clic fallaron")
                        return False
                else:
                    print("❌ No se encontró la opción en el dropdown")
                    return False
            else:
                raise Exception("No se pudo ingresar el texto")
        except Exception as e:
            print(f"💥 ERROR GENERAL: {str(e)}")
            self.logger.error('EjecutarCaso', f"Error al manejar IPS de atención: {str(e)}", e)
            try:
                self.page.evaluate("document.body.click();")
                time.sleep(1)
            except:
                pass
            return False
    
    def buscar_y_clickear_ips_sede(self, sede_atencion: str) -> bool:
        """Buscar y hacer clic en la SEDE usando el valor del JSON"""
        try:
            # XPATH SELENIUM EXACTO
            input_ips_sede = self.page.wait_for_selector("//input[contains(@aria-owns,'sedeIpsAtencion_list')]", timeout=5000)
            input_ips_sede.fill("")
            input_ips_sede.click()
            self.logger.info('EjecutarCaso', "clic ips sede")

            sede_atencion = (sede_atencion or "").strip()
            sede_code = (config.sede_ips or "").strip()
            sede_nombre = (config.sede_ips_nombre or "").strip()

            if not sede_atencion and not sede_code and not sede_nombre:
                self.logger.warning('EjecutarCaso', "SEDE IPS no configurada")
                return False
            
            search_text = sede_atencion or sede_code or sede_nombre
            if self.helper.ingresar_texto_secuencial(input_ips_sede, search_text):
                self.logger.info('EjecutarCaso', "Texto ingresado correctamente en IPS Sede")
                time.sleep(2)
                
                candidates = []
                if sede_atencion:
                    candidates.append(sede_atencion)
                if sede_nombre and sede_code:
                    candidates.append(f"{sede_code}-{sede_nombre}")
                if sede_code:
                    candidates.append(sede_code)
                if sede_nombre:
                    candidates.append(sede_nombre)
                
                option = None
                for cand in candidates:
                    option_xpath = f"//div[@class='ant-select-item-option-content'][contains(.,'{cand}')]"
                    try:
                        option = self.page.wait_for_selector(option_xpath, timeout=5000)
                        if option:
                            break
                    except:
                        continue
                
                if option:
                    option.click()
                    self.logger.info('EjecutarCaso', "Sede seleccionada correctamente")
                    return True
                else:
                    self.logger.warning('EjecutarCaso', "No se encontró la opción de sede")
                    return False
            else:
                self.logger.warning('EjecutarCaso', "No se pudo ingresar texto en IPS Sede")
                return False
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error al buscar IPS Sede: {e}", e)
            return False
    
    def crear_archivo_error(self, data, tipo_error: str, descripcion_error: str, ruta_archivo: str = ""):
        """Crear archivo de errores detallado"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo_error = f"errores_archivos_{timestamp[:8]}.txt"
            
            with open(nombre_archivo_error, 'a', encoding='utf-8') as archivo:
                archivo.write(f"=== ERROR DE ARCHIVO ===\n")
                archivo.write(f"Timestamp: {datetime.datetime.now()}\n")
                archivo.write(f"Tipo Error: {tipo_error}\n")
                archivo.write(f"Descripción: {descripcion_error}\n")
                archivo.write(f"Paciente ID: {data.identificacion}\n")
                archivo.write(f"Orden Capita: {data.facturaEvento}\n")
                archivo.write(f"URL API Original: {data.urlOrdenMedica}\n")
                archivo.write(f"Ruta Archivo Buscada: {ruta_archivo}\n")
                archivo.write(f"Ruta Base Configurada: {config.get('PDF_BASE_PATH', '')}\n")
                archivo.write("="*50 + "\n\n")
            
            self.logger.info('EjecutarCaso', f"Error registrado en: {nombre_archivo_error}")
        except Exception as e:
            self.logger.error('EjecutarCaso', f"Error creando archivo de errores: {e}", e)
    
    def _hacer_clic_ok(self) -> bool:
        """Método para hacer clic en OK - con force y JS fallback"""
        try:
            selectors = [
                "//button[contains(@class,'swal2-confirm')]",
                "//button[contains(.,'OK')]",
                "button.swal2-confirm"
            ]
            
            for selector in selectors:
                try:
                    boton = self.page.wait_for_selector(selector, timeout=5000)
                    try:
                        boton.click(force=True)
                    except Exception:
                        self.page.evaluate("""(el) => el.click()""", boton)
                    print("Clic en OK exitoso")
                    time.sleep(1)
                    return True
                except:
                    continue
            
            # Último recurso: cerrar via JS
            self._cerrar_swal2()
            return True
        except Exception as e:
            print(f"Error haciendo clic en OK: {e}")
            return False
