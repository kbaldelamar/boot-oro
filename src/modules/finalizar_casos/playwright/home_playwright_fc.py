"""
Navegación del Home con Playwright - Módulo Finalizar Casos
Ruta: Servicios de salud → Referencia Ambulatoria
"""
import time
from playwright.sync_api import Page
from utils.logger import AdvancedLogger
from modules.finalizar_casos.playwright.helpers_playwright_fc import PlaywrightHelperFC


class HomePlaywrightFC:
    """Servicio para navegación del menú home (Finalizar Casos)"""
    
    def __init__(self, page: Page, logger: AdvancedLogger):
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelperFC(page)
    
    def navegar_a_referencia_ambulatoria(self) -> bool:
        """
        Navega al menú: Servicios de Salud → Referencia Ambulatoria.
        
        Returns:
            True si navegó exitosamente
        """
        try:
            self.logger.info('HomeFC', 'Navegando a Referencia Ambulatoria...')
            
            # 1. Click en "Servicios de salud"
            self.logger.debug('HomeFC', 'Paso 1: Click en Servicios de salud')
            servicios_xpath = "//div[@role='menuitem'][contains(.,'Servicios de salud')]"
            if not self.helper.click_element(servicios_xpath):
                self.logger.error('HomeFC', 'No se pudo hacer clic en Servicios de salud')
                return False
            
            self.logger.success('HomeFC', '✅ Click en Servicios de salud')
            time.sleep(1)
            
            # 2. Click en "Referencia Ambulatoria"
            self.logger.debug('HomeFC', 'Paso 2: Click en Referencia Ambulatoria')
            referencia_xpath = "//span[@class='ant-menu-title-content'][contains(.,'Referencia Ambulatoria')]"
            if not self.helper.click_element(referencia_xpath):
                self.logger.error('HomeFC', 'No se pudo hacer clic en Referencia Ambulatoria')
                return False
            
            self.logger.success('HomeFC', '✅ Click en Referencia Ambulatoria')
            time.sleep(3)
            
            # 3. Espera adicional para carga completa
            time.sleep(2)
            
            self.logger.success('HomeFC', '✅ Navegación a Referencia Ambulatoria completada')
            return True
            
        except Exception as e:
            self.logger.error('HomeFC', 'Error navegando a Referencia Ambulatoria', e)
            return False
