"""
Helpers y utilidades para Playwright
Equivalente a SeleniumHelper pero optimizado para Playwright
"""
import time
from typing import Optional
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeout


class PlaywrightHelper:
    """Clase de utilidades para operaciones comunes con Playwright"""
    
    def __init__(self, page: Page):
        """
        Args:
            page: Instancia de página de Playwright
        """
        self.page = page
    
    def scroll_to_element(self, locator: Locator):
        """
        Hace scroll hasta un elemento.
        
        Args:
            locator: Locator del elemento
        """
        try:
            locator.scroll_into_view_if_needed()
        except Exception as e:
            # Fallback: scroll usando JavaScript
            self.page.evaluate("arguments[0].scrollIntoView({block: 'center'})", locator.element_handle())
    
    def click_element(self, xpath: str, timeout: int = 30000, force: bool = False) -> bool:
        """
        Hace clic en un elemento con múltiples estrategias.
        
        Args:
            xpath: XPath del elemento
            timeout: Timeout en milisegundos
            force: Si hacer clic forzado (ignora checks de visibilidad)
        
        Returns:
            True si tuvo éxito, False si falló
        """
        try:
            locator = self.page.locator(xpath)
            
            # Esperar que sea visible y clickeable
            locator.wait_for(state='visible', timeout=timeout)
            
            # Scroll si es necesario
            self.scroll_to_element(locator)
            
            # Click
            locator.click(force=force, timeout=timeout)
            return True
            
        except PlaywrightTimeout:
            print(f"Timeout esperando elemento: {xpath}")
            return False
        except Exception as e:
            print(f"Error haciendo clic en {xpath}: {e}")
            return False
    
    def fill_text(self, xpath: str, texto: str, timeout: int = 30000, clear_first: bool = True) -> bool:
        """
        Ingresa texto en un campo.
        
        Args:
            xpath: XPath del campo
            texto: Texto a ingresar
            timeout: Timeout en milisegundos
            clear_first: Si limpiar el campo primero
        
        Returns:
            True si tuvo éxito, False si falló
        """
        try:
            locator = self.page.locator(xpath)
            
            # Esperar que sea visible
            locator.wait_for(state='visible', timeout=timeout)
            
            # Limpiar si se solicita
            if clear_first:
                locator.clear()
            
            # Ingresar texto
            locator.fill(texto)
            return True
            
        except Exception as e:
            print(f"Error ingresando texto en {xpath}: {e}")
            return False
    
    def fill_text_sequential(self, xpath: str, texto: str, delay: int = 50) -> bool:
        """
        Ingresa texto carácter por carácter (útil para campos ant-select).
        
        Args:
            xpath: XPath del campo
            texto: Texto a ingresar
            delay: Delay entre caracteres en milisegundos
        
        Returns:
            True si tuvo éxito
        """
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='visible')
            
            # Click en el campo
            locator.click()
            
            # Limpiar con Ctrl+A + Delete
            self.page.keyboard.press('Control+A')
            self.page.keyboard.press('Delete')
            
            # Ingresar carácter por carácter
            for char in texto:
                self.page.keyboard.type(char, delay=delay)
            
            return True
            
        except Exception as e:
            print(f"Error en ingreso secuencial: {e}")
            return False
    
    def wait_for_element(self, xpath: str, timeout: int = 30000, state: str = 'visible') -> bool:
        """
        Espera a que un elemento esté en cierto estado.
        
        Args:
            xpath: XPath del elemento
            timeout: Timeout en milisegundos
            state: Estado esperado (visible, attached, hidden, detached)
        
        Returns:
            True si apareció, False si timeout
        """
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state=state, timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False
    
    def get_text(self, xpath: str, timeout: int = 10000) -> Optional[str]:
        """
        Obtiene el texto de un elemento.
        
        Args:
            xpath: XPath del elemento
            timeout: Timeout en milisegundos
        
        Returns:
            Texto del elemento o None si no existe
        """
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='visible', timeout=timeout)
            return locator.text_content()
        except:
            return None
    
    def element_exists(self, xpath: str, timeout: int = 5000) -> bool:
        """
        Verifica si un elemento existe.
        
        Args:
            xpath: XPath del elemento
            timeout: Timeout en milisegundos
        
        Returns:
            True si existe, False si no
        """
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='attached', timeout=timeout)
            return locator.count() > 0
        except:
            return False
    
    def scroll_list_and_find(self, option_text: str, max_attempts: int = 30, scroll_increment: int = 100) -> Optional[Locator]:
        """
        Busca una opción en un virtual list con scroll (para Ant Design).
        
        Args:
            option_text: Texto de la opción a buscar
            max_attempts: Intentos máximos de scroll
            scroll_increment: Píxeles por scroll
        
        Returns:
            Locator de la opción si se encuentra, None si no
        """
        attempts = 0
        found_options = set()
        
        # XPath para opciones de Ant Design
        options_xpath = "//div[@class='ant-select-item-option-content']"
        
        while attempts < max_attempts:
            # Obtener opciones actuales
            options = self.page.locator(options_xpath).all()
            
            for option in options:
                try:
                    text = option.text_content()
                    if text and option_text in text:
                        # Encontrada!
                        return option
                    if text:
                        found_options.add(text)
                except:
                    continue
            
            # Scroll down en el dropdown
            try:
                # Buscar el contenedor del dropdown
                dropdown = self.page.locator("//div[contains(@class,'ant-select-dropdown')]").first
                if dropdown.count() > 0:
                    # Scroll usando evaluate
                    self.page.evaluate(f"""
                        const dropdown = document.querySelector('.ant-select-dropdown .rc-virtual-list-holder');
                        if (dropdown) {{
                            dropdown.scrollTop += {scroll_increment};
                        }}
                    """)
                    time.sleep(0.3)
            except:
                pass
            
            attempts += 1
        
        print(f"Opción '{option_text}' no encontrada después de {attempts} intentos")
        print(f"Opciones vistas: {list(found_options)[:10]}...")
        return None
    
    def execute_script(self, script: str, *args):
        """
        Ejecuta JavaScript en el navegador.
        
        Args:
            script: Script a ejecutar
            *args: Argumentos para el script
        
        Returns:
            Resultado del script
        """
        return self.page.evaluate(script, *args)
    
    def ingresar_texto(self, element, texto: str) -> bool:
        """
        Ingresa texto en un elemento (compatible con Selenium).
        Esta versión acepta un element handle directamente.
        
        Args:
            element: Elemento (ElementHandle o Locator) donde ingresar texto
            texto: Texto a ingresar
        
        Returns:
            True si tuvo éxito
        """
        try:
            # Si es un ElementHandle, usar fill directamente
            element.fill('')  # Limpiar primero
            element.fill(str(texto))
            return True
        except Exception as e:
            print(f"Error en ingresar_texto: {e}")
            # Fallback: intentar con type
            try:
                element.click()
                self.page.keyboard.press('Control+A')
                self.page.keyboard.press('Delete')
                element.type(str(texto))
                return True
            except Exception as e2:
                print(f"Error en fallback de ingresar_texto: {e2}")
                return False
    
    def ingresar_texto_secuencial(self, element, texto: str, delay: int = 50) -> bool:
        """
        Ingresa texto carácter por carácter (compatible con Selenium).
        Útil para campos ant-select y búsquedas dinámicas.
        
        Args:
            element: Elemento donde ingresar texto
            texto: Texto a ingresar
            delay: Delay entre caracteres en milisegundos
        
        Returns:
            True si tuvo éxito
        """
        try:
            # Click en el elemento
            element.click()
            
            # Limpiar con Ctrl+A + Delete
            self.page.keyboard.press('Control+A')
            self.page.keyboard.press('Delete')
            
            # Ingresar carácter por carácter
            for char in str(texto):
                self.page.keyboard.type(char, delay=delay)
            
            return True
            
        except Exception as e:
            print(f"Error en ingresar_texto_secuencial: {e}")
            # Fallback: usar JavaScript
            try:
                self.page.evaluate(
                    """([el, text]) => {
                        el.value = text;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    [element, str(texto)]
                )
                return True
            except Exception as js_error:
                print(f"Error en fallback JavaScript: {js_error}")
                return False
