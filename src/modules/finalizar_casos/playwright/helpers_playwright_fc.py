"""
Helpers y utilidades para Playwright - Módulo Finalizar Casos
Copia independiente para no depender de autorizar_anexo3
"""
import time
from typing import Optional
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeout


class PlaywrightHelperFC:
    """Clase de utilidades para operaciones comunes con Playwright (Finalizar Casos)"""
    
    def __init__(self, page: Page):
        self.page = page
    
    def scroll_to_element(self, locator: Locator):
        try:
            locator.scroll_into_view_if_needed()
        except Exception:
            self.page.evaluate("arguments[0].scrollIntoView({block: 'center'})", locator.element_handle())
    
    def click_element(self, xpath: str, timeout: int = 30000, force: bool = False) -> bool:
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='visible', timeout=timeout)
            self.scroll_to_element(locator)
            locator.click(force=force, timeout=timeout)
            return True
        except PlaywrightTimeout:
            print(f"Timeout esperando elemento: {xpath}")
            return False
        except Exception as e:
            print(f"Error haciendo clic en {xpath}: {e}")
            return False
    
    def fill_text(self, xpath: str, texto: str, timeout: int = 30000, clear_first: bool = True) -> bool:
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='visible', timeout=timeout)
            if clear_first:
                locator.clear()
            locator.fill(texto)
            return True
        except Exception as e:
            print(f"Error ingresando texto en {xpath}: {e}")
            return False
    
    def wait_for_element(self, xpath: str, timeout: int = 30000, state: str = 'visible') -> bool:
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state=state, timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False
    
    def get_text(self, xpath: str, timeout: int = 10000) -> Optional[str]:
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='visible', timeout=timeout)
            return locator.text_content()
        except:
            return None
    
    def element_exists(self, xpath: str, timeout: int = 5000) -> bool:
        try:
            locator = self.page.locator(xpath)
            locator.wait_for(state='attached', timeout=timeout)
            return locator.count() > 0
        except:
            return False
    
    def ingresar_texto(self, element, texto: str) -> bool:
        try:
            element.fill('')
            element.fill(str(texto))
            return True
        except Exception:
            try:
                element.click()
                self.page.keyboard.press('Control+A')
                self.page.keyboard.press('Delete')
                element.type(str(texto))
                return True
            except Exception:
                return False
    
    def ingresar_texto_secuencial(self, element, texto: str, delay: int = 50) -> bool:
        try:
            element.click()
            self.page.keyboard.press('Control+A')
            self.page.keyboard.press('Delete')
            for char in str(texto):
                self.page.keyboard.type(char, delay=delay)
            return True
        except Exception:
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
            except Exception:
                return False
    
    def scroll_list_and_find(self, option_text: str, max_attempts: int = 30, scroll_increment: int = 100) -> Optional[Locator]:
        attempts = 0
        found_options = set()
        options_xpath = "//div[@class='ant-select-item-option-content']"
        
        while attempts < max_attempts:
            options = self.page.locator(options_xpath).all()
            for option in options:
                try:
                    text = option.text_content()
                    if text and option_text in text:
                        return option
                    if text:
                        found_options.add(text)
                except:
                    continue
            
            try:
                dropdown = self.page.locator("//div[contains(@class,'ant-select-dropdown')]").first
                if dropdown.count() > 0:
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
        return None
    
    def execute_script(self, script: str, *args):
        return self.page.evaluate(script, *args)
