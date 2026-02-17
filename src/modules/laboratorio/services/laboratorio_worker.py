"""
Worker de automatización para Laboratorio
Procesa pacientes de laboratorio de forma continua en segundo plano
"""
import threading
import time
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.laboratorio.services.laboratorio_service import LaboratorioService
from modules.laboratorio.playwright.ejecutar_casos_laboratorio import EjecutarCasosLaboratorio
from modules.autorizar_anexo3.playwright.playwright_service import PlaywrightService
from modules.autorizar_anexo3.playwright.login_playwright import LoginPlaywright
from modules.autorizar_anexo3.playwright.home_playwright import HomePlaywright
from services.license_service import LicenseService
from utils.logger import Logger


class LaboratorioWorker(threading.Thread):
    """Worker que procesa pacientes de laboratorio de forma continua"""
    
    def __init__(
        self,
        ui_callback: Optional[Callable[[str], None]] = None,
        intervalo_espera: int = 5,
        logger: Optional[Logger] = None
    ):
        """
        Args:
            ui_callback: Callback para enviar logs a la UI (recibe string)
            intervalo_espera: Segundos a esperar entre ciclos cuando no hay trabajo
            logger: Logger para registrar eventos
        """
        super().__init__(daemon=True)
        self.ui_callback = ui_callback
        self.intervalo_espera = intervalo_espera
        self.logger = logger or Logger()
        self.config = Config()
        
        # Control de estado
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # No pausado inicialmente
        
        # Servicios
        self.api_service = LaboratorioService()
        base_url = self.config.api_url_programacion_base or "http://localhost:5000"
        self.license_service = LicenseService(base_url=base_url)
        self.playwright_service: Optional[PlaywrightService] = None
        self.login_service: Optional[LoginPlaywright] = None
        self.home_service: Optional[HomePlaywright] = None
        self.ejecutar_service: Optional[EjecutarCasosLaboratorio] = None
        
        # Estadísticas
        self.stats = {
            'procesados': 0,
            'exitosos': 0,
            'errores': 0
        }
        self.on_stats_update: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Control del formulario
        self._formulario_listo = False  # Indica si ya navegamos al formulario
        
        # Sin reintentos - una sola ejecución por paciente
        # Si hay error, se actualiza estado y se continúa con el siguiente
        
        # Clasificación de errores - IGUAL QUE ANEXO 3
        # Mapeo: error_keywords -> estado_codigo
        self.errores_clasificados = {
            # Estado 4 - Tipo documento incorrecto
            4: ["tipo de documento", "documento incorrecto", "identificación inválida"],
            # Estado 5 - PDF no encontrado
            5: ["pdf no encontrado", "pdf no existe", "urlOrdenMedica vacío", 
                "no se encontró pdf", "archivo pdf", "pdf faltante"],
            # Estado 6 - Solicitud activa (ya radicada)
            6: ["solicitud activa", "ya radicada"],
            # Estado 11 - Paciente no encontrado (default para errores no clasificados)
            11: ["paciente no encontrado", "no encontrado en base", "sin procedimientos"],
            # Estado 12 - Sesión perdida
            12: ["invalid session", "session not created", "no such session", "chrome not reachable", 
                 "browser has been closed", "context has been closed", "disconnected"],
            # Estado 13 - Timeout
            13: ["timeout", "timed out", "exceeded"],
            # Estado 14 - Elemento no encontrado
            14: ["element not found", "no such element", "element not interactable", 
                 "selector", "locator", "waiting for"],
            # Estado 15 - Elemento obsoleto
            15: ["stale element", "element is not attached", "detached"],
            # Estado 16 - Conexión/network
            16: ["network", "connection", "dns", "resolve", "unreachable"],
            # Estado 18 - Permisos
            18: ["permission", "access denied", "forbidden"]
        }
    
    @property
    def paused(self) -> bool:
        """Indica si el worker está pausado"""
        return not self._pause_event.is_set()
    
    def pausar(self):
        """Pausa el procesamiento"""
        self._pause_event.clear()
        self._log("Worker pausado")
    
    def reanudar(self):
        """Reanuda el procesamiento"""
        self._pause_event.set()
        self._log("Worker reanudado")
    
    def detener(self):
        """Detiene el worker de forma segura"""
        self._log("Deteniendo worker...")
        self._stop_event.set()
        self._pause_event.set()  # Desbloquear si está pausado
        
        # Cerrar navegador
        if self.playwright_service:
            try:
                self.playwright_service.cerrar_navegador()
            except Exception as e:
                self._log(f"Error cerrando navegador: {e}", level="error")
    
    def run(self):
        """Método principal del worker"""
        self._log("Worker iniciado")
        
        try:
            # Inicializar servicios de navegación
            self._inicializar_servicios()
            
            while not self._stop_event.is_set():
                # Esperar si está pausado
                self._pause_event.wait()
                
                if self._stop_event.is_set():
                    break
                
                # Verificar saldo antes de procesar
                info_saldo = self.license_service.obtener_saldo()
                if info_saldo.get("success"):
                    saldo_actual = info_saldo.get("saldo_robot")
                    try:
                        if saldo_actual is not None and float(saldo_actual) <= 0:
                            self._log("🛑 SALDO AGOTADO - Deteniendo worker", level="error")
                            self.detener()
                            break
                    except (TypeError, ValueError):
                        pass
                
                # Obtener siguiente paciente pendiente
                pacientes = self.api_service.obtener_pacientes(estado=0)
                
                if not pacientes:
                    self._log(f"Sin pacientes pendientes. Esperando {self.intervalo_espera}s...")
                    time.sleep(self.intervalo_espera)
                    continue
                
                # Procesar el primer paciente
                paciente = pacientes[0]
                self._procesar_paciente(paciente)
                
                # Pequeña pausa entre procesamiento
                time.sleep(1)
                
        except Exception as e:
            self._log(f"Error crítico en worker: {e}", level="error")
        finally:
            self._cleanup()
            self._log("Worker finalizado")
    
    def _inicializar_servicios(self):
        """Inicializa los servicios de automatización"""
        self._log("Inicializando servicios de automatización...")
        
        try:
            # Crear servicio playwright
            self.playwright_service = PlaywrightService(self.logger)
            
            # Iniciar navegador
            if not self.playwright_service.iniciar_navegador(reutilizar_sesion=True):
                raise Exception("No se pudo iniciar el navegador")
            
            page = self.playwright_service.page
            if not page:
                raise Exception("No se pudo obtener la página")
            
            # Inicializar servicios dependientes
            self.login_service = LoginPlaywright(page, self.logger)
            self.home_service = HomePlaywright(page, self.logger)
            self.ejecutar_service = EjecutarCasosLaboratorio(page, self.logger)
            
            # Verificar sesión o hacer login
            if not self.playwright_service.sesion_valida():
                self._log("Realizando login...")
                try:
                    login_exitoso = self.login_service.realizar_login_completo()
                except Exception as e:
                    self._log(f"Error en login: {e}", level="error")
                    login_exitoso = False
                
                if not login_exitoso:
                    raise Exception("Login fallido")
                
                # Guardar sesión
                self.playwright_service.guardar_sesion()
            else:
                self._log("Sesión válida detectada, reutilizando")
            
            self._log("Servicios inicializados.")
            
        except Exception as e:
            self._log(f"Error inicializando servicios: {e}", level="error")
            raise
    
    def _procesar_paciente(self, paciente: Dict[str, Any]):
        """
        Procesa un paciente individual con manejo de errores y clasificación de estados.
        Usa el mismo esquema de estados que Anexo 3.
        """
        from datetime import datetime
        
        # Log datos brutos para depuración
        self._log(f"📥 Datos paciente API: {list(paciente.keys())}")
        
        # idOrdenProcedimiento es el ID para actualizar estados (NO facturaEvento)
        id_orden_procedimiento = paciente.get('idOrdenProcedimiento')
        factura_evento = paciente.get('facturaEvento')  # Solo para referencia/logs
        nombre = paciente.get('nombre', 'Desconocido')
        identificacion = paciente.get('identificacion', 'N/A')
        url_orden_medica = paciente.get('urlOrdenMedica', '')  # Nombre del archivo PDF
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self._log(f"📋 idOrdenProcedimiento: {id_orden_procedimiento}, facturaEvento: {factura_evento}")
        self._log(f"📄 urlOrdenMedica desde API: '{url_orden_medica}'")
        
        self._log(f"Procesando paciente: {nombre} (idOrdenProcedimiento: {id_orden_procedimiento})")
        
        try:
            # Marcar como en proceso (estado = 2)
            self._log(f"Actualizando idOrdenProcedimiento {id_orden_procedimiento} a estado EN PROCESO (2)...")
            actualizado = self.api_service.marcar_como_en_proceso(id_orden_procedimiento)
            if actualizado:
                self._log(f"✓ idOrdenProcedimiento {id_orden_procedimiento} marcada como EN PROCESO")
            else:
                self._log(f"⚠️ No se pudo marcar idOrdenProcedimiento {id_orden_procedimiento} como EN PROCESO", level="warning")
            
            # Asegurar que el navegador esté activo
            self._asegurar_navegador_activo()
            
            # Navegar al formulario solo si es el primer paciente o si es necesario
            if not self._formulario_listo:
                if not self._navegar_a_formulario():
                    raise Exception("No se pudo navegar al formulario")
                self._formulario_listo = True
            
            # Obtener los procedimientos (CUPS) de la orden usando idOrdenProcedimiento (NO facturaEvento)
            # La API procedimientos-orden espera idOrden que corresponde a Id_Ordenes = idOrdenProcedimiento
            self._log(f"🔍 Obteniendo procedimientos para idOrden: {id_orden_procedimiento}")
            procedimientos = self.api_service.obtener_procedimientos_orden(id_orden_procedimiento)
            
            self._log(f"📋 Procedimientos obtenidos: {len(procedimientos)} items")
            for i, p in enumerate(procedimientos):
                self._log(f"   [{i+1}] C_Homologado: {p.get('C_Homologado', 'N/A')}, Id_Procedimiento: {p.get('Id_Procedimiento', 'N/A')}")
            
            if not procedimientos:
                self._log(f"Sin procedimientos para facturaEvento {factura_evento}", level="warning")
                self._actualizar_estado_error(id_orden_procedimiento, identificacion, 11, "Sin procedimientos")
                # Reiniciar formulario para siguiente paciente
                self._reiniciar_formulario()
                return
            
            # Construir datos del paciente para el ejecutor
            paciente_data = self._construir_datos_paciente(paciente, procedimientos)
            self._log(f"📦 cups_list en paciente_data: {paciente_data.get('cups_list', [])}")
            
            # Ejecutar automatizacion
            resultado = self.ejecutar_service.ejecutar(paciente_data)
            
            if resultado:
                self._marcar_completado(id_orden_procedimiento, nombre)
            else:
                raise Exception("Error en automatización - resultado False")
                
        except Exception as e:
            error_message = str(e).lower()
            self._log(f"❌ Error procesando paciente {nombre}: {e}", level="error")
            
            # Clasificar error y actualizar estado
            estado_error = self._clasificar_error(error_message)
            self._actualizar_estado_error(id_orden_procedimiento, identificacion, estado_error, str(e))
            
            # Si fue error de sesión, marcar para reinicializar
            if estado_error == 12:
                self._formulario_listo = False
        
        finally:
            # SIEMPRE reiniciar formulario para el siguiente paciente
            try:
                self._reiniciar_formulario()
            except Exception as e:
                self._log(f"⚠️ Error reiniciando formulario: {e}", level="warning")
                self._formulario_listo = False
    
    def _reiniciar_formulario(self):
        """
        Reinicia el formulario haciendo clic en Urgencias y luego Ambulatoria.
        Esto limpia el formulario para el siguiente paciente.
        """
        try:
            self._log("🔄 Reiniciando formulario para siguiente paciente...")
            # Usar el método reinicio() del ejecutor que hereda de EjecutarCasosPlaywright
            self.ejecutar_service.reinicio()
            self._log("✅ Formulario reiniciado correctamente")
        except Exception as e:
            self._log(f"⚠️ Error en reinicio de formulario: {e}", level="warning")
            # Si falla el reinicio, navegar de nuevo al formulario
            self._formulario_listo = False
    
    def _clasificar_error(self, error_message: str) -> int:
        """
        Clasifica el error y retorna el código de estado correspondiente.
        Usa el mismo esquema de estados que Anexo 3.
        
        Returns:
            Código de estado (4, 11-19)
        """
        for estado, keywords in self.errores_clasificados.items():
            if any(keyword in error_message for keyword in keywords):
                return estado
        return 11  # Default: Error no clasificado
    
    def _actualizar_estado_error(self, id_orden_procedimiento: int, identificacion: str, estado: int, error: str):
        """
        Actualiza el estado de la orden con un código de error específico.
        Imprime log con formato igual a Anexo 3.
        """
        mensajes_estado = {
            4: ("❌ TIPO DE DOCUMENTO INCORRECTO", "[DOCUMENTO]"),
            5: ("📄 PDF NO ENCONTRADO", "[PDF FALTANTE]"),
            6: ("🔁 SOLICITUD ACTIVA - YA RADICADA", "[YA RADICADA]"),
            11: ("❌ ERROR NO CLASIFICADO", "[ERROR]"),
            12: ("❌ SESIÓN DEL NAVEGADOR PERDIDA", "[SESIÓN PERDIDA]"),
            13: ("⏰ TIMEOUT - ELEMENTO NO RESPONDIÓ A TIEMPO", "[TIMEOUT]"),
            14: ("🎯 ELEMENTO NO ENCONTRADO EN LA PÁGINA", "[ELEMENTO FALTANTE]"),
            15: ("🔄 ELEMENTO OBSOLETO - PÁGINA SE ACTUALIZÓ", "[ELEMENTO OBSOLETO]"),
            16: ("🌐 ERROR DE CONEXIÓN A INTERNET", "[SIN INTERNET]"),
            18: ("🔒 ERROR DE PERMISOS O ACCESO DENEGADO", "[SIN PERMISOS]"),
        }
        
        emoji_msg, tag = mensajes_estado.get(estado, ("❌ ERROR", "[ERROR]"))
        self._log(f"{emoji_msg}")
        print(f"{tag} Paciente {identificacion} - {error[:100]}")
        
        # Actualizar en la API usando idOrdenProcedimiento
        self.api_service.actualizar_item_orden_procedimiento(
            id_orden_procedimiento=id_orden_procedimiento,
            estado_dynamicos=estado,
            error_mensaje=error[:500]  # Limitar longitud del mensaje
        )
        self._log(f"✓ idOrdenProcedimiento {id_orden_procedimiento} marcada con estado={estado}")
        
        self._actualizar_stats(error=True)
    
    def _marcar_completado(self, id_orden_procedimiento: int, nombre: str):
        """Marca una orden como completada exitosamente (estado = 1)"""
        self._log(f"✅ Paciente {nombre} procesado exitosamente")
        self.api_service.marcar_como_exitoso(id_orden_procedimiento)
        
        # Descontar saldo por caso exitoso
        resultado_descuento = self.license_service.descontar_caso_exitoso()
        
        if resultado_descuento.get("success"):
            saldo_nuevo = resultado_descuento.get("saldo_nuevo", 0)
            valor_descontado = resultado_descuento.get("valor_descontado", 0)
            self._log(f"💰 Saldo descontado: {valor_descontado} | Saldo restante: {saldo_nuevo}")
            
            # Verificar si el saldo se agotó
            if resultado_descuento.get("saldo_agotado"):
                self._log("⚠️ SALDO AGOTADO - Deteniendo worker")
                self.detener()
                self._log("🛑 Worker detenido por saldo agotado")
        else:
            self._log(f"⚠️ Error descontando saldo: {resultado_descuento.get('message')}")
        
        self._actualizar_stats(exitoso=True)
        self._log(f"✓ idOrdenProcedimiento {id_orden_procedimiento} marcada como EXITOSO (estado=1)")
    
    def _construir_datos_paciente(
        self, 
        paciente: Dict[str, Any], 
        procedimientos: list
    ) -> Dict[str, Any]:
        """Construye el diccionario de datos del paciente"""
        # Extraer CUPS de los procedimientos (campo C_Homologado)
        cups_list = []
        for p in procedimientos:
            if isinstance(p, dict):
                # El campo CUPS viene como C_Homologado
                cups = p.get('C_Homologado', '') or p.get('Id_Procedimiento', '')
                if cups:
                    cups_list.append(str(cups))
            elif isinstance(p, str) and p:
                # Si el procedimiento es directamente un string (el CUPS)
                cups_list.append(p)
        
        url_orden_medica = paciente.get('urlOrdenMedica', '')
        self._log(f"🔧 Construyendo datos - CUPS: {cups_list}, urlOrdenMedica: '{url_orden_medica}'")
        
        return {
            'id': paciente.get('facturaEvento'),  # ID factura (para procedimientos)
            'idOrdenProcedimiento': paciente.get('idOrdenProcedimiento'),  # ID para actualizar estados
            'tipo_identificacion': paciente.get('tipoIdentificacion', 'CC'),
            'numero_identificacion': paciente.get('identificacion', ''),
            'nombre': paciente.get('nombre', ''),
            'diagnostico': paciente.get('diagnostico', ''),
            'telefono': paciente.get('telefono', ''),
            'municipio': paciente.get('municipio', ''),
            'fecha': paciente.get('fechaFacturaEvento', ''),
            'procedimientos': procedimientos,
            'cups_list': cups_list,
            'urlOrdenMedica': url_orden_medica  # Nombre del archivo PDF
        }
    
    def _navegar_a_formulario(self) -> bool:
        """Navega al formulario de reportar ambulatoria"""
        try:
            return self.home_service.navegar_a_reportar_ambulatoria()
        except Exception as e:
            self._log(f"Error navegando a formulario: {e}", level="error")
            return False
    
    def _asegurar_navegador_activo(self):
        """Asegura que el navegador esté activo y conectado"""
        try:
            if not self.playwright_service or not self.playwright_service.page:
                self._log("Reconectando navegador...")
                self._inicializar_servicios()
                return
            
            # Verificar que la página esté activa
            if self.playwright_service.page:
                try:
                    self.playwright_service.page.title()
                except:
                    self._log("Página cerrada, reinicializando...")
                    self._inicializar_servicios()
                    
        except Exception as e:
            self._log(f"Error verificando navegador: {e}", level="error")
            self._inicializar_servicios()
    
    def _actualizar_stats(self, exitoso: bool = False, error: bool = False):
        """Actualiza las estadísticas del worker"""
        self.stats['procesados'] += 1
        if exitoso:
            self.stats['exitosos'] += 1
        if error:
            self.stats['errores'] += 1
            
        if self.on_stats_update:
            self.on_stats_update(self.stats)
    
    def _log(self, mensaje: str, level: str = "info"):
        """Registra un mensaje en el log"""
        modulo = "LaboratorioWorker"
        # Log a archivo
        if level == "error":
            self.logger.error(modulo, mensaje)
        else:
            self.logger.info(modulo, mensaje)
        
        # Callback a UI - solo envía el mensaje
        if self.ui_callback:
            try:
                self.ui_callback(mensaje)
            except Exception as e:
                print(f"Error en callback de UI: {e}")
    
    def _cleanup(self):
        """Limpieza al finalizar"""
        if self.playwright_service:
            try:
                self.playwright_service.cerrar_navegador()
            except:
                pass
