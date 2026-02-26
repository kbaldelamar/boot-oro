"""
Worker de automatización para Finalizar Casos Laboratorio.
Procesa casos de forma continua en segundo plano.
Usa clases Playwright independientes (no depende de autorizar_anexo3).
"""
import threading
import time
from typing import Optional, Callable, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.finalizar_casos.services.finalizar_casos_service import FinalizarCasosService
from modules.finalizar_casos.playwright.playwright_service_fc import PlaywrightServiceFC
from modules.finalizar_casos.playwright.login_playwright_fc import LoginPlaywrightFC
from modules.finalizar_casos.playwright.home_playwright_fc import HomePlaywrightFC
from modules.finalizar_casos.playwright.ejecutar_casos_fc import EjecutarCasosFC, PausedException


class FinalizarCasosWorker(threading.Thread):
    """Worker que procesa casos de finalización de laboratorio de forma continua"""

    def __init__(
        self,
        ui_callback: Optional[Callable[[str], None]] = None,
        intervalo_espera: int = 10
    ):
        """
        Args:
            ui_callback: Callback para enviar logs a la UI (recibe string)
            intervalo_espera: Segundos a esperar entre ciclos cuando no hay trabajo
        """
        super().__init__(daemon=True)
        self.ui_callback = ui_callback
        self.intervalo_espera = intervalo_espera
        self.config = Config()

        # Control de estado
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # No pausado inicialmente

        # Servicio API
        self.api_service = FinalizarCasosService()

        # Servicios Playwright (independientes)
        self.playwright_service: Optional[PlaywrightServiceFC] = None
        self.login_service: Optional[LoginPlaywrightFC] = None
        self.home_service: Optional[HomePlaywrightFC] = None
        self.ejecutar_service: Optional[EjecutarCasosFC] = None

        # Control del formulario
        self._formulario_listo = False

        # Estadísticas
        self.stats: Dict[str, int] = {
            'procesados': 0,
            'exitosos': 0,
            'errores': 0
        }
        self.on_stats_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_data_update: Optional[Callable[[list], None]] = None  # Callback para enviar casos al panel

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    @property
    def paused(self) -> bool:
        return not self._pause_event.is_set()

    def pausar(self):
        self._pause_event.clear()
        self._log("⏸️ Worker pausado")

    def reanudar(self):
        self._pause_event.set()
        self._log("▶️ Worker reanudado")

    def detener(self):
        self._log("⏹️ Deteniendo worker...")
        self._stop_event.set()
        self._pause_event.set()  # Desbloquear si pausado

        # Cerrar navegador
        if self.playwright_service:
            try:
                self.playwright_service.cerrar_navegador()
            except Exception as e:
                self._log(f"Error cerrando navegador: {e}", level="error")

        self._log("Señal de detención enviada")

    # ------------------------------------------------------------------
    # Inicialización de Playwright
    # ------------------------------------------------------------------

    def _inicializar_servicios(self):
        """Inicializa los servicios de Playwright (navegador, login, home)"""
        self._log("🌐 Inicializando servicios de navegación...")

        try:
            # Crear servicio Playwright independiente
            self.playwright_service = PlaywrightServiceFC()

            # Iniciar navegador
            if not self.playwright_service.iniciar_navegador(reutilizar_sesion=True):
                raise Exception("No se pudo iniciar el navegador")

            page = self.playwright_service.page
            if not page:
                raise Exception("No se pudo obtener la página")

            # Inicializar servicios dependientes
            self.login_service = LoginPlaywrightFC(page, self.playwright_service.logger)
            self.home_service = HomePlaywrightFC(page, self.playwright_service.logger)

            # Verificar sesión o hacer login
            if not self.playwright_service.sesion_valida():
                self._log("🔑 Realizando login...")
                login_exitoso = self.login_service.realizar_login_completo()

                if not login_exitoso:
                    raise Exception("Login fallido")

                # Guardar sesión
                self.playwright_service.guardar_sesion()
            else:
                self._log("✅ Sesión válida detectada, reutilizando")

            # Inicializar servicio de ejecución de casos
            self.ejecutar_service = EjecutarCasosFC(
                page=page,
                api_service=self.api_service,
                log_function=lambda msg: self._log(msg),
                pause_callback=lambda: self.paused,
            )

            self._log("✅ Servicios de navegación inicializados")

        except Exception as e:
            self._log(f"❌ Error inicializando servicios: {e}", level="error")
            raise

    def _navegar_a_formulario(self) -> bool:
        """Navega a Referencia Ambulatoria"""
        try:
            return self.home_service.navegar_a_referencia_ambulatoria()
        except Exception as e:
            self._log(f"❌ Error navegando a formulario: {e}", level="error")
            return False

    def _asegurar_navegador_activo(self):
        """Asegura que el navegador esté activo y conectado"""
        try:
            if not self.playwright_service or not self.playwright_service.page:
                self._log("🔄 Reconectando navegador...")
                self._inicializar_servicios()
                return

            # Verificar que la página esté activa
            if self.playwright_service.page:
                try:
                    self.playwright_service.page.title()
                except Exception:
                    self._log("🔄 Página cerrada, reinicializando...")
                    self._inicializar_servicios()

        except Exception as e:
            self._log(f"❌ Error verificando navegador: {e}", level="error")
            self._inicializar_servicios()

    # ------------------------------------------------------------------
    # Ejecución principal
    # ------------------------------------------------------------------

    def run(self):
        self._log("🚀 Worker Finalizar Casos iniciado")

        try:
            # Inicializar navegador y hacer login
            self._inicializar_servicios()

            while not self._stop_event.is_set():
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                # Obtener casos pendientes (ÚNICO GET centralizado)
                casos = self.api_service.obtener_casos()

                # Enviar datos al panel para refrescar tabla
                if self.on_data_update:
                    self.on_data_update(casos if casos else [])

                if not casos:
                    self._log(f"Sin casos pendientes. Esperando {self.intervalo_espera}s...")
                    for _ in range(self.intervalo_espera):
                        if self._stop_event.is_set():
                            break
                        time.sleep(1)
                    continue

                caso = casos[0]
                self._procesar_caso(caso)

                if not self._stop_event.is_set():
                    time.sleep(1)

        except Exception as e:
            self._log(f"❌ Error crítico: {e}", level="error")
        finally:
            self._cleanup()
            self._log("Worker Finalizar Casos finalizado")

    # ------------------------------------------------------------------
    # Procesamiento
    # ------------------------------------------------------------------

    def _procesar_caso(self, caso: Dict[str, Any]):
        """
        Procesa un caso individual delegando a EjecutarCasosFC.
        """
        id_orden = caso.get('idOrden', '?')
        texto_caso = caso.get('caso', '')
        self._log(f"📋 Procesando caso idOrden={id_orden}: {texto_caso[:80]}...")

        try:
            # Asegurar que el navegador esté activo
            self._asegurar_navegador_activo()

            # Navegar al formulario solo la primera vez
            if not self._formulario_listo:
                if not self._navegar_a_formulario():
                    raise Exception("No se pudo navegar al formulario")
                self._formulario_listo = True

            # Ejecutar la lógica de finalización
            exito, error = self.ejecutar_service.ejecutar_ingreso(caso)

            if exito:
                self._log(f"✅ Caso {id_orden} procesado correctamente")
                self._actualizar_stats(exitoso=True)
            else:
                self._log(f"❌ Caso {id_orden} falló: {error}")
                self._actualizar_stats(error=True)

        except PausedException:
            self._log(f"⏸️ Caso {id_orden} interrumpido por pausa")
        except Exception as e:
            self._log(f"❌ Error procesando caso {id_orden}: {e}", level="error")
            self._actualizar_stats(error=True)
            # Intentar marcar error crítico
            try:
                self.api_service.marcar_error_critico(caso.get('idOrden'))
            except Exception:
                pass
            # Si el error es de sesión/navegador, reinicializar
            error_msg = str(e).lower()
            if any(kw in error_msg for kw in ['session', 'browser', 'closed', 'disconnected', 'page']):
                self._formulario_listo = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _actualizar_stats(self, exitoso: bool = False, error: bool = False):
        self.stats['procesados'] += 1
        if exitoso:
            self.stats['exitosos'] += 1
        if error:
            self.stats['errores'] += 1
        if self.on_stats_update:
            self.on_stats_update(self.stats)

    def _cleanup(self):
        """Limpieza al finalizar"""
        if self.playwright_service:
            try:
                self.playwright_service.cerrar_navegador()
            except Exception:
                pass

    def _log(self, mensaje: str, level: str = "info"):
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        linea = f"[{ts}] {mensaje}"
        print(linea)
        if self.ui_callback:
            self.ui_callback(linea)
