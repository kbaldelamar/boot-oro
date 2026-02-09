"""
Sistema de logging avanzado con triple salida:
- Consola (print)
- UI (callback)
- Archivo (solo warnings y errores)
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable


class AdvancedLogger:
    """Logger unificado para consola, UI y archivo"""
    
    NIVELES = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'SUCCESS': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥'
    }
    
    def __init__(self, ui_callback: Optional[Callable] = None, log_dir: str = "logs"):
        """
        Inicializa el logger.
        
        Args:
            ui_callback: Función para actualizar UI (recibe string)
            log_dir: Directorio para archivos de log
        """
        self.ui_callback = ui_callback
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Archivo del día actual
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.log_file = self.log_dir / f"errors_{self.current_date}.txt"
    
    def _format_message(self, nivel: str, modulo: str, mensaje: str) -> str:
        """Formatea el mensaje de log"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        emoji = self.NIVELES.get(nivel, '📝')
        return f"[{timestamp}] [{emoji} {nivel}] [{modulo}] {mensaje}"
    
    def _check_date_rollover(self):
        """Verifica si cambió el día y crea nuevo archivo"""
        current = datetime.now().strftime('%Y-%m-%d')
        if current != self.current_date:
            self.current_date = current
            self.log_file = self.log_dir / f"errors_{self.current_date}.txt"
    
    def _write_to_file(self, mensaje: str):
        """Escribe al archivo de log"""
        try:
            self._check_date_rollover()
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(mensaje + '\n')
        except Exception as e:
            print(f"Error escribiendo al log: {e}")
    
    def log(self, nivel: str, modulo: str, mensaje: str):
        """
        Registra un mensaje en todos los canales apropiados.
        
        Args:
            nivel: DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
            modulo: Nombre del módulo (Worker, Playwright, API, etc)
            mensaje: Mensaje a registrar
        """
        formatted = self._format_message(nivel, modulo, mensaje)
        
        # 1. SIEMPRE a consola
        print(formatted)
        
        # 2. A UI si hay callback
        if self.ui_callback:
            try:
                self.ui_callback(formatted)
            except Exception as e:
                print(f"Error actualizando UI: {e}")
        
        # 3. A archivo solo WARNING, ERROR, CRITICAL
        if nivel in ['WARNING', 'ERROR', 'CRITICAL']:
            self._write_to_file(formatted)
    
    # Métodos de conveniencia
    def debug(self, modulo: str, mensaje: str):
        """Log de debugging"""
        self.log('DEBUG', modulo, mensaje)
    
    def info(self, modulo: str, mensaje: str):
        """Log informativo"""
        self.log('INFO', modulo, mensaje)
    
    def success(self, modulo: str, mensaje: str):
        """Log de éxito"""
        self.log('SUCCESS', modulo, mensaje)
    
    def warning(self, modulo: str, mensaje: str):
        """Log de advertencia"""
        self.log('WARNING', modulo, mensaje)
    
    def error(self, modulo: str, mensaje: str, exception: Optional[Exception] = None):
        """Log de error"""
        if exception:
            mensaje = f"{mensaje}\n  Exception: {type(exception).__name__}: {str(exception)}"
        self.log('ERROR', modulo, mensaje)
    
    def critical(self, modulo: str, mensaje: str):
        """Log crítico"""
        self.log('CRITICAL', modulo, mensaje)
    
    def save_screenshot_info(self, screenshot_path: str, orden_id: str, error: str):
        """Registra información de screenshot en archivo"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        mensaje = f"Screenshot guardado: {screenshot_path}\n  Orden: {orden_id}\n  Error: {error}"
        formatted = f"[{timestamp}] [📸 SCREENSHOT] {mensaje}"
        self._write_to_file(formatted)
