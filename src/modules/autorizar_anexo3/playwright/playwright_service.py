"""
Servicio principal de Playwright
Manejo de navegador, contexto y sesión persistente
"""
import os
import time
import sys
from pathlib import Path
import sys
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from utils.logger import AdvancedLogger
from utils.paths import get_data_path


class PlaywrightService:
    """Servicio para gestionar Playwright con sesión persistente"""
    
    def __init__(self, logger: Optional[AdvancedLogger] = None):
        """
        Args:
            logger: Instancia del logger
        """
        self.logger = logger or AdvancedLogger()
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Archivos de sesión y screenshots
        self.session_dir = get_data_path("session_data")
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "session_state.json"
        
        self.screenshots_dir = get_data_path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
    
    def iniciar_navegador(self, reutilizar_sesion: bool = True) -> bool:
        """
        Inicia el navegador Chromium con Playwright.
        
        Returns:
            True si se inició correctamente
        """
        # Detectar si estamos ejecutando desde .exe
        is_frozen = getattr(sys, 'frozen', False)
        
        try:
            self.logger.info('Playwright', 'Iniciando Playwright...')
            
            # 1. Iniciar Playwright
            self.playwright = sync_playwright().start()
            self.logger.debug('Playwright', 'Playwright iniciado')
            
            # 2. Lanzar Chromium con configuración más robusta
            self.logger.info('Playwright', 'Lanzando navegador Chromium...')
            
            launch_options = {
                'headless': False,
                'args': [
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu'
                ]
            }
            
            # Si estamos en .exe, intentar usar navegadores empaquetados o Chrome del sistema
            if is_frozen:
                self.logger.info('Playwright', '🔄 Ejecutando desde .exe - Configurando navegadores...')
                browser_path = self._configure_playwright_browsers()
                if browser_path:
                    launch_options['executable_path'] = browser_path
                    self.logger.info('Playwright', f'✅ Usando navegador: {browser_path}')
                else:
                    self.logger.warning('Playwright', '⚠️ Navegador no encontrado, intentando con Playwright por defecto...')
            
            self.browser = self.playwright.chromium.launch(**launch_options)
            self.logger.success('Playwright', 'Navegador Chromium lanzado')
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error('Playwright', f'Error al iniciar navegador: {error_msg}')
            
            # Si estamos en .exe y falló, intentar Edge como fallback
            if is_frozen and 'Executable doesn\'t exist' in error_msg:
                try:
                    self.logger.info('Playwright', '🔄 Intentando con Microsoft Edge como fallback...')
                    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                    if os.path.exists(edge_path):
                        launch_options['executable_path'] = edge_path
                        self.browser = self.playwright.chromium.launch(**launch_options)
                        self.logger.success('Playwright', '✅ Navegador Edge lanzado exitosamente')
                    else:
                        raise Exception("Edge tampoco está disponible")
                except Exception as edge_error:
                    self.logger.error('Playwright', f'Edge también falló: {edge_error}')
                    self.cerrar()
                    return False
            else:
                self.cerrar()
                return False
        
        try:
            # 3. Crear contexto con user agent real
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True
            )
            
            # 4. Crear página
            self.page = self.context.new_page()
            self.page.set_default_timeout(60000)
            self.logger.success('Playwright', 'Página creada')
            
            # 5. Navegar a la URL - usar domcontentloaded como Selenium
            self.logger.info('Playwright', 'Navegando a página inicial...')
            # domcontentloaded: espera solo a que el DOM esté listo (como Selenium)
            # NO espera imágenes, CSS externos, etc que pueden estar lentos
            try:
                self.page.goto(
                    'https://portalsalud.coosalud.com/login', 
                    wait_until='domcontentloaded',
                    timeout=15000
                )
                self.logger.success('Playwright', 'Navegación completada')
            except Exception as nav_error:
                # Si hay timeout pero la página cargó parcialmente, continuar
                self.logger.warning('Playwright', f'Timeout en navegación, verificando si la página cargó: {nav_error}')
                try:
                    # Verificar si estamos en el sitio correcto
                    current_url = self.page.url
                    if 'portalsalud' in current_url or 'coosalud' in current_url:
                        self.logger.info('Playwright', f'✅ Página cargada parcialmente en: {current_url}')
                    else:
                        # No está en el sitio - intentar de nuevo con wait_until='commit'
                        self.logger.warning('Playwright', 'URL incorrecta, reintentando...')
                        self.page.goto(
                            'https://portalsalud.coosalud.com/login',
                            wait_until='commit',
                            timeout=10000
                        )
                        time.sleep(3)
                except Exception as retry_error:
                    self.logger.error('Playwright', f'Error en reintento: {retry_error}')
            
            # Esperar a que la página realmente se renderice - buscar campos de login
            self.logger.debug('Playwright', 'Esperando elementos visibles de login...')
            try:
                # Esperar a que aparezca algún elemento clave del login
                # Intentar varios selectores posibles
                self.page.wait_for_selector('input[type="text"], input[type="email"], input#email', 
                                           state='visible', 
                                           timeout=30000)
                self.logger.success('Playwright', '✅ Elementos de login visibles')
            except Exception as e:
                self.logger.warning('Playwright', f'⚠️ Timeout esperando elementos de login, continuando: {e}')
                # Esperar un poco más por si acaso
                time.sleep(3)
            
            time.sleep(1)
            
            return True
            
        except Exception as e:
            self.logger.error('Playwright', 'Error al iniciar navegador', e)
            return False
    
    def _create_new_context(self) -> BrowserContext:
        """Crea un nuevo contexto de navegación"""
        return self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
    
    def _setup_event_listeners(self):
        """Configura listeners para eventos importantes"""
        # Detectar cierre inesperado de página
        self.page.on('close', lambda: self.logger.warning('Playwright', '⚠️ Página cerrada inesperadamente'))
        
        # Detectar errores de consola críticos
        self.page.on('pageerror', lambda exc: self.logger.debug('Playwright', f'Error en página: {exc}'))
    
    def guardar_sesion(self):
        """Guarda el estado actual de la sesión"""
        try:
            if self.context:
                self.context.storage_state(path=str(self.session_file))
                self.logger.debug('Playwright', f'Sesión guardada en {self.session_file}')
        except Exception as e:
            self.logger.error('Playwright', 'Error guardando sesión', e)
    
    def sesion_valida(self) -> bool:
        """
        Verifica si la sesión actual sigue siendo válida.
        
        Returns:
            True si la sesión es válida
        """
        try:
            if not self.page:
                return False
            
            # Verificar que la página responda
            url = self.page.url
            
            # Si estamos en página de login, sesión no válida
            if 'login' in url.lower() or url == 'about:blank':
                return False
            
            # Buscar indicador de sesión activa (ajusta según tu sitio)
            # Por ejemplo, un elemento que solo aparece cuando estás logueado
            home_indicator = self.page.locator("//div[contains(.,'Hola,')]")
            if home_indicator.count() > 0:
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug('Playwright', f'Error verificando sesión: {e}')
            return False
    
    def navegar_a(self, url: str, wait_until: str = 'domcontentloaded') -> bool:
        """
        Navega a una URL.
        
        Args:
            url: URL destino
            wait_until: Cuándo considerar carga completa
        
        Returns:
            True si navegó exitosamente
        """
        try:
            self.logger.debug('Playwright', f'Navegando a: {url}')
            self.page.goto(url, wait_until=wait_until, timeout=60000)
            self.logger.success('Playwright', f'Navegación exitosa a {url}')
            return True
        except Exception as e:
            self.logger.error('Playwright', f'Error navegando a {url}', e)
            return False
    
    def take_screenshot(self, nombre: str = None, full_page: bool = False) -> str:
        """
        Toma una captura de pantalla.
        
        Args:
            nombre: Nombre del archivo (sin extensión)
            full_page: Si capturar página completa
        
        Returns:
            Ruta del archivo guardado
        """
        try:
            if not nombre:
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                nombre = f"screenshot_{timestamp}"
            
            filepath = self.screenshots_dir / f"{nombre}.png"
            self.page.screenshot(path=str(filepath), full_page=full_page)
            self.logger.debug('Playwright', f'Screenshot guardado: {filepath}')
            return str(filepath)
            
        except Exception as e:
            self.logger.error('Playwright', 'Error tomando screenshot', e)
            return ""
    
    def cerrar_navegador(self):
        """Cierra el navegador y limpia recursos"""
        try:
            self.logger.info('Playwright', 'Cerrando navegador...')
            
            if self.page:
                try:
                    self.page.close()
                except:
                    pass
                self.page = None
            
            if self.context:
                try:
                    self.context.close()
                except:
                    pass
                self.context = None
            
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass
                self.browser = None
            
            if self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
                self.playwright = None
            
            self.logger.success('Playwright', 'Navegador cerrado correctamente')
            
        except Exception as e:
            self.logger.error('Playwright', 'Error cerrando navegador', e)

    def cerrar(self):
        """Alias de cerrar_navegador() para compatibilidad"""
        self.cerrar_navegador()
    
    def esta_activo(self) -> bool:
        """
        Verifica si el navegador está activo.
        
        Returns:
            True si el navegador está corriendo
        """
        try:
            if not self.page:
                return False
            
            # Intenta obtener la URL (falla si está cerrado)
            _ = self.page.url
            return True
        except:
            return False
    
    def _find_system_chrome(self) -> Optional[str]:
        """
        Encuentra la instalación de Chrome del sistema.
        
        Returns:
            Ruta al ejecutable de Chrome si se encuentra, None sino
        """
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                self.logger.debug('Playwright', f'Chrome encontrado en: {path}')
                return path
        
        self.logger.warning('Playwright', 'Chrome del sistema no encontrado en rutas comunes')
        return None
    
    def _configure_playwright_browsers(self) -> Optional[str]:
        """
        Configura el navegador Playwright para ejecución desde .exe empaquetado.
        
        Returns:
            Ruta al ejecutable del navegador si se encuentra, None sino
        """
        # Comprobar si estamos ejecutando desde .exe empaquetado
        if not getattr(sys, 'frozen', False):
            return None
        
        try:
            # Buscar navegadores en el directorio de recursos empaquetados
            base_path = Path(sys._MEIPASS)
            
            # Buscar navegadores de Playwright empaquetados
            playwright_browsers_dir = base_path / 'playwright' / 'browsers'
            
            if playwright_browsers_dir.exists():
                # Buscar Chromium
                for chromium_dir in playwright_browsers_dir.glob('chromium-*'):
                    if chromium_dir.is_dir():
                        chrome_exe = chromium_dir / 'chrome-win' / 'chrome.exe'
                        if chrome_exe.exists():
                            self.logger.info('Playwright', f'✅ Navegador Playwright empaquetado encontrado: {chrome_exe}')
                            return str(chrome_exe)
            
            # Si no se encuentra navegador empaquetado, usar Chrome del sistema
            self.logger.warning('Playwright', '⚠️ Navegador Playwright empaquetado no encontrado, usando Chrome del sistema')
            return self._find_system_chrome()
            
        except Exception as e:
            self.logger.error('Playwright', f'Error configurando navegadores: {e}')
            return self._find_system_chrome()
