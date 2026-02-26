"""
Módulo de Login con Playwright - Módulo Finalizar Casos
Copia independiente para no depender de autorizar_anexo3
"""
import time
from playwright.sync_api import Page
from twocaptcha import TwoCaptcha
from utils.logger import AdvancedLogger
from config.config import Config
from modules.finalizar_casos.playwright.helpers_playwright_fc import PlaywrightHelperFC


class LoginPlaywrightFC:
    """Servicio de login con manejo de CAPTCHA (Finalizar Casos)"""
    
    def __init__(self, page: Page, logger: AdvancedLogger):
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelperFC(page)
        self.config = Config()
        
        # Credenciales desde .env
        self.usuario = self.config.get('LOGIN_EMAIL')
        self.password = self.config.get('LOGIN_PASSWORD')
        
        # TwoCaptcha desde .env
        self.captcha_api_key = self.config.get('TWOCAPTCHA_API_KEY', '857a4d41a543d0168a59504919ad5807')
        self.captcha_site_key = self.config.get('TWOCAPTCHA_SITE_KEY', '6LdlqfwhAAAAANGjtq9te3mKQZwqgoey8tOZ44ua')
    
    def realizar_login_completo(self) -> bool:
        """
        Ejecuta el proceso completo de login.
        Verifica primero si ya hay sesión activa.
        
        Returns:
            True si login exitoso o ya está logueado
        """
        try:
            self.logger.info('LoginFC', 'Verificando estado de sesión...')
            
            if self.verificar_ya_logueado():
                self.logger.success('LoginFC', '✅ Sesión activa detectada, saltando login')
                return True
            
            self.logger.info('LoginFC', 'No hay sesión activa, iniciando login...')
            
            if not self.ingresar_credenciales():
                return False
            
            if not self.resolver_captcha():
                return False
            
            if not self.click_boton_login():
                return False
            
            if not self.verificar_login_exitoso():
                return False
            
            self.logger.success('LoginFC', '✅ Login completado exitosamente')
            return True
            
        except Exception as e:
            self.logger.error('LoginFC', 'Error en proceso de login', e)
            return False
    
    def verificar_ya_logueado(self, timeout: int = 5000) -> bool:
        try:
            indicadores_sesion = [
                "//div[@role='menuitem']//span[contains(text(),'Servicios de salud')]",
                "//button[contains(.,'Cerrar sesión')]",
                "//span[contains(text(),'Hola,')]",
                "//div[contains(@class,'user-menu')]",
                "//a[contains(@href,'logout')]"
            ]
            
            for indicador in indicadores_sesion:
                if self.helper.wait_for_element(indicador, timeout=timeout):
                    self.logger.debug('LoginFC', f'Sesión activa detectada con: {indicador}')
                    return True
            
            current_url = self.page.url
            if 'login' not in current_url.lower() and 'signin' not in current_url.lower():
                time.sleep(2)
                for indicador in indicadores_sesion[:3]:
                    if self.helper.wait_for_element(indicador, timeout=3000):
                        return True
            
            return False
        except Exception:
            return False
    
    def ingresar_credenciales(self) -> bool:
        try:
            self.logger.debug('LoginFC', 'Ingresando credenciales...')
            
            usuario_xpath = "//input[contains(@id,'email')]"
            if not self.helper.fill_text(usuario_xpath, self.usuario):
                self.logger.error('LoginFC', 'No se pudo ingresar usuario')
                return False
            
            self.logger.debug('LoginFC', f'Usuario ingresado: {self.usuario}')
            
            password_xpath = "//input[contains(@id,'password')]"
            if not self.helper.fill_text(password_xpath, self.password):
                self.logger.error('LoginFC', 'No se pudo ingresar contraseña')
                return False
            
            self.logger.debug('LoginFC', 'Contraseña ingresada')
            return True
            
        except Exception as e:
            self.logger.error('LoginFC', 'Error ingresando credenciales', e)
            return False
    
    def resolver_captcha(self) -> bool:
        try:
            self.logger.info('LoginFC', '🔐 Resolviendo CAPTCHA...')
            
            current_url = self.page.url
            
            solver = TwoCaptcha(
                apiKey=self.captcha_api_key,
                defaultTimeout=180,
                recaptchaTimeout=180,
                pollingInterval=5
            )
            
            try:
                balance = solver.balance()
                if float(balance) < 0.5:
                    self.logger.warning('LoginFC', '⚠️ Balance bajo!')
            except Exception:
                pass
            
            response = solver.recaptcha(
                sitekey=self.captcha_site_key,
                url=current_url
            )
            
            captcha_code = response['code']
            self.logger.success('LoginFC', f'✅ CAPTCHA resuelto. Token: {captcha_code[:50]}...')
            
            if not self.inyectar_captcha(captcha_code):
                return False
            
            self.logger.success('LoginFC', 'CAPTCHA inyectado')
            time.sleep(2)
            return True
            
        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower():
                self.logger.error('LoginFC', '⏱️ Timeout en TwoCaptcha')
            elif 'balance' in error_msg.lower() or 'insufficient' in error_msg.lower():
                self.logger.error('LoginFC', '💰 Balance insuficiente')
            elif 'key' in error_msg.lower():
                self.logger.error('LoginFC', '🔑 API Key inválida')
            else:
                self.logger.error('LoginFC', f'Error CAPTCHA: {error_msg}')
            return False
    
    def inyectar_captcha(self, code: str) -> bool:
        try:
            script = f"""
                (function() {{
                    function retrieveCallback(obj, visited = new Set()) {{
                        if (typeof obj === 'function') return obj;
                        for (const key in obj) {{
                            if (!visited.has(obj[key])) {{
                                visited.add(obj[key]);
                                if (typeof obj[key] === 'object' || typeof obj[key] === 'function') {{
                                    const value = retrieveCallback(obj[key], visited);
                                    if (value) {{
                                        return value;
                                    }}
                                }}
                                visited.delete(obj[key]);
                            }}
                        }}
                    }}
                    const callback = retrieveCallback(window.___grecaptcha_cfg.clients[0]);
                    if (typeof callback === 'function') {{
                        callback('{code}');
                        return true;
                    }} else {{
                        throw new Error('Callback function not found.');
                    }}
                }})();
            """
            self.page.evaluate(script)
            return True
        except Exception as e:
            self.logger.error('LoginFC', 'Error inyectando CAPTCHA', e)
            return False
    
    def click_boton_login(self) -> bool:
        try:
            self.logger.debug('LoginFC', 'Buscando botón de login...')
            
            login_button_xpaths = [
                "//button[@class='ant-btn ant-btn-primary']",
                "//button[@type='submit']",
                "//button[contains(@class,'ant-btn-primary')]"
            ]
            
            for xpath in login_button_xpaths:
                if self.helper.click_element(xpath, timeout=5000):
                    self.logger.success('LoginFC', '✅ Click en botón login')
                    return True
            
            self.logger.warning('LoginFC', 'Intentando click forzado...')
            if self.helper.click_element(login_button_xpaths[0], force=True):
                return True
            
            self.logger.error('LoginFC', 'No se pudo hacer clic en botón login')
            return False
            
        except Exception as e:
            self.logger.error('LoginFC', 'Error en botón login', e)
            return False
    
    def verificar_login_exitoso(self, timeout: int = 30000) -> bool:
        try:
            self.logger.debug('LoginFC', 'Verificando login exitoso...')
            
            indicadores_exito = [
                "//div[@role='menuitem']//span[contains(text(),'Servicios de salud')]",
                "//button[contains(.,'Cerrar sesión')]",
                "//span[contains(text(),'Hola,')]"
            ]
            
            for indicador in indicadores_exito:
                if self.helper.wait_for_element(indicador, timeout=timeout):
                    self.logger.success('LoginFC', f'Login verificado con: {indicador}')
                    return True
            
            time.sleep(3)
            current_url = self.page.url
            if 'login' not in current_url.lower():
                self.logger.success('LoginFC', 'Login verificado por URL')
                return True
            
            self.logger.error('LoginFC', 'No se pudo verificar login')
            return False
            
        except Exception as e:
            self.logger.error('LoginFC', 'Error verificando login', e)
            return False
