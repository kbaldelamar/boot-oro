"""
Panel de Finalizar Casos Laboratorio.
Muestra tabla de casos con filtros de búsqueda, auto-refresh cada 60 s
y controles de worker de automatización.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.finalizar_casos.services.finalizar_casos_service import FinalizarCasosService
from modules.finalizar_casos.services.finalizar_casos_worker import FinalizarCasosWorker


class FinalizarCasosPanel(ttk.Frame):
    """Panel para visualizar y trabajar con casos de Finalizar Laboratorio"""

    def __init__(self, parent, config):
        """
        Args:
            parent: Widget padre
            config: Configuración (instancia de Config)
        """
        super().__init__(parent)
        self.config = config
        self.global_config = Config()
        self.api_service = FinalizarCasosService()
        self.refresh_id = None

        # Filtros
        self.caso_filtro = tk.StringVar(value="")
        self.id_orden_filtro = tk.StringVar(value="")

        # Worker
        self.worker: Optional[FinalizarCasosWorker] = None

        self._create_widgets()
        self._start_auto_refresh()

    # =================================================================
    # WIDGETS
    # =================================================================

    def _create_widgets(self):
        """Crea todos los widgets del panel"""

        # -------------- FILTROS --------------
        filtros_frame = ttk.LabelFrame(self, text="Filtros de Búsqueda", padding=10)
        filtros_frame.pack(fill=tk.X, padx=10, pady=10)

        filtros_row = ttk.Frame(filtros_frame)
        filtros_row.pack(fill=tk.X)

        ttk.Label(filtros_row, text="Caso / Radicado:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        entry_caso = ttk.Entry(filtros_row, textvariable=self.caso_filtro, width=30)
        entry_caso.pack(side=tk.LEFT, padx=5)
        entry_caso.bind('<Return>', lambda e: self._cargar_casos())

        ttk.Label(filtros_row, text="ID Orden:", font=('Arial', 9)).pack(side=tk.LEFT, padx=(15, 5))
        entry_id_orden = ttk.Entry(filtros_row, textvariable=self.id_orden_filtro, width=12)
        entry_id_orden.pack(side=tk.LEFT, padx=5)
        entry_id_orden.bind('<Return>', lambda e: self._cargar_casos())

        ttk.Button(
            filtros_row, text="🔍 Buscar",
            command=self._cargar_casos, width=12
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            filtros_row, text="🗑️ Limpiar",
            command=self._limpiar_filtros, width=10
        ).pack(side=tk.LEFT, padx=5)

        # -------------- CONTROLES WORKER --------------
        worker_frame = ttk.LabelFrame(self, text="Control de Automatización", padding=10)
        worker_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        worker_row = ttk.Frame(worker_frame)
        worker_row.pack(fill=tk.X)

        self.start_btn = ttk.Button(
            worker_row, text="▶️ Iniciar Worker",
            command=self._iniciar_worker, width=18
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = ttk.Button(
            worker_row, text="⏸️ Pausar",
            command=self._pausar_worker, state='disabled', width=12
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(
            worker_row, text="⏹️ Detener",
            command=self._detener_worker, state='disabled', width=12
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Separator(worker_row, orient='vertical').pack(side=tk.LEFT, fill='y', padx=10, pady=2)

        self.reprogramar_btn = ttk.Button(
            worker_row, text="🔄 Reprogramar Seleccionados",
            command=self._reprogramar_seleccionados, width=22
        )
        self.reprogramar_btn.pack(side=tk.LEFT, padx=5)

        self.worker_status_label = ttk.Label(
            worker_row, text="Estado: Detenido",
            font=('Arial', 9), foreground='gray'
        )
        self.worker_status_label.pack(side=tk.LEFT, padx=10)

        self.stats_label = ttk.Label(
            worker_row,
            text="📊 Procesados: 0 | ✅ Exitosos: 0 | ❌ Errores: 0",
            font=('Arial', 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # -------------- TABLA --------------
        table_frame = ttk.LabelFrame(self, text="Finalizar Casos Laboratorio", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        toolbar = ttk.Frame(table_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="↻ Actualizar", command=self._cargar_casos, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar, text="☑️ Selec. Todo", command=self._seleccionar_todo, width=12).pack(side=tk.LEFT, padx=5)

        self.count_label = ttk.Label(toolbar, text="Total: 0", font=('Arial', 9, 'bold'))
        self.count_label.pack(side=tk.LEFT, padx=10)

        ttk.Label(toolbar, text="🔄 Auto-refresh: 60s", font=('Arial', 8), foreground='green').pack(side=tk.RIGHT, padx=10)

        # Contenedor de tabla + scrollbars
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(table_container, orient="vertical")
        hsb = ttk.Scrollbar(table_container, orient="horizontal")

        columns = ("caso", "fecha", "idIngreso", "idOrden", "idRecepcion", "remision")

        self.tree = ttk.Treeview(
            table_container, columns=columns, show='headings',
            yscrollcommand=vsb.set, xscrollcommand=hsb.set, height=15
        )

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        self.tree.heading("caso", text="Caso")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("idIngreso", text="ID Ingreso")
        self.tree.heading("idOrden", text="ID Orden")
        self.tree.heading("idRecepcion", text="ID Recepción")
        self.tree.heading("remision", text="Remisión")

        self.tree.column("caso", width=450)
        self.tree.column("fecha", width=140, anchor=tk.CENTER)
        self.tree.column("idIngreso", width=90, anchor=tk.CENTER)
        self.tree.column("idOrden", width=90, anchor=tk.CENTER)
        self.tree.column("idRecepcion", width=100, anchor=tk.CENTER)
        self.tree.column("remision", width=80, anchor=tk.CENTER)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # -------------- LOGS --------------
        log_frame = ttk.LabelFrame(self, text="Logs en Vivo", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X)

        ttk.Button(log_toolbar, text="🗑️ Limpiar Log", command=self._limpiar_log, width=15).pack(side=tk.LEFT, padx=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=6, font=('Consolas', 9),
            bg='#1e1e1e', fg='#cccccc'
        )
        self.log_text.pack(fill=tk.X, pady=5)

        self.log_text.tag_configure('info', foreground='#4fc3f7')
        self.log_text.tag_configure('success', foreground='#81c784')
        self.log_text.tag_configure('error', foreground='#ef5350')
        self.log_text.tag_configure('warning', foreground='#ffb74d')

        # Carga inicial
        self._cargar_casos()
        self._agregar_log("Sistema Finalizar Casos Laboratorio iniciado. Esperando casos...")

    # =================================================================
    # DATOS
    # =================================================================

    def _cargar_casos(self):
        """Carga los casos desde la API y aplica filtros locales"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        caso_texto = self.caso_filtro.get().strip() or None
        id_orden_texto = self.id_orden_filtro.get().strip()
        id_orden_val = int(id_orden_texto) if id_orden_texto.isdigit() else None

        casos = self.api_service.obtener_casos(
            id_orden=id_orden_val,
            caso=caso_texto
        )

        if not isinstance(casos, list):
            self._agregar_log(f"⚠️ Respuesta inesperada: {type(casos)}", 'warning')
            casos = []

        for caso in casos:
            if not isinstance(caso, dict):
                continue
            self.tree.insert('', tk.END, values=(
                caso.get('caso', ''),
                caso.get('fecha', ''),
                caso.get('idIngreso', ''),
                caso.get('idOrden', ''),
                caso.get('idRecepcion', ''),
                caso.get('remision', '')
            ))

        total = len(self.tree.get_children())
        self.count_label.config(text=f"Total: {total}")
        self._agregar_log(f"✅ {total} casos cargados")

    def _limpiar_filtros(self):
        self.caso_filtro.set("")
        self.id_orden_filtro.set("")
        self._cargar_casos()

    def _seleccionar_todo(self):
        items = self.tree.get_children()
        if not items:
            return
        if len(self.tree.selection()) == len(items):
            self.tree.selection_remove(*items)
        else:
            self.tree.selection_set(items)

    # =================================================================
    # AUTO-REFRESH
    # =================================================================

    def _start_auto_refresh(self):
        self._auto_refresh()

    def _auto_refresh(self):
        self._cargar_casos()
        self.refresh_id = self.after(60000, self._auto_refresh)

    def _stop_auto_refresh(self):
        if self.refresh_id:
            self.after_cancel(self.refresh_id)
            self.refresh_id = None

    # =================================================================
    # LOGS
    # =================================================================

    def _agregar_log(self, mensaje: str, tipo: str = 'info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {mensaje}\n", tipo)
        self.log_text.see(tk.END)

    def _limpiar_log(self):
        self.log_text.delete(1.0, tk.END)

    # =================================================================
    # WORKER
    # =================================================================

    def _iniciar_worker(self):
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Worker Activo", "El worker ya está en ejecución")
            return

        self._agregar_log("🚀 Iniciando worker de Finalizar Casos...", 'info')

        self.worker = FinalizarCasosWorker(ui_callback=self._ui_log_callback)
        self.worker.on_stats_update = self._actualizar_stats
        self.worker.on_data_update = self._on_worker_data_update
        self.worker.start()

        # Detener auto-refresh del panel (el worker controla los datos)
        self._stop_auto_refresh()
        self._agregar_log("🔄 Auto-refresh desactivado (worker controla datos)", 'info')

        self.start_btn.config(state='disabled')
        self.pause_btn.config(state='normal', text="⏸️ Pausar")
        self.stop_btn.config(state='normal')
        self.worker_status_label.config(text="Estado: Ejecutando", foreground='green')
        self._agregar_log("✅ Worker iniciado!", 'success')

    def _pausar_worker(self):
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
        if not self.worker:
            return
        self._agregar_log("⏹️ Deteniendo worker...", 'warning')
        self.worker.detener()

        # Reactivar auto-refresh del panel
        self._start_auto_refresh()
        self._agregar_log("🔄 Auto-refresh reactivado (cada 60s)", 'info')

        self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled', text="⏸️ Pausar")
        self.stop_btn.config(state='disabled')
        self.worker_status_label.config(text="Estado: Detenido", foreground='gray')
        self.worker = None
        self._agregar_log("⏹️ Worker detenido", 'info')

    def _reprogramar_seleccionados(self):
        seleccionados = self.tree.selection()
        if not seleccionados:
            messagebox.showwarning("Sin selección", "Seleccione al menos un caso")
            return

        if not messagebox.askyesno("Confirmar", f"¿Reprogramar {len(seleccionados)} casos a estado Pendiente?"):
            return

        for item in seleccionados:
            valores = self.tree.item(item, 'values')
            id_orden = valores[3]  # idOrden es la cuarta columna
            try:
                self.api_service.marcar_pendiente(int(id_orden))
                self._agregar_log(f"🔄 Caso {id_orden} reprogramado", 'info')
            except Exception as e:
                self._agregar_log(f"❌ Error reprogramando {id_orden}: {e}", 'error')

        self._cargar_casos()
        self._agregar_log(f"✅ {len(seleccionados)} casos reprogramados", 'success')

    def _ui_log_callback(self, message: str):
        self.after(0, lambda: self._insertar_log_raw(message))

    def _insertar_log_raw(self, mensaje: str):
        self.log_text.insert(tk.END, f"{mensaje}\n")
        self.log_text.see(tk.END)

    def _on_worker_data_update(self, casos: list):
        """Recibe datos del worker y refresca la tabla (sin hacer GET propio)"""
        def update():
            for item in self.tree.get_children():
                self.tree.delete(item)

            if not isinstance(casos, list):
                return

            for caso in casos:
                if not isinstance(caso, dict):
                    continue
                self.tree.insert('', tk.END, values=(
                    caso.get('caso', ''),
                    caso.get('fecha', ''),
                    caso.get('idIngreso', ''),
                    caso.get('idOrden', ''),
                    caso.get('idRecepcion', ''),
                    caso.get('remision', '')
                ))

            total = len(self.tree.get_children())
            self.count_label.config(text=f"Total: {total}")
        self.after(0, update)

    def _actualizar_stats(self, stats: dict):
        def update():
            p = stats.get('procesados', 0)
            e = stats.get('exitosos', 0)
            err = stats.get('errores', 0)
            self.stats_label.config(
                text=f"📊 Procesados: {p} | ✅ Exitosos: {e} | ❌ Errores: {err}"
            )
        self.after(0, update)

    # =================================================================
    # CLEANUP
    # =================================================================

    def destroy(self):
        self._stop_auto_refresh()
        if self.worker and self.worker.is_alive():
            self.worker.detener()
        super().destroy()
