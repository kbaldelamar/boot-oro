"""
Servicio principal de Playwright - Módulo Finalizar Casos
Copia independiente para no depender de autorizar_anexo3
"""
import os
import time
import sys
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from utils.logger import AdvancedLogger
from utils.paths import get_data_path


class PlaywrightServiceFC:
    """Servicio para gestionar Playwright con sesión persistente (Finalizar Casos)"""
    
    def __init__(self, logger: Optional[AdvancedLogger] = None):
        self.logger = logger or AdvancedLogger()
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Archivos de sesión y screenshots
        self.session_dir = get_data_path("session_data")
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "session_state_fc.json"   # Archivo separado
        
        self.screenshots_dir = get_data_path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
    
    def iniciar_navegador(self, reutilizar_sesion: bool = True) -> bool:
        """
        Inicia el navegador Chromium con Playwright.
        Cadena de fallback: Chromium empaquetado → Chromium instalado → Chrome → Edge
        
        Returns:
            True si se inició correctamente
        """
        try:
            self.logger.info('PlaywrightFC', 'Iniciando Playwright...')
            
            # 1. Iniciar Playwright
            self.playwright = sync_playwright().start()
            self.logger.debug('PlaywrightFC', 'Playwright iniciado')
            
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
            
            navegador_lanzado = False
            
            # 1. Si estamos en .exe, buscar Chromium empaquetado
            if getattr(sys, 'frozen', False):
                bundled_path = self._find_bundled_chromium()
                if bundled_path:
                    self.logger.info('PlaywrightFC', f'📦 Usando Chromium empaquetado: {bundled_path}')
                    launch_options['executable_path'] = bundled_path
                    try:
                        self.browser = self.playwright.chromium.launch(**launch_options)
                        self.logger.success('PlaywrightFC', '✅ Chromium empaquetado lanzado')
                        navegador_lanzado = True
                    except Exception as bundled_error:
                        self.logger.warning('PlaywrightFC', f'⚠️ Chromium empaquetado falló: {bundled_error}')
                        launch_options.pop('executable_path', None)
            
            # 2. Intentar Chromium de Playwright instalado
            if not navegador_lanzado:
                self.logger.info('PlaywrightFC', 'Intentando lanzar Chromium de Playwright...')
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.logger.success('PlaywrightFC', '✅ Chromium lanzado')
                    navegador_lanzado = True
                except Exception as chromium_error:
                    self.logger.warning('PlaywrightFC', f'⚠️ Chromium no disponible: {chromium_error}')
            
            # 3. Fallback a Google Chrome
            if not navegador_lanzado:
                self.logger.info('PlaywrightFC', '🔄 Intentando con Google Chrome...')
                launch_options['channel'] = 'chrome'
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.logger.success('PlaywrightFC', '✅ Google Chrome lanzado')
                    navegador_lanzado = True
                except Exception as chrome_error:
                    self.logger.warning('PlaywrightFC', f'⚠️ Chrome no disponible: {chrome_error}')
            
            # 4. Fallback a Microsoft Edge
            if not navegador_lanzado:
                self.logger.info('PlaywrightFC', '🔄 Intentando con Microsoft Edge...')
                launch_options['channel'] = 'msedge'
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.logger.success('PlaywrightFC', '✅ Edge lanzado')
                    navegador_lanzado = True
                except Exception as edge_error:
                    self.logger.error('PlaywrightFC', f'❌ Edge también falló: {edge_error}')
            
            if not navegador_lanzado:
                self.logger.error('PlaywrightFC', '❌ No se encontró ningún navegador')
                self.cerrar()
                return False
            
        except Exception as e:
            self.logger.error('PlaywrightFC', f'Error al iniciar navegador: {e}')
            self.cerrar()
            return False
        
        try:
            # 3. Crear contexto
            self.context = self.browser.new_context(
                viewport=None,
                no_viewport=True,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True
            )
            
            # 4. Crear página
            self.page = self.context.new_page()
            self.page.set_default_timeout(60000)
            self.logger.success('PlaywrightFC', 'Página creada')
            
            # 5. Navegar a la URL de login
            self.logger.info('PlaywrightFC', 'Navegando a página inicial...')
            try:
                self.page.goto(
                    'https://portalsalud.coosalud.com/login', 
                    wait_until='domcontentloaded',
                    timeout=15000
                )
                self.logger.success('PlaywrightFC', 'Navegación completada')
            except Exception as nav_error:
                self.logger.warning('PlaywrightFC', f'Timeout en navegación, verificando: {nav_error}')
                try:
                    current_url = self.page.url
                    if 'portalsalud' in current_url or 'coosalud' in current_url:
                        self.logger.info('PlaywrightFC', f'✅ Página cargada en: {current_url}')
                    else:
                        self.logger.warning('PlaywrightFC', 'URL incorrecta, reintentando...')
                        self.page.goto(
                            'https://portalsalud.coosalud.com/login',
                            wait_until='commit',
                            timeout=10000
                        )
                        time.sleep(3)
                except Exception as retry_error:
                    self.logger.error('PlaywrightFC', f'Error en reintento: {retry_error}')
            
            # Esperar elementos de login
            self.logger.debug('PlaywrightFC', 'Esperando elementos de login...')
            try:
                self.page.wait_for_selector(
                    'input[type="text"], input[type="email"], input#email', 
                    state='visible', 
                    timeout=30000
                )
                self.logger.success('PlaywrightFC', '✅ Elementos de login visibles')
            except Exception as e:
                self.logger.warning('PlaywrightFC', f'⚠️ Timeout esperando login, continuando: {e}')
                time.sleep(3)
            
            time.sleep(1)
            return True
            
        except Exception as e:
            self.logger.error('PlaywrightFC', 'Error al iniciar navegador', e)
            return False
    
    def guardar_sesion(self):
        try:
            if self.context:
                self.context.storage_state(path=str(self.session_file))
                self.logger.debug('PlaywrightFC', f'Sesión guardada en {self.session_file}')
        except Exception as e:
            self.logger.error('PlaywrightFC', 'Error guardando sesión', e)
    
    def sesion_valida(self) -> bool:
        try:
            if not self.page:
                return False
            url = self.page.url
            if 'login' in url.lower() or url == 'about:blank':
                return False
            home_indicator = self.page.locator("//div[contains(.,'Hola,')]")
            if home_indicator.count() > 0:
                return True
            return False
        except Exception:
            return False
    
    def navegar_a(self, url: str, wait_until: str = 'domcontentloaded') -> bool:
        try:
            self.logger.debug('PlaywrightFC', f'Navegando a: {url}')
            self.page.goto(url, wait_until=wait_until, timeout=60000)
            self.logger.success('PlaywrightFC', f'Navegación exitosa a {url}')
            return True
        except Exception as e:
            self.logger.error('PlaywrightFC', f'Error navegando a {url}', e)
            return False
    
    def take_screenshot(self, nombre: str = None, full_page: bool = False) -> str:
        try:
            if not nombre:
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                nombre = f"screenshot_fc_{timestamp}"
            filepath = self.screenshots_dir / f"{nombre}.png"
            self.page.screenshot(path=str(filepath), full_page=full_page)
            return str(filepath)
        except Exception as e:
            self.logger.error('PlaywrightFC', 'Error tomando screenshot', e)
            return ""
    
    def cerrar_navegador(self):
        """Cierra el navegador y limpia recursos"""
        try:
            self.logger.info('PlaywrightFC', 'Cerrando navegador...')
            cierre_exitoso = True
            
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    cierre_exitoso = False
                finally:
                    self.page = None
            
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    cierre_exitoso = False
                finally:
                    self.context = None
            
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    cierre_exitoso = False
                finally:
                    self.browser = None
            
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    cierre_exitoso = False
                finally:
                    self.playwright = None
            
            if not cierre_exitoso:
                self.logger.warning('PlaywrightFC', '🧹 Cierre normal falló, limpieza forzada...')
                time.sleep(1)
                self._kill_chromium_processes()
            
            self.logger.success('PlaywrightFC', 'Navegador cerrado')
            
        except Exception as e:
            self.logger.error('PlaywrightFC', 'Error cerrando navegador', e)
            try:
                time.sleep(1)
                self._kill_chromium_processes()
            except:
                pass

    def cerrar(self):
        """Alias de cerrar_navegador()"""
        self.cerrar_navegador()
    
    def _kill_chromium_processes(self):
        """Mata procesos Chromium/Chrome lanzados por Playwright de forma forzada"""
        try:
            import psutil
            killed = 0
            process_names = ['chromium.exe', 'chrome.exe', 'msedge.exe']
            playwright_markers = [
                '--remote-debugging-pipe',
                '--remote-debugging-port',
                '--test-type',
                'ms-playwright',
            ]
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                    is_browser = any(name.lower() in proc_name for name in process_names)
                    if not is_browser:
                        continue
                    
                    is_playwright = False
                    exe_path = (proc.info.get('exe') or '').lower()
                    if 'ms-playwright' in exe_path:
                        is_playwright = True
                    
                    if not is_playwright and proc.info.get('cmdline'):
                        cmdline_str = ' '.join(proc.info['cmdline']).lower()
                        if any(marker in cmdline_str for marker in playwright_markers):
                            is_playwright = True
                    
                    if is_playwright:
                        proc.kill()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            if killed > 0:
                self.logger.warning('PlaywrightFC', f'🧹 Limpiados {killed} procesos Chromium')
        except ImportError:
            self.logger.warning('PlaywrightFC', '⚠️ psutil no disponible')
        except Exception as e:
            self.logger.error('PlaywrightFC', f'Error matando procesos: {e}')
    
    def esta_activo(self) -> bool:
        try:
            if not self.page:
                return False
            _ = self.page.url
            return True
        except:
            return False
    
    def _find_bundled_chromium(self) -> Optional[str]:
        try:
            base_path = Path(sys._MEIPASS)
            browsers_dir = base_path / 'playwright' / 'browsers'
            if not browsers_dir.exists():
                return None
            chromium_dirs = sorted(
                [d for d in browsers_dir.iterdir() if d.is_dir() and d.name.startswith('chromium-')],
                key=lambda d: d.name,
                reverse=True
            )
            for chromium_dir in chromium_dirs:
                chrome_exe = chromium_dir / 'chrome-win' / 'chrome.exe'
                if chrome_exe.exists():
                    return str(chrome_exe)
            return None
        except Exception:
            return None
    
    def __del__(self):
        try:
            if self.browser or self.playwright:
                self.cerrar_navegador()
        except:
            pass
