"""
Ingreso de Items (CUPS) con Playwright
"""
import time
from playwright.sync_api import Page
from utils.logger import AdvancedLogger
from modules.autorizar_anexo3.playwright.helpers_playwright import PlaywrightHelper


class IngresoItemsPlaywright:
    """Servicio para ingresar items CUPS"""
    
    def __init__(self, page: Page, logger: AdvancedLogger):
        """
        Args:
            page: Página de Playwright
            logger: Logger
        """
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelper(page)
    
    def IntemsAndFor(self, data):
        """
        MÉTODO PRINCIPAL - Migrado de Selenium (versión simplificada para un solo CUPS)
        Ingresa el código CUPS que viene en data.cups
        
        Args:
            data: Objeto con atributo 'cups' que contiene el código CUPS (ej: "890350")
        """
        try:
            codigo_cups = data.cups if hasattr(data, 'cups') else None
            
            if not codigo_cups:
                self.logger.error('IngresoItems', "❌ No se encontró código CUPS en data.cups")
                raise Exception("Código CUPS no encontrado en data")
            
            self.logger.info('IngresoItems', f"=== PROCESANDO CUPS {codigo_cups} ===")
            self.logger.info('IngresoItems', f"codigo: {codigo_cups}")
            
            # Espera breve para estabilizar la página
            time.sleep(0.5)
            
            # Paso 1: Buscar campo CUPS con timeout aumentado (XPATH SELENIUM EXACTO)
            self.logger.info('IngresoItems', "Paso 1: Buscando campo CUPS...")
            input_cups = self.page.wait_for_selector("//h5/following-sibling::div/div/div/div/span/input", timeout=20000)
            self.logger.info('IngresoItems', "✓ Campo CUPS encontrado")
            
            # Paso 2: Limpiar y hacer clic
            input_cups.fill("")
            input_cups.click()
            self.logger.info('IngresoItems', "✓ Clic en campo CUPS")
            
            # Paso 3: Ingresar código
            self.logger.info('IngresoItems', f"Paso 3: Ingresando código {codigo_cups}...")
            self.helper.ingresar_texto(input_cups, str(codigo_cups))
            self.logger.info('IngresoItems', f"✓ Código ingresado: {codigo_cups}")
            
            # Espera para que aparezcan las opciones
            time.sleep(1.5)
            
            # Paso 4: Buscar opción en dropdown con manejo robusto (XPATH EXACTO - EXCLUYE VARIANTES NUMÉRICAS)
            self.logger.info('IngresoItems', "Paso 4: Buscando opción en dropdown...")
            # XPath que excluye variantes con sufijos numéricos (ej: 902210-1, 890282-01, etc.)
            dynamic_xpath_dx = (
                f"//div[@class='ant-select-item-option-content']"
                f"[starts-with(text(),'{codigo_cups}-') "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'0')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'1')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'2')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'3')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'4')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'5')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'6')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'7')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'8')) "
                f"and not(starts-with(substring-after(text(),'{codigo_cups}-'),'9'))]"
            )
            self.logger.info('IngresoItems', f"XPath de búsqueda (sin variantes numéricas): {dynamic_xpath_dx}")
            
            try:
                # Primer intento con timeout estándar
                clic_Dx = self.page.wait_for_selector(dynamic_xpath_dx, timeout=15000)
                self.logger.info('IngresoItems', "✓ Opción encontrada en primer intento")
                
            except Exception as timeout_error:
                self.logger.info('IngresoItems', f"⚠️ Timeout en primer intento para CUPS {codigo_cups}")
                self.logger.info('IngresoItems', "Intentando scroll y segundo intento...")
                
                # Verificar qué opciones están disponibles
                opciones_disponibles = self.page.query_selector_all("//div[@class='ant-select-item-option-content']")
                self.logger.info('IngresoItems', f"Opciones disponibles en dropdown: {len(opciones_disponibles)}")
                
                for i, opcion in enumerate(opciones_disponibles[:3]):  # Mostrar solo las primeras 3
                    try:
                        texto_opcion = opcion.text_content().strip()
                        self.logger.info('IngresoItems', f"Opción {i+1}: '{texto_opcion}'")
                    except Exception as opcion_error:
                        self.logger.info('IngresoItems', f"Error al leer opción {i+1}: {opcion_error}")
                
                # Hacer scroll para cargar más opciones
                self.page.evaluate("window.scrollTo(0, 0);")
                time.sleep(1)
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Segundo intento con timeout más largo
                try:
                    clic_Dx = self.page.wait_for_selector(dynamic_xpath_dx, timeout=25000)
                    self.logger.info('IngresoItems', "✓ Opción encontrada en segundo intento")
                except:
                    self.logger.error('IngresoItems', f"❌ Error definitivo: No se encontró opción para CUPS {codigo_cups}")
                    raise Exception(f"No se encontró opción para CUPS {codigo_cups}")
            
            # Paso 5: Hacer clic en la opción
            self.logger.info('IngresoItems', "Paso 5: Haciendo clic en opción...")
            clic_Dx.click()
            self.logger.info('IngresoItems', f"✓ CUPS {codigo_cups} seleccionado correctamente")
            
        except Exception as e:
            self.logger.error('IngresoItems', f"❌ Error general en IntemsAndFor: {str(e)}", e)
            print(f"Error general en IntemsAndFor: {str(e)}")
            print(f"Tipo de error: {type(e).__name__}")
            raise
        
        finally:
            try:
                # Intentar hacer clic en Aceptar/Volver sin importar si hubo errores (XPATH SELENIUM EXACTO)
                self.logger.info('IngresoItems', "=== FINALIZANDO - Haciendo clic en Aceptar ===")
                time.sleep(0.5)
                clic_aceptar = self.page.wait_for_selector("//span[contains(.,'Aceptar')]", timeout=15000)
                clic_aceptar.click()
                self.logger.info('IngresoItems', "✓ Clicked Aceptar - Proceso finalizado")
            except Exception as volver_error:
                self.logger.error('IngresoItems', f"❌ Error al intentar hacer clic en Aceptar: {str(volver_error)}", volver_error)
                print(f"Error al intentar hacer clic en Aceptar: {str(volver_error)}")
                raise  # Lanzar el error si no se puede hacer clic en Aceptar
