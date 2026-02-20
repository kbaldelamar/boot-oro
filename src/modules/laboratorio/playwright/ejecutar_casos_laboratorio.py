"""
Ejecutor de casos para Laboratorio
Extiende EjecutarCasosPlaywright con lógica específica de laboratorio
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.autorizar_anexo3.playwright.ejecutar_casos_playwright import EjecutarCasosPlaywright
from modules.laboratorio.playwright.ingreso_items_laboratorio import IngresoItemsLaboratorio
from config.config import Config
from utils.logger import Logger


class EjecutarCasosLaboratorio(EjecutarCasosPlaywright):
    """
    Ejecutor de casos para Laboratorio que hereda del ejecutor de Anexo 3.
    Reutiliza los XPaths y lógica base, pero modifica:
    - La fuente de datos
    - El ingreso de múltiples servicios (CUPS)
    - La búsqueda de PDF
    """
    
    def __init__(self, page, logger: Optional[Logger] = None, pause_callback=None):
        """
        Args:
            page: Página de Playwright
            logger: Logger para registrar eventos
            pause_callback: Función que retorna True si el worker está pausado
        """
        super().__init__(page, logger, pause_callback)
        self.config = Config()
        self.ingreso_laboratorio = IngresoItemsLaboratorio(page, logger)
        self.cups_list = []  # Lista de CUPS para laboratorio
    
    def _log(self, mensaje: str, level: str = "info"):
        """Registra un mensaje en el log"""
        modulo = "EjecutarCasosLaboratorio"
        if level == "error":
            self.logger.error(modulo, mensaje)
        elif level == "warning":
            self.logger.warning(modulo, mensaje)
        else:
            self.logger.info(modulo, mensaje)
    
    def ejecutar(self, paciente_data: Dict[str, Any]) -> bool:
        """
        Ejecuta el proceso completo para un paciente de laboratorio
        Convierte los datos y usa inicio_casos de la clase padre
        
        Args:
            paciente_data: Diccionario con datos del paciente incluyendo cups_list
            
        Returns:
            True si el proceso fue exitoso, False en caso contrario
            
        Raises:
            Exception: Propaga excepciones para clasificación de errores en el worker
        """
        self._log(f"Iniciando proceso para paciente: {paciente_data.get('nombre', 'N/A')}")
        
        # Verificar datos mínimos
        if not self._validar_datos_paciente(paciente_data):
            raise Exception("Datos de paciente inválidos o incompletos")
        
        # Guardar cups_list para uso en _ingresar_servicios
        self.cups_list = paciente_data.get('cups_list', [])
        self._log(f"📋 CUPS recibidos en ejecutor: {self.cups_list} (total: {len(self.cups_list)})")
        
        # Convertir diccionario a objeto con atributos (formato que espera inicio_casos)
        class DataObject:
            pass
        data = DataObject()
        
        # Mapear campos al formato esperado por inicio_casos
        data.tipoIdentificacion = paciente_data.get('tipo_identificacion', 'Cédula de Ciudadanía')
        data.identificacion = paciente_data.get('numero_identificacion', '')
        data.telefono = paciente_data.get('telefono', '')
        data.fechaFacturaEvento = paciente_data.get('fecha', '')
        data.diagnostico = paciente_data.get('diagnostico', '')
        data.idOrden = paciente_data.get('idOrdenProcedimiento', '') or paciente_data.get('id', '')
        data.idItemOrden = paciente_data.get('idOrdenProcedimiento', '') or paciente_data.get('id', '')
        data.nombre = paciente_data.get('nombre', '')
        data.municipio = paciente_data.get('municipio', '')
        # El primer CUPS para compatibilidad con lógica existente
        data.cups = self.cups_list[0] if self.cups_list else ''
        data.urlOrdenMedica = paciente_data.get('urlOrdenMedica', '')  # Nombre archivo PDF de la API
        data.idProcedimiento = ''
        data.idAtencion = ''
        
        # Ejecutar usando el método de la clase padre (propaga excepciones)
        resultado = self.inicio_casos(data)
        
        if resultado:
            self._log(f"✅ Proceso completado para {paciente_data.get('nombre', 'N/A')}")
            return True
        else:
            # inicio_casos retornó False = ya actualizó el estado en la API
            # Retornar False sin lanzar excepción para evitar doble actualización
            self._log(f"⚠️ inicio_casos retornó False para {paciente_data.get('nombre', 'N/A')} (estado ya actualizado)", level="warning")
            return False
    
    def _validar_datos_paciente(self, paciente_data: Dict[str, Any]) -> bool:
        """Valida que el paciente tenga los datos mínimos requeridos"""
        campos_requeridos = ['numero_identificacion', 'cups_list']
        
        for campo in campos_requeridos:
            if not paciente_data.get(campo):
                self._log(f"Campo requerido faltante: {campo}", level="error")
                return False
        
        if not paciente_data.get('cups_list'):
            self._log("Lista de CUPS vacía", level="error")
            return False
        
        return True
    
    def _ingresar_servicios(self, data):
        """
        Ingresa múltiples servicios (CUPS) para laboratorio.
        Sobrescribe el método de la clase padre para manejar múltiples CUPS.
        
        Args:
            data: Objeto con datos del paciente (compatibilidad con clase padre)
            
        Returns:
            True si todos los CUPS fueron ingresados correctamente
        """
        # Usar la lista de CUPS guardada en ejecutar()
        cups_list = getattr(self, 'cups_list', []) or [getattr(data, 'cups', '')]
        
        self._log(f"📋 _ingresar_servicios - cups_list: {cups_list}")
        
        if not cups_list or not cups_list[0]:
            self._log("No hay CUPS para ingresar", level="error")
            return False
        
        self._log(f"Ingresando {len(cups_list)} servicios (CUPS)...")
        
        try:
            # Click en botón de servicios (XPATH de la clase padre)
            clic_Boton_servicios = self.page.wait_for_selector(
                "//button[@aria-required='true'][contains(.,'Seleccionar Servicio')]", 
                timeout=5000
            )
            clic_Boton_servicios.click()
            self._log("Click en combo Servicios")
            
            # Usar el servicio especializado para laboratorio
            resultado = self.ingreso_laboratorio.ingresar_procedimientos(
                cups_list=cups_list,
                page=self.page
            )
            
            if resultado:
                self._log(f"✅ {len(cups_list)} CUPS ingresados correctamente")
            else:
                self._log("Error ingresando CUPS", level="error")
            
            return resultado
            
        except Exception as e:
            self._log(f"Error en ingreso de servicios: {e}", level="error")
            return False
    
    def _obtener_archivo_pdf(self, paciente_data: Dict[str, Any]) -> Optional[str]:
        """
        Busca el archivo PDF usando urlOrdenMedica (formato: |1_4_ARCHIVO.pdf)
        
        Args:
            paciente_data: Diccionario con datos del paciente
            
        Returns:
            Ruta al archivo PDF si existe
            
        Raises:
            Exception: Si no se encuentra el PDF (con mensaje para clasificación estado 5)
        """
        ruta_base = getattr(self.config, 'laboratorio_pdf_path', None)
        
        if not ruta_base:
            raise Exception("PDF no encontrado - LABORATORIO_PDF_PATH no configurado")
        
        # Obtener urlOrdenMedica
        if isinstance(paciente_data, dict):
            url_orden_medica = paciente_data.get('urlOrdenMedica', '')
        else:
            url_orden_medica = getattr(paciente_data, 'urlOrdenMedica', '')
        
        if not url_orden_medica:
            raise Exception("PDF no encontrado - urlOrdenMedica vacío")
        
        # Formato: |1_4_HISTORIA CLINICA.pdf - quitar el | inicial
        nombre_archivo = url_orden_medica.lstrip('|').strip()
        
        if not nombre_archivo:
            raise Exception("PDF no encontrado - nombre de archivo vacío")
        
        ruta_completa = os.path.join(ruta_base, nombre_archivo)
        existe = os.path.exists(ruta_completa)
        
        self._log(f"🔍 PDF: {ruta_completa} [{'✓ EXISTE' if existe else '✗ NO EXISTE'}]")
        
        if not existe:
            raise Exception(f"PDF no encontrado - {ruta_completa}")
        
        return ruta_completa
    
    def _manejar_solicitud_activa(self, data, error_text: str) -> bool:
        """
        Override de Anexo 3: Para LABORATORIO, 'solicitud activa' NO es éxito.
        
        COMPORTAMIENTO LABORATORIO:
        - Usa el texto COMPLETO del error (no solo el número)
        - Actualiza con estado 6 (ya radicada) en lugar de 1
        - Retorna True porque ya fue radicado (no reintentar)
        
        Args:
            data: Datos del paciente
            error_text: Texto completo del error con "solicitud activa"
            
        Returns:
            True para evitar reintento (ya está radicado)
        """
        self._log(f"🔁 SOLICITUD ACTIVA DETECTADA - Marcando como ya radicada (estado 6)")
        self._log(f"📝 Mensaje completo: {error_text}")
        
        # Registrar en archivo con mensaje completo
        with open("archivo.txt", 'a', encoding='utf-8') as archivo:
            archivo.write(f"caso,SOLICITUD ACTIVA (Lab) - {error_text},paciente,{data.identificacion},ordenCapita,{data.idItemOrden}\n")
        
        # Cerrar modal y actualizar con estado 6 y mensaje completo
        self._hacer_clic_ok()
        self.actualizar_con_resultado_ejecucion(data, "6", error_text, error_text)
        self.reinicio()
        return True  # True = no reintentar (ya está radicado)
    
    def actualizar_con_resultado_ejecucion(self, data, estado, numero_autorizacion="", resultado_ejecucion=""):
        """
        Override: solicitud activa = estado 6 (ya radicada), no estado 1.
        Envía el mensaje completo como nAutorizacion.
        """
        if resultado_ejecucion and "solicitud activa" in resultado_ejecucion.lower():
            estado = "6"
            # Enviar el mensaje completo, no solo el número de radicado
            numero_autorizacion = resultado_ejecucion
        
        self.actualizar(data, estado, numero_autorizacion)

    def actualizar(self, paciente_data, estado, numero_autorizacion: str = "") -> bool:
        """
        Actualiza el estado de un paciente en la API.
        Firma compatible con la clase padre (data, estado, numero_autorizacion).
        
        Args:
            paciente_data: Datos del paciente (objeto o dict)
            estado: Nuevo estado
            numero_autorizacion: No usado en laboratorio, solo por compatibilidad
            
        Returns:
            True si la actualización fue exitosa
        """
        from modules.laboratorio.services.laboratorio_service import LaboratorioService
        
        try:
            service = LaboratorioService()
            # Soportar tanto dict como objeto DataObject - SIEMPRE usar idOrdenProcedimiento
            if isinstance(paciente_data, dict):
                id_orden = paciente_data.get('idOrdenProcedimiento') or paciente_data.get('idOrden')
            else:
                id_orden = getattr(paciente_data, 'idOrden', None) or getattr(paciente_data, 'idItemOrden', None)
            
            estado_int = int(estado) if isinstance(estado, str) else estado
            # En laboratorio: estado 3 de la clase padre = exitoso = estado 1
            if estado_int == 3:
                estado_int = 1
            
            self._log(f"📡 Actualizando estado={estado_int} para idOrden={id_orden}, nAutorizacion={numero_autorizacion}")
            
            return service.actualizar_item_orden_procedimiento(
                id_orden_procedimiento=id_orden,
                estado_dynamicos=estado_int,
                n_autorizacion=numero_autorizacion if numero_autorizacion else None
            )
        except Exception as e:
            self._log(f"Error actualizando estado: {e}", level="error")
            return False
