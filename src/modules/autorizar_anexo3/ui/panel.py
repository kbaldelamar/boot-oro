"""
Panel para mostrar órdenes HC del sistema.
Consume el API real y muestra los datos en tabla con auto-refresco.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.autorizar_anexo3.services import AutorizarAnexo3Service
from modules.autorizar_anexo3.services.programacion_service import ProgramacionService
from modules.autorizar_anexo3.services.pdf_anexo3_service import PDFAnexo3Service
from utils.logger import AdvancedLogger


class AutorizarAnexo3Panel(ttk.Frame):
    """
    Panel para visualizar órdenes HC con refresco automático cada 60 segundos.
    """
    
    def __init__(self, parent, config):
        """
        Inicializa el panel.
        
        Args:
            parent: Widget padre
            config: Instancia de configuración
        """
        super().__init__(parent)
        self.config = config
        self.service = AutorizarAnexo3Service(config)
        self.programacion_service = ProgramacionService(
            base_url=config.api_url_programacion_base or 'http://localhost:5000'
        )
        self.logger = AdvancedLogger()
        try:
            self.pdf_service = PDFAnexo3Service(self.logger, config)
        except ImportError as e:
            self.pdf_service = None
            messagebox.showwarning(
                "PDF",
                f"No se pudo inicializar PDF: {str(e)}"
            )
        self.auto_refresh_id = None
        self.refresh_interval = 60000  # 60 segundos en milisegundos
        self.seleccionados = set()  # IDs de órdenes seleccionadas
        self.ordenes_por_item = {}
        
        self._create_widgets()
        self._cargar_datos()
        self._start_auto_refresh()
    
    def _create_widgets(self):
        """Crea los widgets del panel"""
        # Barra de herramientas superior
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            toolbar,
            text="Órdenes HC - Pacientes",
            font=('Arial', 16, 'bold')
        ).pack(side=tk.LEFT)
        
        # Indicador de última actualización
        self.last_update_label = ttk.Label(
            toolbar,
            text="Última actualización: --:--:--",
            font=('Arial', 9),
            foreground='gray'
        )
        self.last_update_label.pack(side=tk.LEFT, padx=20)

        # Filtro por estado
        self.estado_caso_var = tk.StringVar(value="0 - Por procesar")
        ttk.Label(toolbar, text="Estado:").pack(side=tk.LEFT, padx=(10, 5))
        estados = [
            "0 - Por procesar",
            "1 - Exitoso",
            "2 - Programado",
            "3 - En proceso",
            "4 - Error",
            "5 - Estado 5",
            "99 - Anulado"
        ]
        combo_estado = ttk.Combobox(
            toolbar,
            textvariable=self.estado_caso_var,
            values=estados,
            state='readonly',
            width=18
        )
        combo_estado.pack(side=tk.LEFT)
        combo_estado.bind('<<ComboboxSelected>>', lambda e: self._cargar_datos())

        # Busqueda por nombre o documento
        self.nombre_var = tk.StringVar()
        self.documento_var = tk.StringVar()
        ttk.Label(toolbar, text="Nombre:").pack(side=tk.LEFT, padx=(10, 5))
        nombre_entry = ttk.Entry(toolbar, textvariable=self.nombre_var, width=18)
        nombre_entry.pack(side=tk.LEFT)
        ttk.Label(toolbar, text="Documento:").pack(side=tk.LEFT, padx=(10, 5))
        documento_entry = ttk.Entry(toolbar, textvariable=self.documento_var, width=14)
        documento_entry.pack(side=tk.LEFT)
        ttk.Button(
            toolbar,
            text="🔍 Buscar",
            command=self._cargar_datos
        ).pack(side=tk.LEFT, padx=5)
        
        # Botón para programar órdenes
        ttk.Button(
            toolbar,
            text="📅 Programar Seleccionados",
            command=self._programar_seleccionados,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT, padx=5)

        # Botón para generar PDF
        ttk.Button(
            toolbar,
            text="📄 Generar PDF",
            command=self._generar_pdf_seleccionados
        ).pack(side=tk.RIGHT, padx=5)

        # Botón para anular órdenes
        ttk.Button(
            toolbar,
            text="🗑️ Anular Seleccionados",
            command=self._anular_seleccionados
        ).pack(side=tk.RIGHT, padx=5)
        
        # Botón de refresco manual
        ttk.Button(
            toolbar,
            text="↻ Actualizar Ahora",
            command=self._cargar_datos
        ).pack(side=tk.RIGHT, padx=5)
        
        # Contador de registros
        self.count_label = ttk.Label(
            toolbar,
            text="Registros: 0",
            font=('Arial', 9, 'bold')
        )
        self.count_label.pack(side=tk.RIGHT, padx=10)
        
        # Frame para la tabla con scrollbars
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")
        
        # Frame para la tabla con checkboxes
        columns = (
            "seleccion", "idOrden", "idItemOrden", "NoDocumento", "Paciente", 
            "cups", "procedimiento", "FechaOrden", "estadoCaso", "telefono"
        )
        
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='tree headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=20
        )
        
        # Bind para selección
        self.tree.bind('<Button-1>', self._on_click)
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Configurar columna #0 para checkbox
        self.tree.heading("#0", text="☑")
        self.tree.heading("seleccion", text="")
        self.tree.heading("idOrden", text="ID Orden")
        self.tree.heading("idItemOrden", text="ID Item")
        self.tree.heading("NoDocumento", text="Documento")
        self.tree.heading("Paciente", text="Paciente")
        self.tree.heading("cups", text="CUPS")
        self.tree.heading("procedimiento", text="Procedimiento")
        self.tree.heading("FechaOrden", text="Fecha Orden")
        self.tree.heading("estadoCaso", text="Estado")
        self.tree.heading("telefono", text="Teléfono")
        
        self.tree.column("#0", width=30, anchor=tk.CENTER)
        self.tree.column("seleccion", width=0, stretch=False)
        self.tree.column("idOrden", width=80, anchor=tk.CENTER)
        self.tree.column("idItemOrden", width=80, anchor=tk.CENTER)
        self.tree.column("NoDocumento", width=100, anchor=tk.CENTER)
        self.tree.column("Paciente", width=200)
        self.tree.column("cups", width=80, anchor=tk.CENTER)
        self.tree.column("procedimiento", width=400)
        self.tree.column("FechaOrden", width=150, anchor=tk.CENTER)
        self.tree.column("estadoCaso", width=70, anchor=tk.CENTER)
        self.tree.column("telefono", width=120, anchor=tk.CENTER)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Barra de estado
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(
            status_frame,
            text="Listo para cargar datos",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.auto_refresh_label = ttk.Label(
            status_frame,
            text="Auto-refresco: Activo (60s)",
            relief=tk.SUNKEN,
            anchor=tk.E,
            foreground='green'
        )
        self.auto_refresh_label.pack(side=tk.RIGHT)
    
    def _cargar_datos(self):
        """Carga los datos desde el API"""
        # Limpiar tabla al inicio para evitar datos congelados
        self._actualizar_tabla([])
        self.status_label.config(text="Cargando datos desde API...")
        self.update_idletasks()
        
        try:
            # Llamada al servicio
            estado_texto = self.estado_caso_var.get().split("-")[0].strip()
            try:
                estado_caso = int(estado_texto)
            except ValueError:
                estado_caso = 0

            nombre = self.nombre_var.get().strip()
            documento = self.documento_var.get().strip()
            response = self.service.obtener_ordenes_hc(
                estado_caso=estado_caso,
                nombre=nombre or None,
                documento=documento or None
            )
            
            if response['success']:
                ordenes = response['data'] or []
                self._actualizar_tabla(ordenes)

                # Actualizar labels
                ahora = datetime.now().strftime("%H:%M:%S")
                self.last_update_label.config(text=f"Última actualización: {ahora}")
                self.count_label.config(text=f"Registros: {len(ordenes)}")
                self.status_label.config(
                    text=f"✓ Datos cargados exitosamente - {len(ordenes)} registros"
                )
            else:
                self._actualizar_tabla([])
                self.status_label.config(
                    text=f"⚠ Error al cargar datos: {response['message']}"
                )

                # Mensaje personalizado según el código de error
                error_detail = response['error'] or response['message']

                messagebox.showerror(
                    "Error al Cargar Datos",
                    f"{response['message']}\n\n"
                    f"{error_detail}"
                )
                
        except Exception as e:
            self._actualizar_tabla([])
            self.status_label.config(text=f"✗ Error: {str(e)}")
            messagebox.showerror(
                "Error",
                f"Error al conectar con el API:\n{str(e)}\n\n"
                f"Asegúrese de que el servidor esté ejecutándose en:\n"
                f"{self.config.api_url_programacion_base}"
            )
    
    def _actualizar_tabla(self, ordenes):
        """Actualiza la tabla con los datos y preserva selecciones"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.seleccionados.clear()
        self.ordenes_por_item.clear()
        
        # Agregar nuevos datos
        for orden in ordenes:
            id_item = orden.get('idItemOrden')
            valores = self.service.formatear_orden_para_tabla(orden)
            if id_item is not None:
                self.ordenes_por_item[int(id_item)] = orden
            
            # Insertar con checkbox vacío
            # La columna "seleccion" guarda el idItemOrden
            valores_con_check = ("", *valores)
            
            self.tree.insert("", tk.END, text="☐", values=valores_con_check, tags=(str(id_item),))
    
    def _start_auto_refresh(self):
        """Inicia el refresco automático cada 60 segundos"""
        self._schedule_refresh()
    
    def _schedule_refresh(self):
        """Programa el próximo refresco"""
        if self.auto_refresh_id:
            self.after_cancel(self.auto_refresh_id)
        
        self.auto_refresh_id = self.after(self.refresh_interval, self._on_auto_refresh)
    
    def _on_auto_refresh(self):
        """Callback para el refresco automático"""
        self._cargar_datos()
        self._schedule_refresh()  # Programar el siguiente
    
    def destroy(self):
        """Limpia recursos al destruir el panel"""
        # Cancelar el timer de auto-refresco
        if self.auto_refresh_id:
            self.after_cancel(self.auto_refresh_id)
        
        # Cerrar servicio
        if hasattr(self, 'service'):
            self.service.close()
        
        super().destroy()
    
    def _on_click(self, event):
        """Maneja clicks en la tabla para seleccionar/deseleccionar"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":
            item = self.tree.identify_row(event.y)
            if item:
                self._toggle_seleccion(item)
    
    def _toggle_seleccion(self, item):
        """Alterna la selección de un item"""
        # Obtener idItemOrden de los tags
        tags = self.tree.item(item, 'tags')
        if not tags:
            return
        
        id_item = int(tags[0])
        
        if id_item in self.seleccionados:
            # Deseleccionar
            self.seleccionados.remove(id_item)
            self.tree.item(item, text="☐")
        else:
            # Seleccionar
            self.seleccionados.add(id_item)
            self.tree.item(item, text="☑")
    
    def _toggle_todos(self):
        """Selecciona/deselecciona todos"""
        if len(self.seleccionados) > 0:
            # Deseleccionar todos
            for item in self.tree.get_children():
                self.tree.item(item, text="☐")
            self.seleccionados.clear()
        else:
            # Seleccionar todos
            for item in self.tree.get_children():
                tags = self.tree.item(item, 'tags')
                if tags:
                    id_item = int(tags[0])
                    self.seleccionados.add(id_item)
                    self.tree.item(item, text="☑")
    
    def _programar_seleccionados(self):
        """Programa las órdenes seleccionadas"""
        if not self.seleccionados:
            messagebox.showwarning(
                "Sin Selección",
                "Por favor seleccione al menos una orden para programar"
            )
            return
        
        # Confirmar
        cantidad = len(self.seleccionados)
        if not messagebox.askyesno(
            "Confirmar Programación",
            f"¿Programar {cantidad} orden(es) para automatización?"
        ):
            return
        
        # Programar cada una
        exitosos = 0
        errores = 0
        
        for id_item in self.seleccionados:
            # Obtener id_orden del item en la tabla
            # Buscar en la tabla
            for item in self.tree.get_children():
                tags = self.tree.item(item, 'tags')
                if tags and int(tags[0]) == id_item:
                    valores = self.tree.item(item, 'values')
                    id_orden = valores[1]  # Segunda columna es idOrden
                    
                    # Programar
                    if self.programacion_service.programar_orden(id_item, id_orden, usuario="usuario_ui"):
                        exitosos += 1
                    else:
                        errores += 1
                    break
        
        # Mostrar resultado
        if errores == 0:
            messagebox.showinfo(
                "Éxito",
                f"✅ {exitosos} orden(es) programada(s) exitosamente.\n\n"
                f"Ve a la pestaña 'Worker Automatización' para iniciar el procesamiento."
            )
        else:
            messagebox.showwarning(
                "Programación Completada",
                f"✅ {exitosos} orden(es) programada(s)\n"
                f"❌ {errores} orden(es) con error"
            )
        
        # Limpiar selección y recargar
        self.seleccionados.clear()
        self._cargar_datos()

    def _generar_pdf_seleccionados(self):
        """Genera y abre el PDF del Anexo 3 para las órdenes seleccionadas"""
        if not self.pdf_service:
            messagebox.showwarning(
                "PDF",
                "PDF no esta disponible. Instale PyMuPDF para habilitar esta funcion."
            )
            return

        tipo = self._seleccionar_tipo_impresion()
        if not tipo:
            return
        if not self.seleccionados:
            messagebox.showwarning(
                "Sin Selección",
                "Por favor seleccione al menos una orden para generar PDF"
            )
            return

        errores = 0
        for id_item in self.seleccionados:
            orden = self.ordenes_por_item.get(id_item)
            if not orden:
                errores += 1
                continue

            try:
                id_atencion = orden.get('idAtencion') or orden.get('IdAtencion')
                id_orden = orden.get('idOrden') or orden.get('IdOrden')
                id_procedimiento = orden.get('idProcedimiento') or orden.get('Id_Procedimiento')

                if not id_atencion or not id_orden:
                    errores += 1
                    continue

                if tipo == "grupo":
                    file_path = self.pdf_service.generar_anexo3_grupo(
                        id_atencion=int(id_atencion),
                        id_orden=int(id_orden)
                    )
                else:
                    if not id_procedimiento:
                        errores += 1
                        continue
                    file_path = self.pdf_service.generar_anexo3(
                        id_atencion=int(id_atencion),
                        id_orden=int(id_orden),
                        id_procedimiento=int(id_procedimiento)
                    )

                if os.path.exists(file_path):
                    os.startfile(file_path)
                else:
                    errores += 1
            except Exception:
                errores += 1

        if errores:
            messagebox.showwarning(
                "PDF",
                f"Se generaron PDFs con errores: {errores}"
            )

    def _seleccionar_tipo_impresion(self) -> Optional[str]:
        """Pregunta el tipo de impresion y devuelve 'individual' o 'grupo'"""
        respuesta = {'tipo': None}

        ventana = tk.Toplevel(self)
        ventana.title("Imprimir")
        ancho, alto = 320, 140
        ventana.geometry(f"{ancho}x{alto}")
        ventana.resizable(False, False)
        ventana.transient(self)

        ttk.Label(
            ventana,
            text="Seleccione el tipo de impresion",
            font=('Arial', 10, 'bold')
        ).pack(pady=10)

        btn_frame = ttk.Frame(ventana)
        btn_frame.pack(pady=5)

        def elegir(tipo: str):
            respuesta['tipo'] = tipo
            ventana.destroy()

        ttk.Button(
            btn_frame,
            text="Imprimir individual",
            command=lambda: elegir("individual"),
            width=18
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Imprimir grupo",
            command=lambda: elegir("grupo"),
            width=18
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            ventana,
            text="Cancelar",
            command=ventana.destroy,
            width=12
        ).pack(pady=5)

        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

        ventana.grab_set()
        ventana.wait_window()

        return respuesta['tipo']

    def _anular_seleccionados(self):
        """Anula las órdenes seleccionadas"""
        if not self.seleccionados:
            messagebox.showwarning(
                "Sin Selección",
                "Por favor seleccione al menos una orden para anular"
            )
            return

        cantidad = len(self.seleccionados)
        if not messagebox.askyesno(
            "Confirmar Anulación",
            f"¿Anular {cantidad} orden(es) seleccionada(s)?"
        ):
            return

        exitosos = 0
        errores = 0

        for id_item in self.seleccionados:
            if self.programacion_service.anular_orden(id_item):
                exitosos += 1
            else:
                errores += 1

        if errores == 0:
            messagebox.showinfo(
                "Éxito",
                f"✅ {exitosos} orden(es) anulada(s) exitosamente."
            )
        else:
            messagebox.showwarning(
                "Anulación Completada",
                f"✅ {exitosos} orden(es) anulada(s)\n"
                f"❌ {errores} orden(es) con error"
            )

        self.seleccionados.clear()
        self._cargar_datos()