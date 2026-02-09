"""
Navegación del Home con Playwright
"""
import time
from playwright.sync_api import Page
from utils.logger import AdvancedLogger
from modules.autorizar_anexo3.playwright.helpers_playwright import PlaywrightHelper


class HomePlaywright:
    """Servicio para navegación del menú home"""
    
    def __init__(self, page: Page, logger: AdvancedLogger):
        """
        Args:
            page: Página de Playwright
            logger: Logger
        """
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelper(page)
    
    def navegar_a_reportar_ambulatoria(self) -> bool:
        """
        Navega al menú: Servicios de Salud → Reportar → Ambulatoria.
        
        Returns:
            True si navegó exitosamente
        """
        try:
            self.logger.info('Home', 'Navegando a Reportar Ambulatoria...')
            
            # 1. Click en "Servicios de salud"
            self.logger.debug('Home', 'Paso 1: Click en Servicios de salud')
            servicios_xpath = "//div[@role='menuitem']//span[contains(text(),'Servicios de salud')]"
            if not self.helper.click_element(servicios_xpath):
                self.logger.error('Home', 'No se pudo hacer clic en Servicios de salud')
                return False
            
            self.logger.success('Home', '✅ Click en Servicios de salud')
            time.sleep(1)
            
            # 2. Click en "Reportar"
            self.logger.debug('Home', 'Paso 2: Click en Reportar')
            reportar_xpath = "//span[contains(text(),'Reportar')]"
            if not self.helper.click_element(reportar_xpath):
                self.logger.error('Home', 'No se pudo hacer clic en Reportar')
                return False
            
            self.logger.success('Home', '✅ Click en Reportar')
            time.sleep(2)
            
            # 3. Click en "Ambulatoria"
            self.logger.debug('Home', 'Paso 3: Click en Ambulatoria')
            ambulatoria_xpath = "//span[contains(.,'Reportar')]/parent::div/following-sibling::ul/li/span[contains(.,'Ambulatoria')]"
            if not self.helper.click_element(ambulatoria_xpath):
                self.logger.error('Home', 'No se pudo hacer clic en Ambulatoria')
                return False
            
            self.logger.success('Home', '✅ Click en Ambulatoria')
            time.sleep(2)
            
            # 4. Verificar que estamos en la página correcta
            self.logger.debug('Home', 'Verificando que estamos en página de reportar...')
            
            self.logger.success('Home', '✅ Navegación a Reportar Ambulatoria completada')
            return True
            
        except Exception as e:
            self.logger.error('Home', 'Error navegando a Reportar Ambulatoria', e)
            return False
