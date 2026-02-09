"""
Worker de automatización en background
Thread que procesa órdenes programadas usando Playwright
"""
import time
import threading
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path

from utils.logger import AdvancedLogger
from modules.autorizar_anexo3.services.programacion_service import ProgramacionService
from modules.autorizar_anexo3.playwright.playwright_service import PlaywrightService
from modules.autorizar_anexo3.playwright.login_playwright import LoginPlaywright
from modules.autorizar_anexo3.playwright.home_playwright import HomePlaywright
from modules.autorizar_anexo3.playwright.ejecutar_casos_playwright import EjecutarCasosPlaywright


class AutomationWorker(threading.Thread):
    """Worker que procesa órdenes programadas en background"""
    
    def __init__(self, ui_callback: Optional[Callable] = None):
        """
        Args:
            ui_callback: Callback para actualizar UI
        """
        super().__init__()
        self.daemon = True  # Thread se cierra cuando app cierra
        
        # Estado del worker
        self.running = False
        self.paused = False
        
        # Servicios
        self.logger = AdvancedLogger(ui_callback=ui_callback)
        self.api_service = ProgramacionService(logger=self.logger)
        self.playwright_service: Optional[PlaywrightService] = None
        
        # Control de navegador
        self.ultima_actividad = None
        self.timeout_inactividad = 3600  # 1 hora en segundos
        self.poll_interval = 5  # Consultar cada 5 segundos
        self._formulario_navegado = False  # Bandera para saber si ya navegamos al formulario
        
        # Estadísticas
        self.procesados = 0
        self.exitosos = 0
        self.errores = 0
        
        # Callbacks para UI
        self.on_status_change: Optional[Callable] = None
        self.on_stats_update: Optional[Callable] = None
    
    def run(self):
        """Loop principal del worker"""
        self.logger.info('Worker', '🚀 Worker de automatización iniciado')
        self.running = True
        
        while self.running:
            try:
                # Verificar si está pausado
                if self.paused:
                    time.sleep(1)
                    continue
                
                # Obtener órdenes pendientes
                pendientes = self.api_service.obtener_pendientes()
                
                if pendientes:
                    self.logger.info('Worker', f'📋 {len(pendientes)} órdenes pendientes encontradas')
                    self.ultima_actividad = time.time()
                    
                    # Asegurar que el navegador esté activo
                    if not self.asegurar_navegador_activo():
                        self.logger.error('Worker', 'No se pudo iniciar navegador, esperando...')
                        time.sleep(30)
                        continue
                    
                    # Procesar cada orden
                    for orden in pendientes:
                        if not self.running or self.paused:
                            break
                        
                        self.procesar_orden(orden)
                    
                    # Notificar si terminamos todos
                    if self.running and not self.paused:
                        self.logger.success('Worker', '🎉 Todas las órdenes pendientes han sido procesadas')
                        self.reproducir_sonido_completado()
                
                else:
                    # No hay pendientes
                    self.verificar_inactividad()
                
                # Esperar antes de siguiente consulta
                time.sleep(self.poll_interval)
                
            except Exception as e:
                self.logger.error('Worker', 'Error en loop principal', e)
                time.sleep(10)  # Esperar más tiempo en caso de error
        
        self.logger.info('Worker', '⏹️ Worker detenido')
        self.cerrar_navegador()
    
    def procesar_orden(self, orden: dict):
        """
        Procesa una orden individual.
        
        Args:
            orden: Diccionario con datos de programacion_ordenes
        """
        id_item = orden.get('id_item_orden_proced')
        intentos_realizados = orden.get('intentos_realizados', 0)
        intentos_maximos = orden.get('intentos_maximos', 2)
        
        self.logger.info('Worker', f'▶️ Procesando orden {id_item} (intento {intentos_realizados + 1}/{intentos_maximos})')
        
        # Obtener datos completos del paciente
        datos_paciente = self.api_service.obtener_datos_orden(id_item)
        if not datos_paciente:
            self.logger.error('Worker', f'No se encontraron datos para orden {id_item}')
            self.marcar_error(id_item, "Datos de paciente no encontrados")
            return
        
        nombre_paciente = f"{datos_paciente.get('Nombre1','')} {datos_paciente.get('Apellido1','')}"
        
        # Actualizar a EN_PROGRESO
        if intentos_realizados == 0:
            # Primer intento: actualizar fecha_inicio y estadoCaso
            fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.api_service.actualizar_estado_programacion(
                id_item, 
                "EN_PROGRESO",
                fecha_inicio=fecha_inicio,
                usuario_ejecuto="worker_automatico"
            )
            self.api_service.actualizar_estado_caso(id_item, 3)  # 3 = En proceso
            
            # Guardar fecha_inicio para usarla después
            self.fecha_inicio_actual = fecha_inicio
            self.logger.info('Worker', f'🚀 Primer intento - estadoCaso actualizado a 3')
        else:
            # Reintento: solo cambiar estado a EN_PROGRESO, NO tocar estadoCaso ni fecha_inicio
            self.api_service.actualizar_estado_programacion(
                id_item, 
                "EN_PROGRESO",
                usuario_ejecuto="worker_automatico"
            )
            # NO actualizar estadoCaso (ya está en 3 desde el primer intento)
            self.logger.info('Worker', f'🔄 Reintento {intentos_realizados + 1}/{intentos_maximos} - estadoCaso permanece en 3')
        
        try:
            # Ejecutar automatización
            self.logger.info('Worker', f'🤖 Automatizando: {nombre_paciente}')
            
            # Navegar al formulario solo la primera vez después de login
            # Para casos subsecuentes, el método reinicio() del ejecutor 
            # ya deja el formulario listo después de cada caso
            if not self._formulario_navegado:
                self.logger.debug('Worker', 'Primera navegación al formulario...')
                if not self.navegar_a_formulario():
                    raise Exception("No se pudo navegar al formulario")
                self._formulario_navegado = True
            else:
                # Verificar que el formulario sigue accesible
                self.logger.debug('Worker', f'Formulario ya navegado (intento {intentos_realizados + 1}/{intentos_maximos}). Verificando estado...')
                try:
                    url_actual = self.playwright_service.page.url
                    self.logger.debug('Worker', f'URL actual: {url_actual}')
                    if 'portalsalud.coosalud.com' not in url_actual:
                        self.logger.warning('Worker', '⚠️ Página incorrecta, navegando de nuevo al formulario...')
                        if not self.navegar_a_formulario():
                            raise Exception("No se pudo navegar al formulario en reintento")
                except Exception as page_error:
                    self.logger.error('Worker', f'Error verificando página: {page_error}')
                    # Si hay error verificando la página, mejor navegar de nuevo
                    self.logger.info('Worker', 'Navegando de nuevo al formulario por seguridad...')
                    if not self.navegar_a_formulario():
                        raise Exception("No se pudo navegar al formulario después de error")
            # Para reintentos o siguientes órdenes, el formulario ya está listo
            
            # Ejecutar caso - usar inicio_casos como en Selenium
            ejecutor = EjecutarCasosPlaywright(
                self.playwright_service.page, 
                self.logger
            )
            
            # Convertir datos_paciente a objeto con atributos (como en Selenium)
            class DataObject:
                pass
            data = DataObject()
            for key, value in datos_paciente.items():
                setattr(data, key, value)
            # Mapear campos adicionales que usa inicio_casos
            data.tipoIdentificacion = datos_paciente.get('TipoIdentificacion', 'Cédula de Ciudadanía')
            data.identificacion = datos_paciente.get('NoDocumento', '')
            data.telefono = datos_paciente.get('telefono', '')
            data.fechaFacturaEvento = datos_paciente.get('FechaOrden', '')
            data.diagnostico = datos_paciente.get('DxIngreso', '')
            data.idItemOrden = datos_paciente.get('idItemOrden', id_item)
            data.idOrden = datos_paciente.get('idOrden', '')
            data.urlOrdenMedica = datos_paciente.get('urlOrdenMedica', '')
            # Nuevos campos agregados al JSON
            data.idProcedimiento = datos_paciente.get('idProcedimiento', '')
            data.idAtencion = datos_paciente.get('idAtencion', '')
            data.cups = datos_paciente.get('cups', '')
            
            if ejecutor.inicio_casos(data):
                # ÉXITO
                self.marcar_completado(id_item, nombre_paciente)
            else:
                # FALLO - Determinar si es error permanente o temporal
                raise Exception("Error ejecutando caso")
            
        except Exception as e:
            # Error en automatización
            error_msg = str(e).lower()
            self.logger.error('Worker', f'Error procesando {nombre_paciente}', e)
            
            # Errores PERMANENTES que NO deben reintentarse:
            # - Duplicados (servicio ya reportado anteriormente)
            # - Tipo de documento incorrecto
            # - Paciente no encontrado
            # - IPS no encontrada
            # - Archivo no existe
            errores_permanentes = [
                'duplicado', 'ya reportado', 'ya existe',
                'servicio', 'número de radicado',  # Mensaje de duplicado del portal
                'tipo documento', 'tipo de documento',
                'paciente no encontrado',
                'ips no encontrada',
                'archivo no encontrado', 'pdf no encontrado'
            ]
            
            # Errores TEMPORALES que SÍ deben reintentarse:
            # - Timeouts de red/página
            # - Sesión perdida (puede recuperarse con login)
            # - Conexión de red
            errores_temporales = [
                'timeout', 'timed out', 
                'session', 'sesión',
                'network', 'connection',
                'temporarily unavailable'
            ]
            
            es_error_permanente = any(keyword in error_msg for keyword in errores_permanentes)
            es_error_temporal = any(keyword in error_msg for keyword in errores_temporales)
            
            # Incrementar contador de intentos
            intentos_realizados += 1
            
            if es_error_permanente:
                # Error PERMANENTE - No reintentar (ej: duplicado, tipo documento incorrecto)
                self.logger.warning('Worker', f'⚠️ Error permanente detectado, marcando como ERROR final: {e}')
                self.marcar_error(id_item, f"Error permanente: {str(e)}")
            elif intentos_realizados >= intentos_maximos:
                # Ya se agotaron los intentos - marcar como ERROR final
                self.marcar_error(id_item, str(e))
            elif es_error_temporal:
                # Error TEMPORAL - vale la pena reintentar
                self.logger.info('Worker', f'🔄 Error temporal detectado, se reintentará: {e}')
                self.marcar_para_reintento(id_item, str(e))
            else:
                # Error desconocido - no reintentar por seguridad
                self.logger.warning('Worker', f'⚠️ Error desconocido, marcando como ERROR final: {e}')
                self.marcar_error(id_item, f"Error no clasificado: {str(e)}")
    
    def marcar_completado(self, id_item: int, nombre_paciente: str):
        """Marca una orden como completada exitosamente"""
        fecha_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.api_service.actualizar_estado_programacion(
            id_item,
            "COMPLETADO",
            fecha_inicio=getattr(self, 'fecha_inicio_actual', None),
            fecha_fin=fecha_fin,
            usuario_ejecuto="worker_automatico",
            resultado="OK"
        )
        self.api_service.actualizar_estado_caso(id_item, 1)  # 1 = Completado
        
        self.exitosos += 1
        self.procesados += 1
        self.actualizar_estadisticas()
        
        self.logger.success('Worker', f'✅ Orden {id_item} ({nombre_paciente}) COMPLETADA')
    
    def marcar_error(self, id_item: int, error: str):
        """Marca una orden con error final"""
        fecha_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.api_service.actualizar_estado_programacion(
            id_item,
            "ERROR",
            fecha_inicio=getattr(self, 'fecha_inicio_actual', None),
            fecha_fin=fecha_fin,
            usuario_ejecuto="worker_automatico",
            resultado="ERROR",
            mensaje_error=error
        )
        self.api_service.actualizar_estado_caso(id_item, 4)  # 4 = Error
        
        # Screenshot de error
        if self.playwright_service and self.playwright_service.page:
            screenshot_path = self.playwright_service.take_screenshot(f"error_{id_item}")
            self.logger.save_screenshot_info(screenshot_path, str(id_item), error)
        
        self.errores += 1
        self.procesados += 1
        self.actualizar_estadisticas()
        
        self.logger.error('Worker', f'❌ Orden {id_item} marcada como ERROR: {error}')
        
        # Alertar si muchos errores consecutivos
        if self.errores >= 5 and self.exitosos == 0:
            self.logger.critical('Worker', '🚨 ALERTA: 5 errores consecutivos detectados')
            self.reproducir_sonido_error()
    
    def marcar_para_reintento(self, id_item: int, error: str):
        """Marca una orden para reintentar después (incrementa intentos, no actualiza estadoCaso)"""
        self.api_service.actualizar_estado_programacion(
            id_item,
            "PENDIENTE",  # Volver a pendiente
            mensaje_error=f"Intento fallido: {error}",
            incrementar_intentos=True  # Incrementar contador de intentos
        )
        # NO actualizar estadoCaso aquí, se mantiene en 3 (en proceso)
        
        self.logger.warning('Worker', f'⚠️ Orden {id_item} reintentará después (intentos incrementados, estadoCaso permanece en 3)')
    
    def asegurar_navegador_activo(self) -> bool:
        """
        Asegura que el navegador esté activo y con sesión válida.
        
        Returns:
            True si el navegador está listo
        """
        try:
            # Si no hay servicio, crear
            if not self.playwright_service:
                self.logger.info('Worker', 'Creando servicio Playwright...')
                self.playwright_service = PlaywrightService(self.logger)
            
            # Si no está activo, iniciar
            if not self.playwright_service.esta_activo():
                self.logger.info('Worker', 'Iniciando navegador...')
                if not self.playwright_service.iniciar_navegador(reutilizar_sesion=True):
                    return False
            
            # Verificar sesión
            if not self.playwright_service.sesion_valida():
                self.logger.info('Worker', 'Sesión no válida, haciendo login...')
                if not self.hacer_login():
                    return False
            else:
                self.logger.success('Worker', '✅ Sesión válida detectada, reutilizando')
            
            return True
            
        except Exception as e:
            self.logger.error('Worker', 'Error asegurando navegador activo', e)
            return False
    
    def hacer_login(self) -> bool:
        """Ejecuta el proceso de login completo"""
        try:
            # Ya estamos en la página (se navegó en iniciar_navegador)
            # Solo ejecutar login
            login_service = LoginPlaywright(self.playwright_service.page, self.logger)
            if not login_service.realizar_login_completo():
                return False
            
            # Guardar sesión
            self.playwright_service.guardar_sesion()
            
            return True
            
        except Exception as e:
            self.logger.error('Worker', 'Error en login', e)
            return False
    
    def navegar_a_formulario(self) -> bool:
        """Navega al formulario de reportar ambulatoria"""
        try:
            home_service = HomePlaywright(self.playwright_service.page, self.logger)
            return home_service.navegar_a_reportar_ambulatoria()
        except Exception as e:
            self.logger.error('Worker', 'Error navegando a formulario', e)
            return False
    
    def refrescar_solo_pagina(self) -> bool:
        """Solo refresca la página actual sin navegar de nuevo (para reintentos)"""
        try:
            self.logger.debug('Worker', 'Refrescando página actual...')
            self.playwright_service.page.reload(wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)
            self.logger.debug('Worker', 'Página refrescada')
            return True
        except Exception as e:
            self.logger.error('Worker', 'Error refrescando página', e)
            return False
    
    def refrescar_formulario(self) -> bool:
        """Refresca la página y navega de nuevo al formulario para limpiar datos"""
        try:
            self.logger.debug('Worker', 'Refrescando página...')
            self.playwright_service.page.reload(wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)
            
            # Navegar de nuevo al formulario
            home_service = HomePlaywright(self.playwright_service.page, self.logger)
            return home_service.navegar_a_reportar_ambulatoria()
        except Exception as e:
            self.logger.error('Worker', 'Error refrescando formulario', e)
            return False
    
    def verificar_inactividad(self):
        """Verifica inactividad y cierra navegador si supera timeout"""
        if not self.ultima_actividad:
            return
        
        tiempo_inactivo = time.time() - self.ultima_actividad
        
        if tiempo_inactivo > self.timeout_inactividad:
            minutos = int(tiempo_inactivo / 60)
            self.logger.info('Worker', f'💤 Sin actividad por {minutos} minutos. Cerrando navegador...')
            self.cerrar_navegador()
            self.ultima_actividad = None
    
    def cerrar_navegador(self):
        """Cierra el navegador y limpia recursos"""
        if self.playwright_service:
            self.playwright_service.cerrar_navegador()
            self.playwright_service = None
        self._formulario_navegado = False  # Resetear bandera
    
    def actualizar_estadisticas(self):
        """Actualiza estadísticas y notifica a UI"""
        if self.on_stats_update:
            try:
                self.on_stats_update({
                    'procesados': self.procesados,
                    'exitosos': self.exitosos,
                    'errores': self.errores
                })
            except:
                pass
    
    def reproducir_sonido_completado(self):
        """Reproduce sonido cuando termina todos los pendientes"""
        try:
            import winsound
            winsound.Beep(1000, 500)  # 1000Hz por 500ms
        except:
            pass
    
    def reproducir_sonido_error(self):
        """Reproduce sonido de alerta por errores"""
        try:
            import winsound
            winsound.Beep(400, 1000)  # 400Hz por 1 segundo
        except:
            pass
    
    def pausar(self):
        """Pausa el worker"""
        self.paused = True
        self.logger.info('Worker', '⏸️ Worker pausado')
    
    def reanudar(self):
        """Reanuda el worker"""
        self.paused = False
        self.logger.info('Worker', '▶️ Worker reanudado')
    
    def detener(self):
        """Detiene el worker completamente"""
        self.running = False
        self.paused = True
        self.logger.info('Worker', '⏹️ Deteniendo worker...')
        # Cerrar navegador inmediatamente para cortar la automatizacion
        self.cerrar_navegador()
