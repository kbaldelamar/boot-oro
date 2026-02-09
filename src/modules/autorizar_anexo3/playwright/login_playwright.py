"""
Módulo de Login con Playwright
Incluye manejo de CAPTCHA con TwoCaptcha
"""
import time
from playwright.sync_api import Page
from twocaptcha import TwoCaptcha
from utils.logger import AdvancedLogger
from config.config import Config
from modules.autorizar_anexo3.playwright.helpers_playwright import PlaywrightHelper


class LoginPlaywright:
    """Servicio de login con manejo de CAPTCHA"""
    
    def __init__(self, page: Page, logger: AdvancedLogger):
        """
        Args:
            page: Página de Playwright
            logger: Logger
        """
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelper(page)
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
            self.logger.info('Login', 'Verificando estado de sesión...')
            
            # 0. Verificar si ya estamos logueados
            if self.verificar_ya_logueado():
                self.logger.success('Login', '✅ Sesión activa detectada, saltando login')
                return True
            
            self.logger.info('Login', 'No hay sesión activa, iniciando proceso de login...')
            
            # 1. Ingresar credenciales
            if not self.ingresar_credenciales():
                return False
            
            # 2. Resolver CAPTCHA
            if not self.resolver_captcha():
                return False
            
            # 3. Click en botón login
            if not self.click_boton_login():
                return False
            
            # 4. Verificar login exitoso
            if not self.verificar_login_exitoso():
                return False
            
            self.logger.success('Login', '✅ Login completado exitosamente')
            return True
            
        except Exception as e:
            self.logger.error('Login', 'Error en proceso de login', e)
            return False
    
    def verificar_ya_logueado(self, timeout: int = 5000) -> bool:
        """
        Verifica si ya hay una sesión activa (usuario ya logueado).
        
        Args:
            timeout: Tiempo de espera en milisegundos
            
        Returns:
            True si ya está logueado
        """
        try:
            # Buscar indicadores de sesión activa
            indicadores_sesion = [
                "//div[@role='menuitem']//span[contains(text(),'Servicios de salud')]",
                "//button[contains(.,'Cerrar sesión')]",
                "//span[contains(text(),'Hola,')]",
                "//div[contains(@class,'user-menu')]",
                "//a[contains(@href,'logout')]"
            ]
            
            for indicador in indicadores_sesion:
                if self.helper.wait_for_element(indicador, timeout=timeout):
                    self.logger.debug('Login', f'Sesión activa detectada con: {indicador}')
                    return True
            
            # Verificar si NO estamos en página de login
            current_url = self.page.url
            if 'login' not in current_url.lower() and 'signin' not in current_url.lower():
                # Dar tiempo adicional para cargar
                time.sleep(2)
                
                # Verificar de nuevo los indicadores con más tiempo
                for indicador in indicadores_sesion[:3]:  # Solo los 3 primeros
                    if self.helper.wait_for_element(indicador, timeout=3000):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.debug('Login', f'No se pudo verificar sesión: {e}')
            return False
    
    def ingresar_credenciales(self) -> bool:
        """Ingresa usuario y contraseña"""
        try:
            self.logger.debug('Login', 'Ingresando credenciales...')
            
            # Campo usuario
            usuario_xpath = "//input[contains(@id,'email')]"
            if not self.helper.fill_text(usuario_xpath, self.usuario):
                self.logger.error('Login', 'No se pudo ingresar usuario')
                return False
            
            self.logger.debug('Login', f'Usuario ingresado: {self.usuario}')
            
            # Campo contraseña
            password_xpath = "//input[contains(@id,'password')]"
            if not self.helper.fill_text(password_xpath, self.password):
                self.logger.error('Login', 'No se pudo ingresar contraseña')
                return False
            
            self.logger.debug('Login', 'Contraseña ingresada')
            
            return True
            
        except Exception as e:
            self.logger.error('Login', 'Error ingresando credenciales', e)
            return False
    
    def resolver_captcha(self) -> bool:
        """
        Resuelve el CAPTCHA usando TwoCaptcha.
        
        Returns:
            True si se resolvió exitosamente
        """
        try:
            self.logger.info('Login', '🔐 Resolviendo CAPTCHA con Captcha...')
            
            # 1. Obtener URL actual
            current_url = self.page.url
            self.logger.debug('Login', f'URL para CAPTCHA: {current_url}')
            self.logger.debug('Login', f'Site Key: {self.captcha_site_key}')
            
            # 2. Llamar a TwoCaptcha con configuración optimizada
            solver = TwoCaptcha(
                apiKey=self.captcha_api_key,
                defaultTimeout=180,  # Aumentar timeout a 3 minutos
                recaptchaTimeout=180,
                pollingInterval=5  # Verificar cada 5 segundos
            )
            
            # Verificar balance primero
            try:
                balance = solver.balance()
                self.logger.info('Login', f'💰 Balance TwoCaptcha: ${balance}')
                if float(balance) < 0.5:
                    self.logger.warning('Login', '⚠️ Balance bajo! Recarga en https://2captcha.com')
            except Exception as e:
                self.logger.warning('Login', f'No se pudo verificar balance: {e}')
            
            self.logger.info('Login', 'Esperando respuesta de Captcha...')
            response = solver.recaptcha(
                sitekey=self.captcha_site_key,
                url=current_url
            )
            
            captcha_code = response['code']
            self.logger.success('Login', f'✅ CAPTCHA resuelto. Token obtenido: {captcha_code[:50]}...')
            
            # 3. Inyectar respuesta del CAPTCHA
            if not self.inyectar_captcha(captcha_code):
                return False
            
            self.logger.success('Login', 'CAPTCHA inyectado exitosamente')
            time.sleep(2)  # Esperar procesamiento
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            
            # Mensajes específicos según el error
            if 'timeout' in error_msg.lower():
                self.logger.error('Login', '⏱️ Timeout esperando TwoCaptcha. Servicio muy ocupado.')
                self.logger.info('Login', '💡 Espera unos segundos y vuelve a intentar')
            elif 'balance' in error_msg.lower() or 'insufficient' in error_msg.lower():
                self.logger.error('Login', '💰 Balance insuficiente. Recarga en https://2captcha.com')
            elif 'key' in error_msg.lower():
                self.logger.error('Login', '🔑 API Key inválida. Verifica endpoint.env')
            else:
                self.logger.error('Login', f'Error resolviendo CAPTCHA: {error_msg}')
            self.logger.error('Login', 'Error resolviendo CAPTCHA', e)
            return False
    
    def inyectar_captcha(self, code: str) -> bool:
        """
        Inyecta el código del CAPTCHA usando JavaScript.
        
        Args:
            code: Código del CAPTCHA resuelto
        
        Returns:
            True si se inyectó exitosamente
        """
        try:
            self.logger.debug('Login', 'Inyectando código CAPTCHA...')
            
            # Script de inyección usando template literal
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
            
            # Ejecutar script
            result = self.page.evaluate(script)
            self.logger.debug('Login', f'Script ejecutado. Resultado: {result}')
            
            return True
            
        except Exception as e:
            self.logger.error('Login', 'Error inyectando CAPTCHA', e)
            return False
    
    def click_boton_login(self) -> bool:
        """
        Hace clic en el botón de login con múltiples estrategias.
        
        Returns:
            True si hizo clic exitosamente
        """
        try:
            self.logger.debug('Login', 'Buscando botón de login...')
            
            # Lista de posibles selectores (usando el XPath original que funciona)
            login_button_xpaths = [
                "//button[@class='ant-btn ant-btn-primary']",
                "//button[@type='submit']",
                "//button[contains(@class,'ant-btn-primary')]"
            ]
            
            for xpath in login_button_xpaths:
                self.logger.debug('Login', f'Probando selector: {xpath}')
                
                if self.helper.click_element(xpath, timeout=5000):
                    self.logger.success('Login', f'✅ Click en botón login exitoso')
                    return True
            
            # Si ninguno funcionó, intentar con force
            self.logger.warning('Login', 'Intentando click forzado...')
            if self.helper.click_element(login_button_xpaths[0], force=True):
                return True
            
            self.logger.error('Login', 'No se pudo hacer clic en botón de login')
            return False
            
        except Exception as e:
            self.logger.error('Login', 'Error haciendo clic en botón login', e)
            return False
    
    def verificar_login_exitoso(self, timeout: int = 30000) -> bool:
        """
        Verifica que el login fue exitoso.
        
        Args:
            timeout: Tiempo máximo de espera
        
        Returns:
            True si login exitoso
        """
        try:
            self.logger.debug('Login', 'Verificando login exitoso...')
            
            # Indicadores de login exitoso (usando XPaths originales)
            indicadores_exito = [
                "//div[@role='menuitem']//span[contains(text(),'Servicios de salud')]",
                "//button[contains(.,'Cerrar sesión')]",
                "//span[contains(text(),'Hola,')]"
            ]
            
            for indicador in indicadores_exito:
                if self.helper.wait_for_element(indicador, timeout=timeout):
                    self.logger.success('Login', f'Login verificado con indicador: {indicador}')
                    return True
            
            # Si llegamos aquí, verificar URL
            time.sleep(3)
            current_url = self.page.url
            if 'login' not in current_url.lower():
                self.logger.success('Login', 'Login verificado por URL')
                return True
            
            self.logger.error('Login', 'No se pudo verificar login exitoso')
            return False
            
        except Exception as e:
            self.logger.error('Login', 'Error verificando login', e)
            return False
