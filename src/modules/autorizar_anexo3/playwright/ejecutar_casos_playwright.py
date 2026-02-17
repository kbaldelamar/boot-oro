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


class EjecutarCasosPlaywright:
    """Servicio para ejecutar casos completos de pacientes - USANDO XPATHS DE SELENIUM"""
    
    def __init__(self, page: Page, logger: AdvancedLogger):
        """
        Args:
            page: Página de Playwright
            logger: Logger
        """
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelper(page)
        self.ingreso_items = IngresoItemsPlaywright(page, logger)
        self.pdf_service = PDFAnexo3Service(logger, config)
        self.modo_actual = config.get('MODE', 'REGULAR')  # CAPITATED o REGULAR
        print(f"Modo actual de operación: {self.modo_actual}")
    
    def inicio_casos(self, data) -> bool:
        """
        MÉTODO PRINCIPAL - Migrado de Selenium
        Ejecuta el caso completo de un paciente.
        """
        telefono_value = None
        telefono_value1 = None
        texto = None
        
        try:
            self.verificar_sesion_activa(data, "Error: Sesión del navegador no está activa al inicio del proceso de casos")
            
            self.logger.info('EjecutarCaso', f"tipoIdentificacion: {data.tipoIdentificacion}")
            print(data.tipoIdentificacion)
            
            # ====== SELECCIÓN DE TIPO DE IDENTIFICACIÓN ======
            if data.tipoIdentificacion == "Cédula de Ciudadanía":
                # Lógica especial para cédula
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
                # Lógica general para otros tipos de documento
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
                    self.page.wait_for_selector('.rc-virtual-list-holder', timeout=5000)
                    option = self.scroll_list_and_find_option(data.tipoIdentificacion)
                    time.sleep(1)
                    if option:
                        self.click_option(option)
                        print(f"Opción '{data.tipoIdentificacion}' seleccionada con éxito.")
                    else:
                        print(f"No se pudo encontrar la opción: {data.tipoIdentificacion}")
            
            # ====== VERIFICACIÓN DE SESIÓN ANTES DE CONTINUAR ======
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
            time.sleep(3)
            
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
                self.verificar_sesion_activa(data, "ANTES DE LLENAR FORMULARIO")
                
                # Correo (XPATH SELENIUM EXACTO)
                input_correo = self.page.wait_for_selector("#email", timeout=5000)
                input_correo.click()
                self.logger.info('EjecutarCaso', "Clicked on email input")
                input_correo.fill("")
                self.helper.ingresar_texto(input_correo, "GENOMA@GENOMA.com")
                self.logger.info('EjecutarCaso', f"Ingresó GENOMA@GENOMA.com")
                
                # Nombre de emergencia (XPATH SELENIUM EXACTO)
                input_nombre_e = self.page.wait_for_selector("#emergencyContactName", timeout=5000)
                input_nombre_e.click()
                input_nombre_e.fill("")
                self.helper.ingresar_texto(input_nombre_e, "emergencia")
                self.logger.info('EjecutarCaso', f"Ingresó emergencia")
                
                # Teléfono principal (XPATH SELENIUM EXACTO)
                input_telefono = self.page.wait_for_selector("#telefono", timeout=5000)
                telefono_value = input_telefono.get_attribute('value')
                self.logger.info('EjecutarCaso', f"Valor actual del campo de teléfono: {telefono_value}")
                
                if telefono_value:
                    self.logger.info('EjecutarCaso', "El campo de teléfono tiene un valor.")
                    if len(telefono_value) == 10:
                        print("El número de teléfono tiene 10 caracteres.")
                    else:
                        input_telefono.click(click_count=2)
                        input_telefono.press("Delete")
                        self.helper.ingresar_texto(input_telefono, str(data.telefono))
                else:
                    self.logger.info('EjecutarCaso', "El campo de teléfono está vacío.")
                    input_telefono.click()
                    input_telefono.fill("")
                    self.helper.ingresar_texto(input_telefono, str(data.telefono))
                    self.logger.info('EjecutarCaso', f"Ingresó telefono")
                
                # Teléfono de emergencia (XPATH SELENIUM EXACTO)
                input_telefono_1 = self.page.wait_for_selector("#emergencyContactPhone", timeout=5000)
                telefono_value1 = input_telefono_1.get_attribute('value')
                self.logger.info('EjecutarCaso', f"Valor actual del campo de teléfono de emergencia: {telefono_value1}")
                
                if telefono_value1:
                    self.logger.info('EjecutarCaso', "El campo de teléfono de emergencia tiene un valor.")
                    if len(telefono_value1) == 10:
                        print("El número de teléfono tiene 10 caracteres.")
                    else:
                        input_telefono_1.click(click_count=2)
                        input_telefono_1.press("Delete")
                        self.helper.ingresar_texto(input_telefono_1, str(data.telefono))
                else:
                    self.logger.info('EjecutarCaso', "El campo de teléfono de emergencia está vacío.")
                    input_telefono_1.click()
                    input_telefono_1.fill("")
                    self.helper.ingresar_texto(input_telefono_1, str(data.telefono))
                    self.logger.info('EjecutarCaso', f"Ingresó telefono")
                
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
                self.verificar_sesion_activa(data, "ANTES DE INGRESAR FECHA")
                
                # Fecha de orden (XPATH SELENIUM EXACTO)
                self.page.evaluate("window.scrollBy(0, 400);")
                time.sleep(2)
                input_fecha_orden = self.page.wait_for_selector("//input[contains(@placeholder,'Select date')]", timeout=5000)
                input_fecha_orden.click()
                self.logger.info('EjecutarCaso', "Clicked on date input")
                input_fecha_orden.fill("")
                self.helper.ingresar_texto(input_fecha_orden, data.fechaFacturaEvento)
                input_fecha_orden.press("Enter")
                self.logger.info('EjecutarCaso', f"Ingresó la fecha: {data.fechaFacturaEvento}")
                time.sleep(1)
                
                # IPS REMITENTE (XPATH SELENIUM EXACTO)
                try:
                    input_IPSREMITE = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* IPS Remitente:')]/parent::div/div/div", timeout=5000)
                    input_IPSREMITE.click()
                    self.logger.info('EjecutarCaso', "Clicked on IPS Remitente input")
                    time.sleep(1)
                    
                    # IPS Remitente: usar NITIPS + NOMBREIPS del .env
                    nit_config = (config.nit_ips or "").strip()
                    nombre_config = (config.nombre_ips or "").strip()
                    if nit_config and nombre_config:
                        nombre_ips_remitente = f"{nit_config} - {nombre_config}"
                    else:
                        nombre_ips_remitente = nombre_config or nit_config
                    self.logger.info('EjecutarCaso', f"IPS Remitente desde config: '{nombre_ips_remitente}'")
                    
                    if not nombre_ips_remitente:
                        raise Exception("No se encontró NITIPS/NOMBREIPS en configuración")
                    
                    # Extraer el NIT (primer parte antes del guión) para búsqueda
                    nit_busqueda = nit_config or (nombre_ips_remitente.split('-')[0].strip() if '-' in nombre_ips_remitente else nombre_ips_remitente)
                    
                    if not self.helper.ingresar_texto_secuencial(input_IPSREMITE, nit_busqueda):
                        self.logger.info('EjecutarCaso', f"No se pudo ingresar texto secuencialmente: '{nit_busqueda}'")
                        raise Exception(f"No se pudo ingresar el NIT de IPS Remitente: {nit_busqueda}")
                    
                    time.sleep(2)
                    try:
                        self.page.wait_for_selector("//div[@class='ant-select-dropdown']", timeout=5000)
                    except:
                        self.logger.info('EjecutarCaso', "Dropdown no apareció, reintentando input")
                        input_IPSREMITE.click()
                        time.sleep(1)
                    
                    # Buscar opción que contenga el NIT
                    opciones_a_buscar = [
                        f"//div[@class='ant-select-item-option-content'][contains(text(),'{nit_busqueda}')]",
                        f"//div[contains(@class,'ant-select-item-option-content')][contains(.,'{nit_busqueda}')]"
                    ]
                    
                    option = None
                    for xpath_opcion in opciones_a_buscar:
                        try:
                            option = self.page.wait_for_selector(xpath_opcion, timeout=3000)
                            self.logger.info('EjecutarCaso', f"Opción encontrada with XPath: {xpath_opcion}")
                            break
                        except:
                            continue
                    
                    if option:
                        option.click()
                        self.logger.info('EjecutarCaso', f"IPS Remitente seleccionada: {nombre_ips_remitente}")
                    else:
                        try:
                            opciones_disponibles = self.page.query_selector_all("//div[@class='ant-select-item-option-content']")
                            self.logger.info('EjecutarCaso', f"Opciones disponibles: {len(opciones_disponibles)}")
                            for i, opcion in enumerate(opciones_disponibles[:5]):
                                self.logger.info('EjecutarCaso', f"Opción {i+1}: {opcion.text_content()}")
                        except Exception as e:
                            self.logger.info('EjecutarCaso', f"Error al listar opciones disponibles: {e}")
                        raise Exception(f"No se encontró la opción de IPS Remitente: {nombre_ips_remitente}")
                
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
                    time.sleep(1)
                    
                    search_text = "Enfermedad"
                    if self.helper.ingresar_texto_secuencial(input_causa, search_text):
                        self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                        time.sleep(1)
                        
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
                time.sleep(1)
                input_prioridad = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* Prioridad de la atención')]/parent::div/div", timeout=5000)
                input_prioridad.click()
                self.logger.info('EjecutarCaso', "Clicked prioridad")
                
                # XPATH SELENIUM EXACTO
                clic_prioridad = self.page.wait_for_selector("//div[@class='ant-select-item-option-content'][contains(.,'No prioritaria')]", timeout=5000)
                clic_prioridad.click()
                self.logger.info('EjecutarCaso', "Clicked prioritaria combo")
                time.sleep(1)
                
                # ====== VERIFICACIÓN DE SESIÓN ANTES DE DIAGNÓSTICO ======
                self.verificar_sesion_activa(data, "ANTES DE INGRESAR DIAGNÓSTICO")
                
                # Diagnóstico (XPATH SELENIUM EXACTO)
                try:
                    input_dx = self.page.wait_for_selector("//input[contains(@aria-owns,'diagnostico_list')]", timeout=5000)
                    input_dx.click()
                    self.logger.info('EjecutarCaso', "Clicked on Diagnóstico input")
                    time.sleep(1)
                    
                    if self.helper.ingresar_texto_secuencial(input_dx, data.diagnostico):
                        self.logger.info('EjecutarCaso', f"Texto ingresado correctamente: {data.diagnostico}")
                        time.sleep(2)
                        
                        # XPATH SELENIUM EXACTO
                        dynamic_xpath_dx = f"//div[@class='ant-select-item-option-content'][contains(.,'{data.diagnostico}')]"
                        option = self.page.wait_for_selector(dynamic_xpath_dx, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionado Diagnóstico correctamente")
                        time.sleep(1)
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
                    time.sleep(1)
                    
                    input_modalidad = self.page.wait_for_selector("//label[@class='form-label'][contains(.,'* Modalidad de realización de la tecnologia de salud')]/parent::div/div/div", timeout=5000)
                    input_modalidad.click()
                    self.logger.info('EjecutarCaso', "Clicked on Modalidad input")
                    time.sleep(1)
                    
                    search_text = "Intramural"
                    if self.helper.ingresar_texto_secuencial(input_modalidad, search_text):
                        self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                        time.sleep(1)
                        
                        # XPATH SELENIUM EXACTO
                        option_xpath = "//div[@class='ant-select-item-option-content'][contains(.,'Intramural')]"
                        option = self.page.wait_for_selector(option_xpath, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionada Modalidad Intramural")
                        time.sleep(1)
                    else:
                        raise Exception("No se pudo ingresar el texto en el campo Modalidad")
                
                except Exception as e:
                    print(f"Error detallado en Modalidad: {str(e)}")
                    self.logger.error('EjecutarCaso', f"Error al manejar Modalidad: {str(e)}", e)
                    raise
                
                # ====== INGRESO DE SERVICIOS (método sobrescribible) ======
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
                    time.sleep(1)
                    
                    search_text = "Paciente"
                    if self.helper.ingresar_texto_secuencial(input_condicion, search_text):
                        self.logger.info('EjecutarCaso', "Texto ingresado correctamente")
                        time.sleep(1)
                        
                        # XPATH SELENIUM EXACTO
                        option_xpath = "//div[@class='ant-select-item-option-content'][contains(.,'Paciente con destino a su domicilio')]"
                        option = self.page.wait_for_selector(option_xpath, timeout=5000)
                        option.click()
                        self.logger.info('EjecutarCaso', "Seleccionada Condición: Paciente con destino a su domicilio")
                        time.sleep(1)
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
                time.sleep(1)
                self.page.evaluate("window.scrollBy(0, 100)")
                time.sleep(1)
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
                file_path = self._obtener_archivo_pdf(data)
                if not file_path:
                    return False  # El método ya manejó el error y reinicio
                
                # Verificar sesión antes de subir archivos
                self.verificar_sesion_activa(data, "ANTES DE SUBIR ARCHIVOS")
                
                try:
                    # USANDO IDs SELENIUM EXACTOS
                    file_input = self.page.query_selector("#fileListOrdenMedica")
                    file_input.set_input_files(file_path)
                    self.logger.info('EjecutarCaso', f"✅ Archivo cargado en fileListOrdenMedica")
                    
                    file_input_hc = self.page.query_selector("#fileListHistoriaClinica")
                    file_input_hc.set_input_files(file_path)
                    self.logger.info('EjecutarCaso', f"✅ Archivo cargado en fileListHistoriaClinica")
                    
                    time.sleep(1)
                except Exception as e:
                    error_msg = f"Error al cargar archivo en campos de entrada: {e}"
                    self.logger.error('EjecutarCaso', f"❌ {error_msg}", e)
                    self.crear_archivo_error(data, "ERROR_CARGA_ARCHIVO", error_msg, file_path)
                    raise
                
                self.page.evaluate("window.scrollBy(0, 100)")
                time.sleep(2)
                
                # XPATH SELENIUM EXACTO - Usar justificación del JSON
                txt_area = self.page.wait_for_selector("#descripcion", timeout=5000)
                txt_area.fill("")
                print("area")
                time.sleep(1)
                justificacion_texto = getattr(data, 'justificacion', '') or 'Orden de autorización'
                # Limpiar comillas extra si las hay
                justificacion_texto = justificacion_texto.strip('"').strip()
                self.helper.ingresar_texto(txt_area, justificacion_texto)
                self.logger.info('EjecutarCaso', f"ingreso input justificación: {justificacion_texto[:50]}...")
                time.sleep(2)
                
                self.page.evaluate("window.scrollBy(0, 400)")
                time.sleep(1)
                
                # ====== VERIFICACIÓN DE SESIÓN ANTES DE GUARDAR ======
                self.verificar_sesion_activa(data, "ANTES DE GUARDAR")
                
                # XPATH SELENIUM EXACTO
                bonton_guardar = self.page.wait_for_selector("//button[@type='submit'][contains(.,'Guardar')]", timeout=10000)
                print("bonton_guardar")
                bonton_guardar.click()
                self.logger.info('EjecutarCaso', f"clic boton guardar")
                time.sleep(7)
                
                try:
                    # Buscar modal de respuesta
                    modal = self.page.wait_for_selector("//div[@aria-labelledby='swal2-title']", timeout=30000)
                    modal.click()
                    
                    # Verificar si hay error
                    try:
                        error_title = self.page.query_selector("//h2[contains(.,'Error')]")
                        if error_title and error_title.is_visible():
                            error_text = "Error sin detalle"
                            try:
                                error_el = self.page.query_selector("//div[contains(@class,'swal2-html-container') or @id='swal2-html-container']")
                                error_text = (error_el.text_content() or "").strip() or error_text
                            except Exception as e:
                                self.logger.warning('EjecutarCaso', f"⚠️ No se pudo leer swal2-html-container: {e}")
                            
                            # NUEVO: Verificar si es error de solicitud activa (manejarlo como éxito)
                            if "solicitud activa" in error_text.lower() and "número de radicado" in error_text.lower():
                                self.logger.info('EjecutarCaso', f"✅ SOLICITUD ACTIVA DETECTADA - Tratando como éxito")
                                
                                # Extraer el número de radicado
                                numero_radicado = ""
                                radicado_match = re.search(r'número de radicado\s*#?\s*(\d+)', error_text, re.IGNORECASE)
                                if radicado_match:
                                    numero_radicado = radicado_match.group(1)
                                    self.logger.info('EjecutarCaso', f"📝 Número de radicado extraído: {numero_radicado}")
                                else:
                                    # Fallback: extraer cualquier número
                                    numbers = re.findall(r'\d+', error_text)
                                    numero_radicado = ''.join(numbers) if numbers else ""
                                    self.logger.warning('EjecutarCaso', f"⚠️ Usando fallback para número: {numero_radicado}")
                                
                                # Guardar en archivo como caso exitoso
                                with open("archivo.txt", 'a', encoding='utf-8') as archivo:
                                    archivo.write(f"caso,SOLICITUD ACTIVA - {error_text},paciente,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
                                
                                # Hacer clic OK y actualizar como completado
                                self._hacer_clic_ok()
                                
                                # Actualizar como exitoso (estado "1") con el número de radicado y resultado_ejecucion
                                self.actualizar_con_resultado_ejecucion(data, "1", numero_radicado, error_text)
                                
                                self.reinicio()
                                time.sleep(5)
                                self.alerta()
                                return True  # ÉXITO: Solicitud activa tratada como completada
                            
                            # Si no es solicitud activa, manejar como error normal
                            # Extraer fragmento
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
                            raise Exception("No es error")
                    except:
                        # NO HAY ERROR - ES ÉXITO
                        try:
                            success_element = self.page.query_selector("//h2[contains(.,'Correcto')]")
                            success_text = success_element.text_content()
                            print(f"ÉXITO: {success_text}")
                            
                            numbers = re.findall(r'\d+', success_text)
                            numbers_str = ''.join(numbers)
                            
                            with open("archivo.txt", 'a', encoding='utf-8') as archivo:
                                archivo.write(f"caso,{success_text},paciente,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
                            
                            self._hacer_clic_ok()
                            self.actualizar(data, "3", numbers_str)
                            self.reinicio()
                            time.sleep(5)
                            self.alerta()
                            return True  # ÉXITO: Caso completado correctamente
                        except:
                            print("No se pudo determinar el resultado")
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
            elif "no se pudo encontrar" in error_message and "archivo" in error_message:
                self.logger.error('EjecutarCaso', f"📄 ARCHIVO PDF NO ENCONTRADO", e)
                print(f"[PDF FALTANTE] Paciente {data.identificacion} - Documento no encontrado")
                self.actualizar(data, "17", "")
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
                time.sleep(0.8)
                
                options = self.page.query_selector_all("//div[contains(@class, 'ant-select-item-option-content')]")
                
                for option in options:
                    try:
                        option_content = option.text_content().strip()
                        if option_content:
                            found_options.add(option_content)
                            self.logger.debug('EjecutarCaso', f"Comparando opción visible: '{option_content}' con opción buscada: '{option_text}'")
                            
                            if option_content == option_text:
                                self.logger.info('EjecutarCaso', f"Opción encontrada: {option_content}")
                                option.scroll_into_view_if_needed()
                                time.sleep(0.5)
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
        
        Mapeo de estados (de Selenium):
        - "1" = Completado/OK (envía numeroAutorizacion)
        - "3" = En proceso (con número de orden)
        - "4" = Error - error por tipo de documento 
        - "11" = Error - No se encontró paciente
        - "12" = Error - Sesión perdida
        - "13" = Error - No se encontró diagnóstico  
        - "14" = Error - No se pudo seleccionar IPS
        - "15" = Error - No se pudo guardar
        - "16" = Error - Timeout
        - "17" = Error - Otro
        - "18" = Error - No se encontró el botón
        - "19" = Error - No se pudo determinar resultado
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
    
    def reinicio(self):
        """Método de reinicio - XPATH SELENIUM EXACTO"""
        try:
            self.logger.info('EjecutarCaso', "🔄 Iniciando proceso de reinicio...")
            
            if not self.verificar_sesion_activa():
                self.logger.error('EjecutarCaso', "❌ Sesión no activa, no se puede realizar reinicio", None)
                raise SessionLostException("Sesión perdida durante reinicio")
            
            time.sleep(1)
            self.page.evaluate("window.scrollTo(0, 0);")
            time.sleep(1)
            
            url_actual = self.page.url
            if "portalsalud.coosalud.com" not in url_actual:
                self.logger.error('EjecutarCaso', f"❌ No estamos en la página correcta: {url_actual}", None)
                raise Exception("Página incorrecta para reinicio")
            
            # XPATH SELENIUM EXACTO
            try:
                bonton_urg = self.page.wait_for_selector("//span[contains(.,'Reportar')]/parent::div/following-sibling::ul/li/span[contains(.,'Urgencias')]", timeout=10000)
                bonton_urg.click()
                self.logger.info('EjecutarCaso', "✅ Clic en botón Urgencias")
                time.sleep(1)
            except Exception as e:
                self.logger.error('EjecutarCaso', f"❌ Error haciendo clic en Urgencias: {e}", e)
                raise
            
            # XPATH SELENIUM EXACTO
            try:
                bonton_amb = self.page.wait_for_selector("//span[contains(.,'Reportar')]/parent::div/following-sibling::ul/li/span[contains(.,'Ambulatoria')]", timeout=10000)
                bonton_amb.click()
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
        for componente in componentes:
            texto = self.obtener_texto_componente(componente)
            if texto is not None:
                print(texto)
                break
        
        if texto is not None:
            bonton_ok = self.page.wait_for_selector("body > div.swal2-container.swal2-center.swal2-backdrop-show > div > div.swal2-actions > button.swal2-confirm.swal2-styled", timeout=5000)
            print("bonton_ok")
            bonton_ok.click()
            self.logger.info('EjecutarCaso', f"clic boton bonton_ok")
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
            time.sleep(1)
            
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
                time.sleep(2)
                
                # Esperar opciones
                max_intentos = 15
                opciones_con_texto = []
                
                for intento in range(max_intentos):
                    try:
                        time.sleep(0.5)
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
        """Método para hacer clic en OK"""
        try:
            selectors = [
                "//button[contains(@class,'swal2-confirm')]",
                "//button[contains(.,'OK')]",
                "button.swal2-confirm"
            ]
            
            for selector in selectors:
                try:
                    boton = self.page.wait_for_selector(selector, timeout=5000)
                    boton.click()
                    print("Clic en OK exitoso")
                    time.sleep(1)
                    return True
                except:
                    continue
            
            print("No se encontró botón OK")
            return False
        except Exception as e:
            print(f"Error haciendo clic en OK: {e}")
            return False
