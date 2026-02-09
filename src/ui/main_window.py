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


class MainWindow:
    """
    Ventana principal de la aplicación con sistema de navegación por menú.
    """
    
    def __init__(self):
        """Inicializa la ventana principal"""
        self.root = tk.Tk()
        self.config = Config()
        self.current_panel: Optional[tk.Frame] = None
        self.panels_registry: Dict[str, Type] = {}
        
        self._setup_window()
        self._create_menu()
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
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Configuración", command=self._show_config)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self._on_closing)
        
        # Menú Procesos
        procesos_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Procesos", menu=procesos_menu)
        procesos_menu.add_command(
            label="Autorizar - Anexo 3",
            command=lambda: self._open_panel('autorizar_anexo3')
        )
        procesos_menu.add_separator()
        procesos_menu.add_command(
            label="Worker Automatización",
            command=lambda: self._open_panel('worker_automatizacion')
        )
        # Aquí se pueden agregar más opciones de menú para otros paneles
        
        # Menú Ayuda
        ayuda_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
        ayuda_menu.add_command(label="Acerca de", command=self._show_about)
    
    def _create_main_container(self):
        """Crea el contenedor principal para los paneles"""
        # Frame principal
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Barra de estado
        self.status_bar = ttk.Label(
            self.root,
            text=f"Conectado - {self.config.sede_ips_nombre}",
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
        self.status_bar.config(text=f"Panel activo: {panel_name}")
    
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
