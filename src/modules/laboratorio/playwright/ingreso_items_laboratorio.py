"""
Módulo para ingreso de múltiples items/procedimientos en Laboratorio
Reutiliza la lógica de IngresoItemsPlaywright pero permite múltiples CUPS
"""
import time
from typing import List, Optional
from playwright.sync_api import Page

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.logger import Logger
from modules.autorizar_anexo3.playwright.helpers_playwright import PlaywrightHelper


class IngresoItemsLaboratorio:
    """
    Maneja el ingreso de múltiples procedimientos (CUPS) para laboratorio.
    Usa los mismos XPaths que IngresoItemsPlaywright pero permite iterar múltiples CUPS.
    """
    
    # XPaths EXACTOS del sistema (mismo que IngresoItemsPlaywright)
    XPATH_INPUT_CUPS = "//h5/following-sibling::div/div/div/div/span/input"
    XPATH_OPCION_CUPS = "//div[@class='ant-select-item-option-content'][contains(.,'{}')]"
    XPATH_ACEPTAR = "//span[contains(.,'Aceptar')]"
    XPATH_AGREGAR_ITEM = "//button[contains(.,'Agregar') or contains(.,'agregar')]"
    
    def __init__(self, page, logger: Optional[Logger] = None):
        """
        Args:
            page: Página de Playwright
            logger: Logger para registrar eventos
        """
        self.page = page
        self.logger = logger or Logger()
        self.helper = PlaywrightHelper(page) if page else None
    
    def _log(self, mensaje: str, level: str = "info"):
        """Registra un mensaje en el log"""
        modulo = "IngresoItemsLaboratorio"
        if level == "error":
            self.logger.error(modulo, mensaje)
        else:
            self.logger.info(modulo, mensaje)
    
    def ingresar_procedimientos(self, cups_list: List[str], page: Page) -> bool:
        """
        Ingresa múltiples procedimientos (CUPS) en el formulario.
        Selecciona cada CUPS en el dropdown y al final hace clic en Aceptar.
        
        Args:
            cups_list: Lista de códigos CUPS a ingresar
            page: Página de Playwright donde realizar la operación
            
        Returns:
            True si todos los CUPS fueron ingresados correctamente
        """
        self.page = page
        self.helper = PlaywrightHelper(page)
        
        if not cups_list:
            self._log("Lista de CUPS vacía", level="error")
            return False
        
        self._log(f"Ingresando {len(cups_list)} procedimiento(s)...")
        cups_ingresados = 0
        
        try:
            # Espera para estabilizar la página
            time.sleep(2)
            
            # Procesar TODOS los CUPS de la lista
            for idx, codigo_cups in enumerate(cups_list, start=1):
                self._log(f"=== PROCESANDO CUPS {idx}/{len(cups_list)}: {codigo_cups} ===")
                
                if not self._ingresar_un_cups(codigo_cups, idx):
                    self._log(f"⚠️ Error ingresando CUPS {codigo_cups}, continuando con el siguiente...", level="warning")
                    continue
                
                cups_ingresados += 1
                
                # Si NO es el último CUPS, esperar un momento antes del siguiente
                if idx < len(cups_list):
                    self._log(f"Preparando para siguiente CUPS...")
                    time.sleep(1)
            
            # Al final, hacer clic en Aceptar
            self._log("=== FINALIZANDO - Haciendo clic en Aceptar ===")
            time.sleep(2)
            clic_aceptar = self.page.wait_for_selector(self.XPATH_ACEPTAR, timeout=15000)
            clic_aceptar.click()
            self._log("✓ Clicked Aceptar - Proceso finalizado")
            
            self._log(f"✅ {cups_ingresados}/{len(cups_list)} CUPS ingresados correctamente")
            return cups_ingresados > 0
            
        except Exception as e:
            self._log(f"Error ingresando procedimientos: {e}", level="error")
            return False
    
    def _ingresar_un_cups(self, codigo_cups: str, numero: int) -> bool:
        """
        Ingresa un código CUPS individual en el formulario.
        
        Args:
            codigo_cups: Código CUPS a ingresar
            numero: Número de orden del CUPS (para logs)
            
        Returns:
            True si el CUPS fue ingresado correctamente
        """
        try:
            # Paso 1: Buscar campo CUPS (XPATH del sistema)
            self._log(f"[CUPS {numero}] Buscando campo de entrada...")
            input_cups = self.page.wait_for_selector(self.XPATH_INPUT_CUPS, timeout=20000)
            self._log(f"[CUPS {numero}] ✓ Campo encontrado")
            
            # Paso 2: Limpiar y hacer clic
            input_cups.fill("")
            input_cups.click()
            self._log(f"[CUPS {numero}] ✓ Clic en campo")
            
            # Paso 3: Ingresar código
            self.helper.ingresar_texto(input_cups, str(codigo_cups))
            self._log(f"[CUPS {numero}] ✓ Código ingresado: {codigo_cups}")
            
            # Espera para que aparezcan las opciones
            time.sleep(3)
            
            # Paso 4: Buscar opción en dropdown
            dynamic_xpath = self.XPATH_OPCION_CUPS.format(codigo_cups)
            self._log(f"[CUPS {numero}] Buscando en dropdown: {codigo_cups}")
            
            try:
                clic_opcion = self.page.wait_for_selector(dynamic_xpath, timeout=15000)
                self._log(f"[CUPS {numero}] ✓ Opción encontrada")
            except Exception as timeout_error:
                self._log(f"[CUPS {numero}] ⚠️ Timeout, reintentando con scroll...")
                self.page.evaluate("window.scrollTo(0, 0);")
                time.sleep(1)
                clic_opcion = self.page.wait_for_selector(dynamic_xpath, timeout=25000)
                self._log(f"[CUPS {numero}] ✓ Opción encontrada en segundo intento")
            
            # Paso 5: Hacer clic en la opción
            time.sleep(1)
            clic_opcion.click()
            self._log(f"[CUPS {numero}] ✓ CUPS {codigo_cups} seleccionado correctamente")
            
            return True
            
        except Exception as e:
            self._log(f"[CUPS {numero}] ❌ Error: {e}", level="error")
            return False
