"""
Ventana principal de la aplicación con menú para navegar entre paneles.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Type
import sys
from pathlib import Path

# Agregar el directorio src al path para importaciones
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.license_service import LicenseService
from ui.saldo_panel import RecargaSaldoPanel
from ui.empresas_panel import EmpresasCasosBootPanel
from ui.procedimientos_panel import ProcedimientosBootPanel


class MainWindow:
    """
    Ventana principal de la aplicación con sistema de navegación por menú.
    """
    
    def __init__(self):
        """Inicializa la ventana principal"""
        self.root = tk.Tk()
        self.root.app = self
        self.config = Config()
        self.saldo_robot = None
        self.saldo_agotado = False
        self.nombre_licencia = ""
        self.license_service: Optional[LicenseService] = None
        self.current_panel: Optional[tk.Frame] = None
        self.panels_registry: Dict[str, Type] = {}
        
        self._setup_window()
        self._create_menu()
        self._verificar_licencia()
        self._create_main_container()
        self._register_panels()
    
    def _setup_window(self):
        """Configura las propiedades de la ventana principal"""
        self.root.title(f"Sistema de Automatización - {self.config.nombre_ips}")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Centrar la ventana en la pantalla
        self._center_window()
        
        # Configurar el estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')
    
    def _center_window(self):
        """Centra la ventana en la pantalla"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _create_menu(self):
        """Crea la barra de menú principal"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Configuración", command=self._show_config)
        file_menu.add_command(label="Crear empresa", command=lambda: self._open_panel('empresas_casos_boot'))
        file_menu.add_command(label="Procedimientos", command=lambda: self._open_panel('procedimientos_boot'))
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self._on_closing)
        
        # Menú Procesos
        self.procesos_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Procesos", menu=self.procesos_menu)
        self.procesos_menu.add_command(
            label="Autorizar - Anexo 3",
            command=lambda: self._open_panel('autorizar_anexo3')
        )
        self.procesos_menu.add_separator()
        self.procesos_menu.add_command(
            label="Worker Automatización",
            command=lambda: self._open_panel('worker_automatizacion')
        )
        # Aquí se pueden agregar más opciones de menú para otros paneles
        
        # Menú Ayuda
        ayuda_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
        ayuda_menu.add_command(label="Acerca de", command=self._show_about)

        # Menú Administración
        admin_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Administración", menu=admin_menu)
        admin_menu.add_command(
            label="Cargar saldo",
            command=lambda: self._open_panel('recarga_saldo')
        )
    
    def _create_main_container(self):
        """Crea el contenedor principal para los paneles"""
        # Frame principal
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Barra de estado
        saldo_texto = self._formatear_saldo()
        self.status_bar = ttk.Label(
            self.root,
            text=f"Conectado - {self.config.sede_ips_nombre} | Saldo: {saldo_texto}",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Mostrar panel de bienvenida por defecto
        self._show_welcome_panel()
    
    def _register_panels(self):
        """Registra todos los paneles disponibles"""
        try:
            from modules.autorizar_anexo3 import AutorizarAnexo3Panel, ProgramacionPanel
            self.panels_registry['autorizar_anexo3'] = AutorizarAnexo3Panel
            self.panels_registry['worker_automatizacion'] = ProgramacionPanel
            self.panels_registry['recarga_saldo'] = RecargaSaldoPanel
            self.panels_registry['empresas_casos_boot'] = EmpresasCasosBootPanel
            self.panels_registry['procedimientos_boot'] = ProcedimientosBootPanel
        except ImportError as e:
            print(f"Advertencia: No se pudo cargar el panel AutorizarAnexo3: {e}")
    
    def _show_welcome_panel(self):
        """Muestra el panel de bienvenida"""
        self._clear_current_panel()
        
        welcome_frame = ttk.Frame(self.main_frame)
        welcome_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(
            welcome_frame,
            text=f"Bienvenido al Sistema de Automatización",
            font=('Arial', 24, 'bold')
        )
        title_label.pack(pady=50)
        
        # Información de la IPS
        info_frame = ttk.LabelFrame(welcome_frame, text="Información de la Institución", padding=20)
        info_frame.pack(pady=20, padx=50, fill=tk.X)
        
        ttk.Label(info_frame, text=f"Nombre: {self.config.nombre_ips}", font=('Arial', 12)).pack(anchor=tk.W, pady=5)
        ttk.Label(info_frame, text=f"NIT: {self.config.nit_ips}", font=('Arial', 12)).pack(anchor=tk.W, pady=5)
        ttk.Label(info_frame, text=f"Sede: {self.config.sede_ips_nombre}", font=('Arial', 12)).pack(anchor=tk.W, pady=5)
        self.saldo_info_label = ttk.Label(
            info_frame,
            text=f"Saldo robot: {self._formatear_saldo()}",
            font=('Arial', 12)
        )
        self.saldo_info_label.pack(anchor=tk.W, pady=5)
        
        # Instrucciones
        instructions = ttk.Label(
            welcome_frame,
            text="Seleccione una opción del menú 'Procesos' para comenzar",
            font=('Arial', 11),
            foreground='gray'
        )
        instructions.pack(pady=30)
        
        self.current_panel = welcome_frame
    
    def _clear_current_panel(self):
        """Limpia el panel actual"""
        if self.current_panel:
            self.current_panel.destroy()
            self.current_panel = None
    
    def _open_panel(self, panel_name: str):
        """
        Abre un panel específico.
        
        Args:
            panel_name: Nombre del panel a abrir
        """
        if self.saldo_agotado and panel_name != 'recarga_saldo':
            messagebox.showwarning(
                "Saldo agotado",
                "El saldo del robot se agotó. No es posible abrir paneles."
            )
            return

        if panel_name not in self.panels_registry:
            messagebox.showerror(
                "Error",
                f"El panel '{panel_name}' no está disponible."
            )
            return
        
        self._clear_current_panel()
        
        # Crear instancia del panel
        panel_class = self.panels_registry[panel_name]
        self.current_panel = panel_class(self.main_frame, self.config)
        self.current_panel.pack(fill=tk.BOTH, expand=True)
        
        # Actualizar barra de estado
        self.status_bar.config(
            text=f"Panel activo: {panel_name} | Saldo: {self._formatear_saldo()}"
        )

    def _formatear_saldo(self) -> str:
        if self.saldo_robot is None:
            return "--"
        try:
            return f"{float(self.saldo_robot):,.0f}"
        except (TypeError, ValueError):
            return str(self.saldo_robot)

    def actualizar_saldo_ui(self, saldo):
        self.saldo_robot = saldo
        saldo_texto = self._formatear_saldo()
        self.status_bar.config(
            text=f"Conectado - {self.config.sede_ips_nombre} | Saldo: {saldo_texto}"
        )
        if hasattr(self, 'saldo_info_label'):
            try:
                if self.saldo_info_label.winfo_exists():
                    self.saldo_info_label.config(text=f"Saldo robot: {saldo_texto}")
            except Exception:
                pass
        try:
            if saldo is not None and float(saldo) > 0:
                self.saldo_agotado = False
                if hasattr(self, 'procesos_menu'):
                    self.procesos_menu.entryconfig(0, state=tk.NORMAL)
                    self.procesos_menu.entryconfig(2, state=tk.NORMAL)
        except (TypeError, ValueError):
            pass

    def _bloquear_menus(self):
        if hasattr(self, 'procesos_menu'):
            self.procesos_menu.entryconfig(0, state=tk.DISABLED)
            self.procesos_menu.entryconfig(2, state=tk.DISABLED)

    def _verificar_licencia(self):
        from utils.logger import AdvancedLogger
        self._startup_logger = AdvancedLogger()

        try:
            base_url = self.config.api_url_programacion_base or 'http://localhost:5000'
            self.license_service = LicenseService(base_url=base_url)
            self._startup_logger.info('Licencia', f'LicenseService inicializado - base_url: {base_url}')
        except ImportError as exc:
            self._startup_logger.error('Licencia', f'Error importando cryptography: {exc}', exc)
            messagebox.showerror("Licencia", str(exc))
            raise SystemExit(1)

        saldo_url = f"{self.license_service.base_url}/ips-saldos"
        self._startup_logger.info('Licencia', f'Consultando saldo en: {saldo_url}')

        info = self.license_service.obtener_saldo()

        self._startup_logger.info('Licencia', f'Respuesta saldo - success: {info.get("success")}')
        self._startup_logger.info('Licencia', f'Respuesta saldo - message: {info.get("message")}')
        self._startup_logger.info('Licencia', f'Respuesta saldo - saldo_robot: {info.get("saldo_robot")}')
        self._startup_logger.info('Licencia', f'Respuesta saldo - nombre_encriptado: {(info.get("nombre_encriptado") or "")[:30]}...')
        self._startup_logger.info('Licencia', f'Respuesta saldo - nombre_desencriptado: {info.get("nombre_desencriptado")}')
        if info.get("error"):
            self._startup_logger.error('Licencia', f'Error en consulta: {info.get("error")}')

        if not info.get("success"):
            self._startup_logger.warning('Licencia', f'Validación fallida: {info.get("message", "")}')
            messagebox.showerror(
                "Licencia",
                f"No se pudo validar licencia. {info.get('message', '')}"
            )
            self.saldo_agotado = True
            self._bloquear_menus()
            return

        self.saldo_robot = info.get("saldo_robot")
        self.nombre_licencia = info.get("nombre_desencriptado") or ""

        permitidos = self.config.ips_nombres_permitidos
        es_autorizado = self.license_service.nombre_autorizado(
            self.nombre_licencia,
            permitidos
        )
        self._startup_logger.info('Licencia', f'Nombre desencriptado: "{self.nombre_licencia}"')
        self._startup_logger.info('Licencia', f'IPS permitidas: {permitidos}')
        self._startup_logger.info('Licencia', f'Autorizado: {es_autorizado}')

        if not es_autorizado:
            self._startup_logger.error('Licencia', 'IPS NO autorizada - cerrando app')
            messagebox.showerror(
                "Licencia",
                "IPS no autorizada para usar esta aplicacion."
            )
            self.root.destroy()
            raise SystemExit(1)

        self._startup_logger.info('Licencia', f'Saldo robot: {self.saldo_robot}')

        if self.saldo_robot is None or float(self.saldo_robot) <= 0:
            self.saldo_agotado = True
            self._bloquear_menus()
            self._startup_logger.warning('Licencia', 'Saldo agotado - menús bloqueados')
            messagebox.showwarning(
                "Saldo agotado",
                "El saldo del robot se agotó."
            )
        else:
            self._startup_logger.success('Licencia', f'Licencia OK - Saldo: {self.saldo_robot}')
    
    def _show_config(self):
        """Muestra la configuración de la aplicación"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configuración")
        config_window.geometry("600x400")
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Crear notebook para pestañas
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña de Endpoints
        endpoints_frame = ttk.Frame(notebook)
        notebook.add(endpoints_frame, text="Endpoints")
        
        ttk.Label(endpoints_frame, text="Configuración de Endpoints API", font=('Arial', 12, 'bold')).pack(pady=10)
        
        info_text = tk.Text(endpoints_frame, height=15, width=70)
        info_text.pack(padx=10, pady=10)
        info_text.insert('1.0', f"""
Órdenes HC: {self.config.api_url_ordenes_hc}
Programación: {self.config.api_url_programacion}
Programación Base: {self.config.api_url_programacion_base}

Para modificar estos valores, edite el archivo endpoint.env
        """)
        info_text.config(state='disabled')
        
        ttk.Button(
            config_window,
            text="Cerrar",
            command=config_window.destroy
        ).pack(pady=10)
    
    def _show_about(self):
        """Muestra información sobre la aplicación"""
        messagebox.showinfo(
            "Acerca de",
            f"Sistema de Automatización\n\n"
            f"Versión: 1.0.0\n"
            f"Institución: {self.config.nombre_ips}\n\n"
            f"© 2026 - Todos los derechos reservados"
        )
    
    def _on_closing(self):
        """Maneja el cierre de la aplicación"""
        if messagebox.askokcancel("Salir", "¿Está seguro que desea salir?"):
            self.root.destroy()
    
    def run(self):
        """Inicia el loop principal de la aplicación"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
