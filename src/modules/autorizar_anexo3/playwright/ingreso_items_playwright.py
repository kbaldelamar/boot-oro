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
                clic_cups = self.page.wait_for_selector(dynamic_xpath_dx, timeout=15000)
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
                    clic_cups = self.page.wait_for_selector(dynamic_xpath_dx, timeout=25000)
                    self.logger.info('IngresoItems', "✓ Opción encontrada en segundo intento")
                except:
                    self.logger.error('IngresoItems', f"❌ Error definitivo: No se encontró opción para CUPS {codigo_cups}")
                    raise Exception(f"No se encontró opción para CUPS {codigo_cups}")
            
            # Paso 5: Hacer clic en la opción
            self.logger.info('IngresoItems', "Paso 5: Haciendo clic en opción...")
            clic_cups.click(timeout=15000)  # Timeout de 15s en lugar de 60s por defecto
            self.logger.info('IngresoItems', f"✓ CUPS {codigo_cups} seleccionado correctamente")
            
        except Exception as e:
            self.logger.error('IngresoItems', f"❌ Error general en IntemsAndFor: {str(e)}", e)
            print(f"Error general en IntemsAndFor: {str(e)}")
            print(f"Tipo de error: {type(e).__name__}")
            raise
        
        finally:
            # === CERRAR MODAL DE PROCEDIMIENTOS CON MÚLTIPLES ESTRATEGIAS ===
            self.logger.info('IngresoItems', "=== FINALIZANDO - Cerrando modal de procedimientos ===")
            modal_cerrado = False
            
            # Estrategia 1: Botón "Aceptar" (flujo normal)
            try:
                time.sleep(0.5)
                clic_aceptar = self.page.wait_for_selector("//span[contains(.,'Aceptar')]", timeout=8000)
                if clic_aceptar and clic_aceptar.is_visible():
                    clic_aceptar.click()
                    time.sleep(1)
                    self.logger.info('IngresoItems', "✅ Modal cerrado con botón Aceptar")
                    modal_cerrado = True
            except Exception as e:
                self.logger.warning('IngresoItems', f"⚠️ Estrategia 1 falló (botón Aceptar): {str(e)}")
            
            # Estrategia 2: Verificar si el modal aún está visible y usar ESC
            if not modal_cerrado:
                try:
                    modal_visible = self.page.query_selector(".ant-modal-wrap:not([style*='display: none'])")
                    if modal_visible and modal_visible.is_visible():
                        self.logger.info('IngresoItems', "⚠️ Modal aún visible, presionando ESC...")
                        self.page.keyboard.press("Escape")
                        time.sleep(1)
                        self.logger.info('IngresoItems', "✅ Modal cerrado con ESC")
                        modal_cerrado = True
                except Exception as e:
                    self.logger.warning('IngresoItems', f"⚠️ Estrategia 2 falló (ESC): {str(e)}")
            
            # Estrategia 3: Botón X de cerrar modal
            if not modal_cerrado:
                try:
                    boton_cerrar = self.page.query_selector(".ant-modal-close, .ant-modal-close-x")
                    if boton_cerrar and boton_cerrar.is_visible():
                        self.logger.info('IngresoItems', "⚠️ Intentando cerrar con botón X...")
                        boton_cerrar.click()
                        time.sleep(1)
                        self.logger.info('IngresoItems', "✅ Modal cerrado con botón X")
                        modal_cerrado = True
                except Exception as e:
                    self.logger.warning('IngresoItems', f"⚠️ Estrategia 3 falló (botón X): {str(e)}")
            
            # Estrategia 4: Clic en overlay (backdrop) del modal
            if not modal_cerrado:
                try:
                    overlay = self.page.query_selector(".ant-modal-wrap")
                    if overlay and overlay.is_visible():
                        self.logger.info('IngresoItems', "⚠️ Intentando cerrar con clic en overlay...")
                        # Hacer clic en las coordenadas del overlay (fuera del contenido del modal)
                        overlay.click(position={"x": 10, "y": 10})
                        time.sleep(1)
                        self.logger.info('IngresoItems', "✅ Modal cerrado con clic en overlay")
                        modal_cerrado = True
                except Exception as e:
                    self.logger.warning('IngresoItems', f"⚠️ Estrategia 4 falló (overlay): {str(e)}")
            
            # Estrategia 5: JavaScript directo para remover el modal (último recurso)
            if not modal_cerrado:
                try:
                    self.logger.warning('IngresoItems', "⚠️ Último recurso: Removiendo modal con JavaScript...")
                    resultado = self.page.evaluate("""
                        (() => {
                            // Buscar modal de Ant Design
                            const modal = document.querySelector('.ant-modal-wrap');
                            if (modal) {
                                modal.remove();
                                return 'removed_modal';
                            }
                            // Buscar backdrop
                            const backdrop = document.querySelector('.ant-modal-mask');
                            if (backdrop) {
                                backdrop.remove();
                                return 'removed_backdrop';
                            }
                            return 'none';
                        })()
                    """)
                    if resultado != 'none':
                        self.logger.info('IngresoItems', f"✅ Modal removido con JavaScript ({resultado})")
                        modal_cerrado = True
                    time.sleep(0.5)
                except Exception as e:
                    self.logger.error('IngresoItems', f"❌ Estrategia 5 falló (JavaScript): {str(e)}")
            
            # Resultado final
            if modal_cerrado:
                self.logger.info('IngresoItems', "✅ Proceso finalizado - Modal cerrado correctamente")
            else:
                self.logger.error('IngresoItems', "❌ ADVERTENCIA: No se pudo confirmar el cierre del modal")
            # NO lanzar excepción aquí - continuar el flujo
