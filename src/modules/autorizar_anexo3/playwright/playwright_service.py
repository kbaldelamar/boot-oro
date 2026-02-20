"""
Servicio principal de Playwright
Manejo de navegador, contexto y sesión persistente
"""
import os
import time
import sys
from pathlib import Path
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
        Cuando se ejecuta desde .exe, usa Google Chrome del sistema (channel='chrome').
        Si Chrome no está disponible, intenta con Microsoft Edge (channel='msedge').
        
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
            
            # 2. Lanzar navegador
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
            
            # Cadena de fallback: Chromium empaquetado → Chromium instalado → Chrome → Edge
            navegador_lanzado = False
            
            # 1. Si estamos en .exe, buscar Chromium empaquetado en sys._MEIPASS
            if getattr(sys, 'frozen', False):
                bundled_path = self._find_bundled_chromium()
                if bundled_path:
                    self.logger.info('Playwright', f'📦 Usando Chromium empaquetado: {bundled_path}')
                    launch_options['executable_path'] = bundled_path
                    try:
                        self.browser = self.playwright.chromium.launch(**launch_options)
                        self.logger.success('Playwright', '✅ Chromium empaquetado lanzado exitosamente')
                        navegador_lanzado = True
                    except Exception as bundled_error:
                        self.logger.warning('Playwright', f'⚠️ Chromium empaquetado falló: {bundled_error}')
                        launch_options.pop('executable_path', None)
            
            # 2. Intentar Chromium de Playwright instalado en el sistema
            if not navegador_lanzado:
                self.logger.info('Playwright', 'Intentando lanzar Chromium de Playwright...')
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.logger.success('Playwright', '✅ Chromium de Playwright lanzado exitosamente')
                    navegador_lanzado = True
                except Exception as chromium_error:
                    self.logger.warning('Playwright', f'⚠️ Chromium no disponible: {chromium_error}')
            
            # 3. Fallback a Google Chrome del sistema
            if not navegador_lanzado:
                self.logger.info('Playwright', '🔄 Intentando con Google Chrome del sistema...')
                launch_options['channel'] = 'chrome'
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.logger.success('Playwright', '✅ Google Chrome lanzado exitosamente')
                    navegador_lanzado = True
                except Exception as chrome_error:
                    self.logger.warning('Playwright', f'⚠️ Google Chrome no disponible: {chrome_error}')
            
            # 4. Fallback a Microsoft Edge
            if not navegador_lanzado:
                self.logger.info('Playwright', '🔄 Intentando con Microsoft Edge como fallback...')
                launch_options['channel'] = 'msedge'
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.logger.success('Playwright', '✅ Microsoft Edge lanzado exitosamente')
                    navegador_lanzado = True
                except Exception as edge_error:
                    self.logger.error('Playwright', f'❌ Edge también falló: {edge_error}')
            
            if not navegador_lanzado:
                self.logger.error('Playwright', '❌ No se encontró ningún navegador disponible')
                self.cerrar()
                return False
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error('Playwright', f'Error al iniciar navegador: {error_msg}')
            self.cerrar()
            return False
        
        try:
            # 3. Crear contexto con user agent real
            # viewport=None permite que --start-maximized funcione correctamente
            # y la página se adapte al tamaño real de la ventana del navegador
            self.context = self.browser.new_context(
                viewport=None,
                no_viewport=True,
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
            viewport=None,
            no_viewport=True
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
        """Cierra el navegador y limpia recursos, matando procesos zombies si es necesario"""
        try:
            self.logger.info('Playwright', 'Cerrando navegador...')
            cierre_exitoso = True
            
            # 1. Cerrar página
            if self.page:
                try:
                    self.page.close()
                    self.logger.debug('Playwright', '✓ Página cerrada')
                except Exception as e:
                    self.logger.warning('Playwright', f'⚠️ Error cerrando página: {e}')
                    cierre_exitoso = False
                finally:
                    self.page = None
            
            # 2. Cerrar contexto
            if self.context:
                try:
                    self.context.close()
                    self.logger.debug('Playwright', '✓ Contexto cerrado')
                except Exception as e:
                    self.logger.warning('Playwright', f'⚠️ Error cerrando contexto: {e}')
                    cierre_exitoso = False
                finally:
                    self.context = None
            
            # 3. Cerrar navegador
            if self.browser:
                try:
                    self.browser.close()
                    self.logger.debug('Playwright', '✓ Browser cerrado')
                except Exception as e:
                    self.logger.warning('Playwright', f'⚠️ Error cerrando browser: {e}')
                    cierre_exitoso = False
                finally:
                    self.browser = None
            
            # 4. Detener Playwright
            if self.playwright:
                try:
                    self.playwright.stop()
                    self.logger.debug('Playwright', '✓ Playwright detenido')
                except Exception as e:
                    self.logger.warning('Playwright', f'⚠️ Error deteniendo Playwright: {e}')
                    cierre_exitoso = False
                finally:
                    self.playwright = None
            
            # 5. Si hubo errores, hacer limpieza forzada de procesos
            if not cierre_exitoso:
                self.logger.warning('Playwright', '🧹 Cierre normal falló, ejecutando limpieza forzada...')
                time.sleep(1)  # Esperar 1 segundo antes de matar procesos
                self._kill_chromium_processes()
            
            self.logger.success('Playwright', 'Navegador cerrado correctamente')
            
        except Exception as e:
            self.logger.error('Playwright', 'Error general cerrando navegador', e)
            # Intentar limpieza forzada como último recurso
            try:
                time.sleep(1)
                self._kill_chromium_processes()
            except:
                pass

    def cerrar(self):
        """Alias de cerrar_navegador() para compatibilidad"""
        self.cerrar_navegador()
    
    def _kill_chromium_processes(self):
        """Mata procesos Chromium/Chrome huérfanos de forma forzada"""
        try:
            import psutil
            killed = 0
            process_names = ['chromium.exe', 'chrome.exe', 'msedge.exe']
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                    
                    # Verificar si es un proceso de navegador
                    is_browser = any(name.lower() in proc_name for name in process_names)
                    
                    # También verificar si fue lanzado por Playwright (contiene '--remote-debugging-port')
                    is_playwright = False
                    if proc.info.get('cmdline'):
                        cmdline_str = ' '.join(proc.info['cmdline'])
                        if '--remote-debugging-port' in cmdline_str or '--test-type' in cmdline_str:
                            is_playwright = True
                    
                    if is_browser and is_playwright:
                        proc.kill()
                        killed += 1
                        self.logger.debug('Playwright', f'🔪 Proceso eliminado: {proc_name} (PID: {proc.info["pid"]})')
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            if killed > 0:
                self.logger.warning('Playwright', f'🧹 Limpiados {killed} procesos Chromium huérfanos')
            else:
                self.logger.debug('Playwright', 'No se encontraron procesos huérfanos para limpiar')
                
        except ImportError:
            self.logger.warning('Playwright', '⚠️ psutil no disponible, no se pueden matar procesos huérfanos')
        except Exception as e:
            self.logger.error('Playwright', f'Error matando procesos: {e}')
    
    def __del__(self):
        """Destructor: garantiza limpieza de recursos al destruir el objeto"""
        try:
            if self.browser or self.playwright:
                self.cerrar_navegador()
        except:
            pass
    
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
    
    def _find_bundled_chromium(self) -> Optional[str]:
        """
        Busca Chromium empaquetado dentro del .exe (sys._MEIPASS).
        
        Returns:
            Ruta al ejecutable chrome.exe empaquetado, o None si no se encuentra
        """
        try:
            base_path = Path(sys._MEIPASS)
            browsers_dir = base_path / 'playwright' / 'browsers'
            
            if not browsers_dir.exists():
                self.logger.debug('Playwright', f'Directorio de browsers no existe: {browsers_dir}')
                return None
            
            # Buscar la versión más reciente de Chromium empaquetado
            chromium_dirs = sorted(
                [d for d in browsers_dir.iterdir() if d.is_dir() and d.name.startswith('chromium-')],
                key=lambda d: d.name,
                reverse=True  # Más reciente primero
            )
            
            for chromium_dir in chromium_dirs:
                chrome_exe = chromium_dir / 'chrome-win' / 'chrome.exe'
                if chrome_exe.exists():
                    self.logger.info('Playwright', f'📦 Chromium empaquetado encontrado: {chrome_exe}')
                    return str(chrome_exe)
            
            self.logger.warning('Playwright', 'No se encontró chrome.exe en browsers empaquetados')
            return None
            
        except Exception as e:
            self.logger.error('Playwright', f'Error buscando Chromium empaquetado: {e}')
            return None

    def _find_system_chrome(self) -> Optional[str]:
        """
        Encuentra la instalación de Chrome del sistema.
        NOTA: Método conservado como utilidad. El método iniciar_navegador()
        ahora usa channel='chrome' que es más robusto.
        
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
