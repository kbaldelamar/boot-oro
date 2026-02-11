"""
Panel de control del Worker de Automatización
Muestra estado, controles y tabla de órdenes programadas
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.autorizar_anexo3.services.automation_worker import AutomationWorker
from modules.autorizar_anexo3.services.programacion_service import ProgramacionService


class ProgramacionPanel(ttk.Frame):
    """Panel para controlar el Worker de automatización"""
    
    def __init__(self, parent, config):
        """
        Args:
            parent: Widget padre
            config: Configuración
        """
        super().__init__(parent)
        self.config = config
        self.global_config = Config()  # Configuración global
        self.worker: Optional[AutomationWorker] = None
        self.api_service = ProgramacionService()
        self.refresh_id = None
        self.estado_filtro = tk.StringVar(value="PENDIENTE")  # Filtro por defecto
        
        self._create_widgets()
        self._start_auto_refresh()
    
    def _create_widgets(self):
        """Crea todos los widgets del panel"""
        # =========================
        # SECCIÓN DE CONTROLES
        # =========================
        control_frame = ttk.LabelFrame(self, text="Control del Worker", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Botones de control
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.btn_iniciar = ttk.Button(
            btn_frame,
            text="▶️ Iniciar Worker",
            command=self._iniciar_worker,
            width=20
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)
        
        self.btn_pausar = ttk.Button(
            btn_frame,
            text="⏸️ Pausar",
            command=self._pausar_worker,
            state='disabled',
            width=15
        )
        self.btn_pausar.pack(side=tk.LEFT, padx=5)
        
        self.btn_detener = ttk.Button(
            btn_frame,
            text="⏹️ Detener",
            command=self._detener_worker,
            state='disabled',
            width=15
        )
        self.btn_detener.pack(side=tk.LEFT, padx=5)
        
        # Estado del worker
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(side=tk.RIGHT)
        
        ttk.Label(status_frame, text="Estado:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.status_label = ttk.Label(
            status_frame,
            text="⚪ INACTIVO",
            font=('Arial', 10, 'bold'),
            foreground='gray'
        )
        self.status_label.pack(side=tk.LEFT)
        
        # =========================
        # ESTADÍSTICAS
        # =========================
        stats_frame = ttk.LabelFrame(self, text="Estadísticas", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Fila de estadísticas
        stats_row = ttk.Frame(stats_frame)
        stats_row.pack(fill=tk.X)
        
        # Procesados
        ttk.Label(stats_row, text="Procesados:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        self.procesados_label = ttk.Label(stats_row, text="0", font=('Arial', 9, 'bold'))
        self.procesados_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Exitosos
        ttk.Label(stats_row, text="✅ Exitosos:", font=('Arial', 9), foreground='green').pack(side=tk.LEFT, padx=5)
        self.exitosos_label = ttk.Label(stats_row, text="0", font=('Arial', 9, 'bold'), foreground='green')
        self.exitosos_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Errores
        ttk.Label(stats_row, text="❌ Errores:", font=('Arial', 9), foreground='red').pack(side=tk.LEFT, padx=5)
        self.errores_label = ttk.Label(stats_row, text="0", font=('Arial', 9, 'bold'), foreground='red')
        self.errores_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Navegador
        ttk.Label(stats_row, text="🌐 Navegador:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        self.navegador_label = ttk.Label(stats_row, text="Sin sesión", font=('Arial', 9, 'italic'))
        self.navegador_label.pack(side=tk.LEFT)
        
        # =========================
        # TABLA DE PROGRAMADOS
        # =========================
        table_frame = ttk.LabelFrame(self, text="Órdenes Programadas", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Toolbar de tabla
        toolbar = ttk.Frame(table_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            toolbar,
            text="↻ Actualizar",
            command=self._cargar_programados,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="🗑️ Anular",
            command=self._anular_seleccion,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Filtro por estado
        ttk.Label(toolbar, text="Estado:", font=('Arial', 9)).pack(side=tk.LEFT, padx=(15, 5))
        estados = ["TODO", "PENDIENTE", "EN_PROGRESO", "COMPLETADO", "ERROR", "CANCELADO"]
        combo_estado = ttk.Combobox(
            toolbar,
            textvariable=self.estado_filtro,
            values=estados,
            state='readonly',
            width=15
        )
        combo_estado.pack(side=tk.LEFT, padx=5)
        combo_estado.bind('<<ComboboxSelected>>', lambda e: self._cargar_programados())
        
        self.count_programados_label = ttk.Label(toolbar, text="Total: 0", font=('Arial', 9, 'bold'))
        self.count_programados_label.pack(side=tk.LEFT, padx=10)
        
        # Indicador de auto-refresh
        ttk.Label(toolbar, text="🔄 Auto-refresh: 60s", font=('Arial', 8), foreground='green').pack(side=tk.RIGHT, padx=10)
        
        # Crear tabla
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_container, orient="vertical")
        hsb = ttk.Scrollbar(table_container, orient="horizontal")
        
        columns = ("id_item", "paciente", "orden", "estado", "intentos", "fecha", "resultado")
        self.tree_programados = ttk.Treeview(
            table_container,
            columns=columns,
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=10
        )
        
        vsb.config(command=self.tree_programados.yview)
        hsb.config(command=self.tree_programados.xview)
        
        # Configurar columnas
        self.tree_programados.heading("id_item", text="ID Item")
        self.tree_programados.heading("paciente", text="Paciente")
        self.tree_programados.heading("orden", text="ID Orden")
        self.tree_programados.heading("estado", text="Estado")
        self.tree_programados.heading("intentos", text="Intentos")
        self.tree_programados.heading("fecha", text="Fecha Prog.")
        self.tree_programados.heading("resultado", text="Resultado")
        
        self.tree_programados.column("id_item", width=80, anchor=tk.CENTER)
        self.tree_programados.column("paciente", width=200)
        self.tree_programados.column("orden", width=80, anchor=tk.CENTER)
        self.tree_programados.column("estado", width=120, anchor=tk.CENTER)
        self.tree_programados.column("intentos", width=80, anchor=tk.CENTER)
        self.tree_programados.column("fecha", width=150, anchor=tk.CENTER)
        self.tree_programados.column("resultado", width=200)
        
        # Tags para colores
        self.tree_programados.tag_configure('PENDIENTE', background='#fffacd')
        self.tree_programados.tag_configure('EN_PROGRESO', background='#87ceeb')
        self.tree_programados.tag_configure('COMPLETADO', background='#90ee90')
        self.tree_programados.tag_configure('ERROR', background='#ffcccb')
        
        # Grid
        self.tree_programados.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # =========================
        # LOGS EN VIVO
        # =========================
        logs_frame = ttk.LabelFrame(self, text="Logs en Vivo", padding=10)
        logs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Toolbar de logs
        logs_toolbar = ttk.Frame(logs_frame)
        logs_toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            logs_toolbar,
            text="🗑️ Limpiar Logs",
            command=self._limpiar_logs,
            width=15
        ).pack(side=tk.LEFT)
        
        # TextBox de logs
        self.log_text = scrolledtext.ScrolledText(
            logs_frame,
            height=8,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state='disabled')
        
        # Agregar mensaje inicial
        self._agregar_log("Sistema de automatización iniciado. Esperando órdenes...")

    def _anular_seleccion(self):
        """Anula las órdenes seleccionadas en la tabla"""
        seleccion = self.tree_programados.selection()
        if not seleccion:
            messagebox.showwarning("Sin selección", "Seleccione al menos un registro")
            return

        if not messagebox.askyesno(
            "Confirmar",
            f"¿Anular {len(seleccion)} registro(s) seleccionado(s)?"
        ):
            return

        anuladas = 0
        canceladas = 0
        errores = 0

        for item_id in seleccion:
            valores = self.tree_programados.item(item_id, "values")
            id_item = valores[0] if valores else None
            if not id_item:
                errores += 1
                continue

            try:
                ok_anular = self.api_service.anular_orden(int(id_item))
                ok_cancelar = self.api_service.cancelar_programacion(int(id_item))

                if ok_anular:
                    anuladas += 1
                if ok_cancelar:
                    canceladas += 1
                if not ok_anular or not ok_cancelar:
                    errores += 1
            except Exception:
                errores += 1

        self._agregar_log(
            f"🗑️ Anuladas: {anuladas}, canceladas: {canceladas}, errores: {errores}"
        )
        self._cargar_programados()
    
    def _iniciar_worker(self):
        """Inicia el worker de automatización"""
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Worker Activo", "El worker ya está en ejecución")
            return
        
        try:
            self._agregar_log("🚀 Iniciando Worker de automatización...")
            
            # Crear worker con callback para logs
            self.worker = AutomationWorker(ui_callback=self._agregar_log)
            self.worker.on_stats_update = self._actualizar_estadisticas
            
            # Iniciar thread
            self.worker.start()
            
            # Actualizar UI
            self.status_label.config(text="🟢 ACTIVO", foreground='green')
            self.btn_iniciar.config(state='disabled')
            self.btn_pausar.config(state='normal')
            self.btn_detener.config(state='normal')
            
            self._agregar_log("✅ Worker iniciado correctamente")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el worker:\n{str(e)}")
            self._agregar_log(f"❌ Error iniciando worker: {str(e)}")
    
    def _pausar_worker(self):
        """Pausa/reanuda el worker"""
        if not self.worker:
            return
        
        if self.worker.paused:
            self.worker.reanudar()
            self.btn_pausar.config(text="⏸️ Pausar")
            self.status_label.config(text="🟢 ACTIVO", foreground='green')
            self._agregar_log("▶️ Worker reanudado")
        else:
            self.worker.pausar()
            self.btn_pausar.config(text="▶️ Reanudar")
            self.status_label.config(text="🟡 PAUSADO", foreground='orange')
            self._agregar_log("⏸️ Worker pausado")
    
    def _detener_worker(self):
        """Detiene el worker completamente"""
        if not self.worker:
            return
        
        if messagebox.askyesno("Confirmar", "¿Detener el worker de automatización?"):
            self._agregar_log("⏹️ Deteniendo worker...")
            
            self.worker.detener()
            
            # Actualizar UI
            self.status_label.config(text="⚪ INACTIVO", foreground='gray')
            self.btn_iniciar.config(state='normal')
            self.btn_pausar.config(state='disabled', text="⏸️ Pausar")
            self.btn_detener.config(state='disabled')
            
            self._agregar_log("✅ Worker detenido")
    
    def _actualizar_estadisticas(self, stats: dict):
        """Actualiza las estadísticas en la UI"""
        self.procesados_label.config(text=str(stats.get('procesados', 0)))
        self.exitosos_label.config(text=str(stats.get('exitosos', 0)))
        self.errores_label.config(text=str(stats.get('errores', 0)))
    
    def _cargar_programados(self):
        """Carga las órdenes programadas desde la API"""
        try:
            # Limpiar tabla
            for item in self.tree_programados.get_children():
                self.tree_programados.delete(item)
            
            # Construir URL con filtro
            import requests
            base_url = self.global_config.api_url_programacion
            estado_actual = self.estado_filtro.get()
            
            if estado_actual == "TODO":
                url = f"{base_url}?page=1&per_page=100"
            else:
                url = f"{base_url}?estado={estado_actual}&page=1&per_page=100"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # La estructura es: {data: {programaciones: [...]}}
                data_wrapper = data.get('data', {})
                ordenes = data_wrapper.get('programaciones', [])
                
                for orden in ordenes:
                    # Obtener nombre del paciente (necesitamos hacer otra llamada o tener el dato)
                    paciente = f"Orden {orden.get('id_orden', 'N/A')}"
                    
                    # Manejar valores None en resultado y mensaje de error
                    resultado = orden.get('resultado_ejecucion') or ''
                    mensaje_error = orden.get('mensaje_error') or ''
                    resultado_texto = resultado[:50] or mensaje_error[:50] or '-'
                    
                    valores = (
                        orden.get('id_item_orden_proced', ''),
                        paciente,
                        orden.get('id_orden', ''),
                        self._format_estado(orden.get('estado', 'PENDIENTE')),
                        f"{orden.get('intentos_realizados', 0)}/{orden.get('intentos_maximos', 2)}",
                        self._format_fecha(orden.get('fecha_programacion', '')),
                        resultado_texto
                    )
                    
                    tag = orden.get('estado', 'PENDIENTE')
                    self.tree_programados.insert("", tk.END, values=valores, tags=(tag,))
                
                self.count_programados_label.config(text=f"Total: {len(ordenes)}")
                self._agregar_log(f"✅ {len(ordenes)} órdenes {estado_actual}")
            else:
                self._agregar_log(f"❌ Error HTTP: {response.status_code}")
            
        except Exception as e:
            self._agregar_log(f"❌ Error: {str(e)}")
    
    def _format_estado(self, estado: str) -> str:
        """Formatea el estado con emoji"""
        emojis = {
            'PENDIENTE': '⏳',
            'EN_PROGRESO': '🔵',
            'COMPLETADO': '✅',
            'ERROR': '❌',
            'CANCELADO': '🚫'
        }
        emoji = emojis.get(estado, '📝')
        return f"{emoji} {estado}"
    
    def _format_fecha(self, fecha_str: str) -> str:
        """Formatea la fecha"""
        try:
            if not fecha_str:
                return '-'
            # Formato que viene del API: "Mon, 02 Feb 2026 16:48:15 GMT"
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(fecha_str)
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            # Si falla, devolver la fecha tal cual (truncada)
            return fecha_str[:19] if len(fecha_str) > 19 else fecha_str
    
    def _agregar_log(self, mensaje: str):
        """Agrega un mensaje al log"""
        self.log_text.config(state='normal')
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"{mensaje}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    
    def _limpiar_logs(self):
        """Limpia el área de logs"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self._agregar_log("Logs limpiados")
    
    def _start_auto_refresh(self):
        """Inicia el auto-refresh de la tabla (cada 60 segundos)"""
        self._cargar_programados()
        self.refresh_id = self.after(60000, self._refresh_loop)  # 60 segundos
    
    def _refresh_loop(self):
        """Loop de refresco (cada minuto)"""
        self._cargar_programados()
        self.refresh_id = self.after(60000, self._refresh_loop)  # 60 segundos
    
    def destroy(self):
        """Limpia recursos al destruir"""
        if self.refresh_id:
            self.after_cancel(self.refresh_id)

        if self.worker:
            # Evitar callbacks a UI destruida
            self.worker.on_stats_update = None
            if hasattr(self.worker, 'logger'):
                self.worker.logger.ui_callback = None

        super().destroy()
