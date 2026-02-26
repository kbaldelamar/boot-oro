"""
Panel de Worker Automatización Laboratorio
Muestra tabla de pacientes de laboratorio con filtros de búsqueda y controles de worker
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.laboratorio.services.laboratorio_service import LaboratorioService
from modules.laboratorio.services.laboratorio_worker import LaboratorioWorker


class LaboratorioPanel(ttk.Frame):
    """Panel para visualizar y trabajar con pacientes de laboratorio"""
    
    def __init__(self, parent, config):
        """
        Args:
            parent: Widget padre
            config: Configuración
        """
        super().__init__(parent)
        self.config = config
        self.global_config = Config()
        self.api_service = LaboratorioService()
        self.refresh_id = None
        self.estado_filtro = tk.StringVar(value="Pendiente")  # Inicializar con TEXTO, no valor
        self.documento_filtro = tk.StringVar(value="")
        self.nombre_filtro = tk.StringVar(value="")
        
        # Worker de automatización
        self.worker: Optional[LaboratorioWorker] = None
        
        self._create_widgets()
        self._start_auto_refresh()
    
    def _create_widgets(self):
        """Crea todos los widgets del panel"""
        # =========================
        # SECCIÓN DE FILTROS
        # =========================
        filtros_frame = ttk.LabelFrame(self, text="Filtros de Búsqueda", padding=10)
        filtros_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Fila de filtros
        filtros_row = ttk.Frame(filtros_frame)
        filtros_row.pack(fill=tk.X)
        
        # Filtro por estado
        ttk.Label(filtros_row, text="Estado:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        estados = [
            ("Todos", ""),
            ("Pendiente", "0"),
            ("Exitoso", "1"),
            ("En proceso", "3"),
            ("Datos inválidos", "4"),
            ("PDF no encontrado", "5"),
            ("Solicitud activa", "6"),
            ("Error no clasificado", "11"),
            ("Sesión perdida", "12"),
            ("Timeout", "13"),
            ("Elemento no encontrado", "14"),
            ("Elemento obsoleto", "15"),
            ("Error de conexión", "16"),
            ("Otro error", "17"),
            ("Error de permisos", "18"),
            ("Resultado indeterminado", "19"),
            ("Teléfono inválido", "20")
        ]
        combo_estado = ttk.Combobox(
            filtros_row,
            textvariable=self.estado_filtro,
            values=[e[0] for e in estados],
            state='readonly',
            width=20
        )
        combo_estado.current(1)  # Pendiente por defecto
        combo_estado.pack(side=tk.LEFT, padx=5)
        # Mapeo de nombres a valores
        self.estado_map = {e[0]: e[1] for e in estados}
        combo_estado.bind('<<ComboboxSelected>>', lambda e: self._cargar_pacientes())
        
        # Filtro por documento
        ttk.Label(filtros_row, text="Documento:", font=('Arial', 9)).pack(side=tk.LEFT, padx=(15, 5))
        entry_documento = ttk.Entry(filtros_row, textvariable=self.documento_filtro, width=15)
        entry_documento.pack(side=tk.LEFT, padx=5)
        entry_documento.bind('<Return>', lambda e: self._cargar_pacientes())
        
        # Filtro por nombre
        ttk.Label(filtros_row, text="Nombre:", font=('Arial', 9)).pack(side=tk.LEFT, padx=(15, 5))
        entry_nombre = ttk.Entry(filtros_row, textvariable=self.nombre_filtro, width=20)
        entry_nombre.pack(side=tk.LEFT, padx=5)
        entry_nombre.bind('<Return>', lambda e: self._cargar_pacientes())
        
        # Botón buscar
        ttk.Button(
            filtros_row,
            text="🔍 Buscar",
            command=self._cargar_pacientes,
            width=12
        ).pack(side=tk.LEFT, padx=10)
        
        # Botón limpiar filtros
        ttk.Button(
            filtros_row,
            text="🗑️ Limpiar",
            command=self._limpiar_filtros,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # =========================
        # CONTROLES DEL WORKER
        # =========================
        worker_frame = ttk.LabelFrame(self, text="Control de Automatización", padding=10)
        worker_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        worker_row = ttk.Frame(worker_frame)
        worker_row.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(
            worker_row,
            text="▶️ Iniciar Worker",
            command=self._iniciar_worker,
            width=18
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(
            worker_row,
            text="⏸️ Pausar",
            command=self._pausar_worker,
            state='disabled',
            width=12
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            worker_row,
            text="⏹️ Detener",
            command=self._detener_worker,
            state='disabled',
            width=12
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(worker_row, orient='vertical').pack(side=tk.LEFT, fill='y', padx=10, pady=2)
        
        self.reprogramar_btn = ttk.Button(
            worker_row,
            text="🔄 Reprogramar Seleccionados",
            command=self._reprogramar_seleccionados,
            width=22
        )
        self.reprogramar_btn.pack(side=tk.LEFT, padx=5)
        
        # Estado del worker
        self.worker_status_label = ttk.Label(
            worker_row,
            text="Estado: Detenido",
            font=('Arial', 9),
            foreground='gray'
        )
        self.worker_status_label.pack(side=tk.LEFT, padx=10)
        
        # Estadísticas del worker
        self.stats_label = ttk.Label(
            worker_row,
            text="📊 Procesados: 0 | ✅ Exitosos: 0 | ❌ Errores: 0",
            font=('Arial', 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        # =========================
        # TABLA DE PACIENTES
        # =========================
        table_frame = ttk.LabelFrame(self, text="Pacientes de Laboratorio", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Toolbar de tabla
        toolbar = ttk.Frame(table_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            toolbar,
            text="↻ Actualizar",
            command=self._cargar_pacientes,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="☑️ Selec. Todo",
            command=self._seleccionar_todo,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        self.count_label = ttk.Label(toolbar, text="Total: 0", font=('Arial', 9, 'bold'))
        self.count_label.pack(side=tk.LEFT, padx=10)
        
        # Indicador de auto-refresh
        ttk.Label(toolbar, text="🔄 Auto-refresh: 60s", font=('Arial', 8), foreground='green').pack(side=tk.RIGHT, padx=10)
        
        # Crear tabla
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient="vertical")
        hsb = ttk.Scrollbar(table_container, orient="horizontal")
        
        columns = (
            "facturaEvento", "idOrdenProcedimiento", "tipoIdentificacion", "identificacion", 
            "nombre", "diagnostico", "telefono", "municipio", 
            "fechaFacturaEvento", "estado"
        )
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=15
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configurar columnas
        self.tree.heading("facturaEvento", text="ID Factura")
        self.tree.heading("idOrdenProcedimiento", text="ID Orden")
        self.tree.heading("tipoIdentificacion", text="Tipo Doc")
        self.tree.heading("identificacion", text="Documento")
        self.tree.heading("nombre", text="Paciente")
        self.tree.heading("diagnostico", text="Diagnóstico")
        self.tree.heading("telefono", text="Teléfono")
        self.tree.heading("municipio", text="Municipio")
        self.tree.heading("fechaFacturaEvento", text="Fecha")
        self.tree.heading("estado", text="Estado")
        
        self.tree.column("facturaEvento", width=80, anchor=tk.CENTER)
        self.tree.column("idOrdenProcedimiento", width=80, anchor=tk.CENTER)
        self.tree.column("tipoIdentificacion", width=80, anchor=tk.CENTER)
        self.tree.column("identificacion", width=100, anchor=tk.CENTER)
        self.tree.column("nombre", width=250)
        self.tree.column("diagnostico", width=80, anchor=tk.CENTER)
        self.tree.column("telefono", width=100, anchor=tk.CENTER)
        self.tree.column("municipio", width=120)
        self.tree.column("fechaFacturaEvento", width=100, anchor=tk.CENTER)
        self.tree.column("estado", width=80, anchor=tk.CENTER)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # =========================
        # ÁREA DE LOGS
        # =========================
        log_frame = ttk.LabelFrame(self, text="Logs en Vivo", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Toolbar de logs
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X)
        
        ttk.Button(
            log_toolbar,
            text="🗑️ Limpiar Log",
            command=self._limpiar_log,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Text area para logs
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#cccccc'
        )
        self.log_text.pack(fill=tk.X, pady=5)
        
        # Configurar tags de colores
        self.log_text.tag_configure('info', foreground='#4fc3f7')
        self.log_text.tag_configure('success', foreground='#81c784')
        self.log_text.tag_configure('error', foreground='#ef5350')
        self.log_text.tag_configure('warning', foreground='#ffb74d')
        
        # Cargar datos iniciales
        self._cargar_pacientes()
        self._agregar_log("Sistema de laboratorio iniciado. Esperando órdenes...")
    
    def _limpiar_filtros(self):
        """Limpia todos los filtros"""
        self.documento_filtro.set("")
        self.nombre_filtro.set("")
        self.estado_filtro.set("0")
        self._cargar_pacientes()
    
    def _cargar_pacientes(self):
        """Carga los pacientes desde la API"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Obtener valor de estado
        estado_texto = self.estado_filtro.get()
        print(f"\n[DEBUG PANEL] ===== CARGANDO PACIENTES =====")
        print(f"[DEBUG PANEL] estado_texto del combo: '{estado_texto}'")
        
        estado_valor = self.estado_map.get(estado_texto, "0")
        print(f"[DEBUG PANEL] estado_valor mapeado: '{estado_valor}'")
        
        # Si es "Todos", no filtramos por estado
        if estado_valor == "":
            estado_valor = None
            print(f"[DEBUG PANEL] Estado es 'Todos' -> estado_valor = None")
        else:
            estado_valor = int(estado_valor)
            print(f"[DEBUG PANEL] Estado convertido a int: {estado_valor}")
        
        # Log de parámetros que se enviarán
        print(f"[DEBUG PANEL] Parámetros para API:")
        print(f"  - estado: {estado_valor}")
        print(f"  - documento: {self.documento_filtro.get() or None}")
        print(f"  - nombre: {self.nombre_filtro.get() or None}")
        
        # Obtener pacientes
        pacientes = self.api_service.obtener_pacientes(
            estado=estado_valor,  # Pasar None cuando es "Todos", valor específico en los demás casos
            documento=self.documento_filtro.get() or None,
            nombre=self.nombre_filtro.get() or None
        )
        
        print(f"[DEBUG PANEL] Pacientes recibidos: {len(pacientes) if isinstance(pacientes, list) else 'ERROR'}")
        print(f"[DEBUG PANEL] ===========================\n")
        
        # Validar que sea una lista de diccionarios
        if not isinstance(pacientes, list):
            self._agregar_log(f"⚠️ Respuesta inesperada: {type(pacientes)}", 'warning')
            pacientes = []
        
        # Poblar tabla
        for paciente in pacientes:
            if not isinstance(paciente, dict):
                continue
            estado_texto = self._get_estado_texto(paciente.get('estado', 0))
            self.tree.insert('', 'end', values=(
                paciente.get('facturaEvento', ''),
                paciente.get('idOrdenProcedimiento', ''),
                paciente.get('tipoIdentificacion', ''),
                paciente.get('identificacion', ''),
                paciente.get('nombre', '').strip(),
                paciente.get('diagnostico', ''),
                paciente.get('telefono', ''),
                paciente.get('municipio', ''),
                paciente.get('fechaFacturaEvento', ''),
                estado_texto
            ))
        
        # Actualizar contador con lo que realmente se cargó
        total = len(self.tree.get_children())
        self.count_label.config(text=f"Total: {total}")
        self._agregar_log(f"✅ {total} pacientes cargados")
    
    def _get_estado_texto(self, estado: int) -> str:
        """Convierte el código de estado a texto"""
        estados = {
            0: "Pendiente",
            1: "Exitoso",
            2: "En proceso",
            4: "Doc incorrecto",
            5: "PDF no encontrado",
            6: "Solicitud activa",
            11: "Error no clasificado",
            12: "Sesión perdida",
            13: "Timeout",
            14: "Elemento no encontrado",
            15: "Elemento obsoleto",
            16: "Error de conexión",
            18: "Error de permisos"
        }
        return estados.get(estado, f"Estado {estado}")
    
    def _seleccionar_todo(self):
        """Selecciona o deselecciona todos los registros"""
        items = self.tree.get_children()
        if not items:
            return
        
        seleccion_actual = self.tree.selection()
        if len(seleccion_actual) == len(items):
            self.tree.selection_remove(*items)
        else:
            self.tree.selection_set(items)
    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh de la tabla"""
        self._auto_refresh()
    
    def _auto_refresh(self):
        """Ejecuta el refresh automático cada 60 segundos"""
        self._cargar_pacientes()
        self.refresh_id = self.after(60000, self._auto_refresh)
    
    def _stop_auto_refresh(self):
        """Detiene el auto-refresh"""
        if self.refresh_id:
            self.after_cancel(self.refresh_id)
            self.refresh_id = None
    
    def _agregar_log(self, mensaje: str, tipo: str = 'info'):
        """Agrega un mensaje al área de logs"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {mensaje}\n", tipo)
        self.log_text.see(tk.END)
    
    def _limpiar_log(self):
        """Limpia el área de logs"""
        self.log_text.delete(1.0, tk.END)
    
    # =========================
    # MÉTODOS DEL WORKER
    # =========================
    
    def _iniciar_worker(self):
        """Inicia el worker de automatización"""
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Worker Activo", "El worker ya está en ejecución")
            return
        
        self._agregar_log("🚀 Iniciando worker de automatización...", 'info')
        
        # Crear worker con callback de logs
        self.worker = LaboratorioWorker(ui_callback=self._ui_log_callback)
        self.worker.on_stats_update = self._actualizar_stats
        self.worker.start()
        
        # Actualizar UI
        self.start_btn.config(state='disabled')
        self.pause_btn.config(state='normal', text="⏸️ Pausar")
        self.stop_btn.config(state='normal')
        self.worker_status_label.config(text="Estado: Ejecutando", foreground='green')
        
        self._agregar_log("✅ Worker iniciado!", 'success')
    
    def _pausar_worker(self):
        """Pausa o reanuda el worker"""
        if not self.worker or not self.worker.is_alive():
            return
        
        if self.worker.paused:
            self.worker.reanudar()
            self.pause_btn.config(text="⏸️ Pausar")
            self.worker_status_label.config(text="Estado: Ejecutando", foreground='green')
            self._agregar_log("▶️ Worker reanudado", 'info')
        else:
            self.worker.pausar()
            self.pause_btn.config(text="▶️ Reanudar")
            self.worker_status_label.config(text="Estado: Pausado", foreground='orange')
            self._agregar_log("⏸️ Worker pausado", 'warning')
    
    def _detener_worker(self):
        """Detiene el worker"""
        if not self.worker:
            return
        
        self._agregar_log("⏹️ Deteniendo worker...", 'warning')
        self.worker.detener()
                # Detener el auto-refresh de la tabla
        self._stop_auto_refresh()
                # Actualizar UI inmediatamente sin esperar al thread
        self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️ Pausar")
        self.stop_btn.config(state='disabled')
        self.worker_status_label.config(text="Estado: Detenido", foreground='gray')
        self.worker = None
        
        self._agregar_log("⏹️ Worker detenido", 'info')
    
    def _reprogramar_seleccionados(self):
        """Reprograma (resetea a pendiente) los pacientes seleccionados"""
        seleccionados = self.tree.selection()
        if not seleccionados:
            messagebox.showwarning("Sin selección", "Seleccione al menos un paciente")
            return
        
        if not messagebox.askyesno("Confirmar", f"¿Reprogramar {len(seleccionados)} pacientes a estado Pendiente?"):
            return
        
        for item in seleccionados:
            valores = self.tree.item(item, 'values')
            id_orden_proc = valores[1]  # idOrdenProcedimiento en la segunda columna
            
            try:
                self.api_service.actualizar_item_orden_procedimiento(
                    id_orden_procedimiento=int(id_orden_proc),
                    estado_dynamicos=0  # Pendiente
                )
                self._agregar_log(f"🔄 Orden {id_orden_proc} reprogramada", 'info')
            except Exception as e:
                self._agregar_log(f"❌ Error reprogramando {id_orden_proc}: {e}", 'error')
        
        self._cargar_pacientes()
        self._agregar_log(f"✅ {len(seleccionados)} pacientes reprogramados", 'success')
    
    def _ui_log_callback(self, message: str):
        """Callback para logs del worker - recibe string ya formateado por el logger"""
        # El mensaje ya viene con timestamp del logger, insertarlo directo
        self.after(0, lambda: self._insertar_log_raw(message))
    
    def _insertar_log_raw(self, mensaje: str):
        """Inserta un mensaje ya formateado directamente en el log"""
        self.log_text.insert(tk.END, f"{mensaje}\n")
        self.log_text.see(tk.END)
    
    def _actualizar_stats(self, stats: dict):
        """Actualiza las estadísticas en la UI"""
        def update():
            procesados = stats.get('procesados', 0)
            exitosos = stats.get('exitosos', 0)
            errores = stats.get('errores', 0)
            self.stats_label.config(
                text=f"📊 Procesados: {procesados} | ✅ Exitosos: {exitosos} | ❌ Errores: {errores}"
            )
        self.after(0, update)
    
    def destroy(self):
        """Limpieza al destruir el panel"""
        self._stop_auto_refresh()
        
        # Detener worker si está activo
        if self.worker and self.worker.is_alive():
            self.worker.detener()
        
        super().destroy()
