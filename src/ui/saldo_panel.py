"""
Panel de recarga de saldo.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import Config
from services.license_service import LicenseService
from services.topup_service import TopupService
from utils.logger import AdvancedLogger


class RecargaSaldoPanel(ttk.Frame):
    """Panel para cargar saldo mediante archivo firmado"""

    def __init__(self, parent, config: Config):
        super().__init__(parent)
        self.config = config
        self.logger = AdvancedLogger()
        
        base_url = self.config.api_url_programacion_base or 'http://localhost:5000'
        self.license_service = LicenseService(base_url=base_url)
        self.topup_service = TopupService(
            base_url=base_url,
            public_key_path=self.config.recarga_public_key_path
        )
        self.logger.info('RecargaSaldo', f'Panel inicializado - base_url: {base_url}')
        self.logger.info('RecargaSaldo', f'Public key path: {self.config.recarga_public_key_path}')

        self._create_widgets()
        self._refresh_saldo()

    def _create_widgets(self):
        title = ttk.Label(self, text="Recarga de saldo", font=('Arial', 16, 'bold'))
        title.pack(pady=10)

        # Frame para información del saldo
        info_frame = ttk.LabelFrame(self, text="Información de Saldo", padding=10)
        info_frame.pack(pady=10, padx=20, fill=tk.X)

        self.saldo_label = ttk.Label(info_frame, text="Saldo actual: --", font=('Arial', 12, 'bold'))
        self.saldo_label.pack(pady=5)
        
        self.valor_caso_label = ttk.Label(info_frame, text="Valor por caso: --", font=('Arial', 10))
        self.valor_caso_label.pack(pady=2)
        
        self.casos_exitosos_label = ttk.Label(info_frame, text="Casos exitosos: --", font=('Arial', 10))
        self.casos_exitosos_label.pack(pady=2)

        info = ttk.Label(
            self,
            text="Seleccione un archivo de recarga firmado para aplicar saldo",
            font=('Arial', 10)
        )
        info.pack(pady=5)

        ttk.Button(
            self,
            text="Cargar archivo de recarga",
            command=self._cargar_archivo,
            width=28
        ).pack(pady=10)

        self.result_label = ttk.Label(self, text="", font=('Arial', 10), foreground='gray')
        self.result_label.pack(pady=5)

    def _refresh_saldo(self):
        info = self.license_service.obtener_saldo()
        saldo = info.get("saldo_robot") if info.get("success") else None
        valor_caso = info.get("valor_caso") if info.get("success") else None
        casos_exitosos = info.get("numero_casos_exitosos") if info.get("success") else None
        
        texto_saldo = self._formatear_saldo(saldo)
        self.saldo_label.config(text=f"Saldo actual: {texto_saldo}")
        
        # Actualizar valor por caso
        if valor_caso is not None:
            try:
                texto_valor = f"{float(valor_caso):,.0f}"
            except (TypeError, ValueError):
                texto_valor = str(valor_caso)
        else:
            texto_valor = "--"
        self.valor_caso_label.config(text=f"Valor por caso: {texto_valor}")
        
        # Actualizar casos exitosos
        if casos_exitosos is not None:
            texto_casos = str(casos_exitosos)
        else:
            texto_casos = "--"
        self.casos_exitosos_label.config(text=f"Casos exitosos: {texto_casos}")

        app = self._get_app()
        if app:
            app.actualizar_saldo_ui(saldo)

    def _formatear_saldo(self, saldo):
        if saldo is None:
            return "--"
        try:
            return f"{float(saldo):,.0f}"
        except (TypeError, ValueError):
            return str(saldo)

    def _cargar_archivo(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de recarga",
            filetypes=[("Archivo JSON", "*.json"), ("Todos", "*.*")]
        )
        if not file_path:
            self.logger.info('RecargaSaldo', 'Carga cancelada por usuario')
            return

        self.logger.info('RecargaSaldo', f'Archivo seleccionado: {file_path}')
        
        # Leer contenido para diagnostico
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            self.logger.info('RecargaSaldo', f'Contenido archivo ({len(contenido)} bytes): {contenido[:200]}...')
        except Exception as e:
            self.logger.error('RecargaSaldo', f'Error leyendo archivo: {e}', e)

        self.logger.info('RecargaSaldo', f'IPS permitidas: {self.config.ips_nombres_permitidos}')
        
        result = self.topup_service.recargar_desde_archivo(
            file_path,
            self.config.ips_nombres_permitidos
        )
        
        self.logger.info('RecargaSaldo', f'Resultado recarga: {result}')

        if result.get("success"):
            self.logger.success('RecargaSaldo', 'Recarga aplicada exitosamente')
            self.result_label.config(text="Recarga aplicada", foreground='green')
            self._refresh_saldo()
        else:
            msg = result.get("message", "Error en recarga")
            err = result.get("error", "")
            self.logger.error('RecargaSaldo', f'Recarga fallida - mensaje: {msg}, error: {err}')
            self.result_label.config(
                text=msg,
                foreground='red'
            )

    def _get_app(self):
        root = self.winfo_toplevel()
        return getattr(root, 'app', None)
