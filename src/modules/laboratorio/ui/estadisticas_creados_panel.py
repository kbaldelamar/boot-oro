"""
Panel de Estadísticas de Casos Creados en Laboratorio
Muestra conteos y métricas de todos los casos creados
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, Any, List
from tkcalendar import DateEntry
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.laboratorio.services.laboratorio_service import LaboratorioService


class EstadisticasCreadosPanel(ttk.Frame):
    """Panel para visualizar estadísticas de casos creados en laboratorio"""
    
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
        self.datos_reporte: List[Dict[str, Any]] = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Crea todos los widgets del panel"""
        # =========================
        # ENCABEZADO
        # =========================
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(
            header_frame,
            text="📊 Estadísticas - Casos Creados Laboratorio",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        # =========================
        # FILTROS
        # =========================
        filtros_frame = ttk.LabelFrame(self, text="Filtros de Búsqueda", padding=10)
        filtros_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Primera fila - Estado
        fila1 = ttk.Frame(filtros_frame)
        fila1.pack(fill=tk.X, pady=5)
        
        ttk.Label(fila1, text="Estado:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        
        self.estado_var = tk.StringVar(value="")
        estados = [
            ("Todos", ""),
            ("Pendiente", "0"),
            ("Exitoso", "1"),
            ("En proceso", "2"),
            ("Doc incorrecto", "4"),
            ("PDF no encontrado", "5"),
            ("Solicitud activa", "6"),
            ("Error no clasificado", "11"),
            ("Sesión perdida", "12"),
            ("Timeout", "13"),
            ("Elemento no encontrado", "14"),
            ("Elemento obsoleto", "15"),
            ("Error de conexión", "16"),
            ("Error de permisos", "18")
        ]
        
        self.combo_estado = ttk.Combobox(
            fila1,
            textvariable=self.estado_var,
            values=[e[0] for e in estados],
            state='readonly',
            width=25
        )
        self.combo_estado.pack(side=tk.LEFT, padx=5)
        self.combo_estado.current(0)  # "Todos" por defecto
        
        # Mapeo de texto a código
        self.estados_map = {e[0]: e[1] for e in estados}
        
        # Segunda fila - Fechas
        fila2 = ttk.Frame(filtros_frame)
        fila2.pack(fill=tk.X, pady=5)
        
        ttk.Label(fila2, text="Fecha Inicio:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        self.fecha_inicio = DateEntry(
            fila2,
            width=15,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.fecha_inicio.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(fila2, text="Fecha Fin:", font=('Arial', 9)).pack(side=tk.LEFT, padx=15)
        self.fecha_fin = DateEntry(
            fila2,
            width=15,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='yyyy-mm-dd'
        )
        self.fecha_fin.pack(side=tk.LEFT, padx=5)
        
        # Botón buscar
        btn_buscar = ttk.Button(
            fila2,
            text="🔍 Buscar",
            command=self._buscar_reporte
        )
        btn_buscar.pack(side=tk.LEFT, padx=15)
        
        # Botón limpiar filtros
        btn_limpiar = ttk.Button(
            fila2,
            text="🗑️ Limpiar",
            command=self._limpiar_filtros
        )
        btn_limpiar.pack(side=tk.LEFT, padx=5)
        
        # Botón exportar Excel
        btn_exportar = ttk.Button(
            fila2,
            text="📊 Exportar Excel",
            command=self._exportar_excel
        )
        btn_exportar.pack(side=tk.LEFT, padx=15)
        
        # =========================
        # ESTADÍSTICAS GENERALES
        # =========================
        stats_frame = ttk.LabelFrame(self, text="Resumen", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        # Total de casos
        ttk.Label(stats_grid, text="Total Registros:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, sticky='w', padx=10, pady=5
        )
        self.total_label = ttk.Label(stats_grid, text="0", font=('Arial', 10))
        self.total_label.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        # Exitosos
        ttk.Label(stats_grid, text="Exitosos:", font=('Arial', 10, 'bold')).grid(
            row=0, column=2, sticky='w', padx=10, pady=5
        )
        self.exitosos_label = ttk.Label(stats_grid, text="0", font=('Arial', 10), foreground='green')
        self.exitosos_label.grid(row=0, column=3, sticky='w', padx=10, pady=5)
        
        # Pendientes
        ttk.Label(stats_grid, text="Pendientes:", font=('Arial', 10, 'bold')).grid(
            row=1, column=0, sticky='w', padx=10, pady=5
        )
        self.pendientes_label = ttk.Label(stats_grid, text="0", font=('Arial', 10), foreground='orange')
        self.pendientes_label.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        # Con errores
        ttk.Label(stats_grid, text="Con Errores:", font=('Arial', 10, 'bold')).grid(
            row=1, column=2, sticky='w', padx=10, pady=5
        )
        self.errores_label = ttk.Label(stats_grid, text="0", font=('Arial', 10), foreground='red')
        self.errores_label.grid(row=1, column=3, sticky='w', padx=10, pady=5)
        
        # Descripción del reporte
        self.descripcion_label = ttk.Label(stats_grid, text="", font=('Arial', 9), foreground='gray')
        self.descripcion_label.grid(row=2, column=0, columnspan=4, sticky='w', padx=10, pady=5)
        
        # =========================
        # TABLA DE DATOS
        # =========================
        tabla_frame = ttk.LabelFrame(self, text="Registros Encontrados", padding=10)
        tabla_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Frame para el treeview con scrollbars
        tree_container = ttk.Frame(tabla_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(tree_container, orient='vertical')
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(tree_container, orient='horizontal')
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_container,
            columns=('documento', 'tipo_doc', 'nombre', 'orden_interna', 'cups', 'procedimiento', 
                     'estado', 'descripcion_estado', 'autorizacion', 'fecha_factura', 'fecha_ingreso'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            height=15
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # Configurar columnas
        self.tree.heading('documento', text='Documento')
        self.tree.heading('tipo_doc', text='Tipo')
        self.tree.heading('nombre', text='Nombre Paciente')
        self.tree.heading('orden_interna', text='Orden Interna')
        self.tree.heading('cups', text='CUPS')
        self.tree.heading('procedimiento', text='Procedimiento')
        self.tree.heading('estado', text='Est.')
        self.tree.heading('descripcion_estado', text='Descripción Estado')
        self.tree.heading('autorizacion', text='N° Autorización')
        self.tree.heading('fecha_factura', text='Fecha Factura')
        self.tree.heading('fecha_ingreso', text='Fecha Ingreso')
        
        self.tree.column('documento', width=100, anchor='center')
        self.tree.column('tipo_doc', width=50, anchor='center')
        self.tree.column('nombre', width=180, anchor='w')
        self.tree.column('orden_interna', width=90, anchor='center')
        self.tree.column('cups', width=80, anchor='center')
        self.tree.column('procedimiento', width=300, anchor='w')
        self.tree.column('estado', width=40, anchor='center')
        self.tree.column('descripcion_estado', width=130, anchor='w')
        self.tree.column('autorizacion', width=100, anchor='center')
        self.tree.column('fecha_factura', width=100, anchor='center')
        self.tree.column('fecha_ingreso', width=100, anchor='center')
        
        # Tags para colores
        self.tree.tag_configure('exitoso', background='#d4edda')
        self.tree.tag_configure('pendiente', background='#fff3cd')
        self.tree.tag_configure('error', background='#f8d7da')
        self.tree.tag_configure('proceso', background='#d1ecf1')
    
    
    def _get_estado_tag(self, estado_code: int) -> str:
        """Obtiene el tag de color para el estado"""
        if estado_code == 1:
            return "exitoso"
        elif estado_code == 0:
            return "pendiente"
        elif estado_code in [2, 6]:
            return "proceso"
        else:
            return "error"
    
    def _limpiar_filtros(self):
        """Limpia todos los filtros y recarga datos"""
        self.combo_estado.current(0)  # "Todos"
        
        # Resetear fechas a hoy
        self.fecha_inicio.set_date(datetime.now())
        self.fecha_fin.set_date(datetime.now())
        
        self._buscar_reporte()
    
    def _buscar_reporte(self):
        """Busca el reporte con los filtros especificados"""
        try:
            # Limpiar datos anteriores
            self.datos_reporte = []
            self._limpiar_interfaz()
            
            # Obtener valores de filtros
            estado_texto = self.estado_var.get()
            estado_codigo = self.estados_map.get(estado_texto, "")
            
            fecha_inicio_str = self.fecha_inicio.get_date().strftime('%Y-%m-%d') if hasattr(self, 'fecha_inicio') else None
            fecha_fin_str = self.fecha_fin.get_date().strftime('%Y-%m-%d') if hasattr(self, 'fecha_fin') else None
            
            # Llamar al servicio
            estado_param = int(estado_codigo) if estado_codigo != "" else None
            
            resultado = self.api_service.obtener_reporte_laboratorio(
                estado=estado_param,
                fecha_inicio=fecha_inicio_str,
                fecha_final=fecha_fin_str
            )
            
            # Verificar respuesta - validar si hay datos o si es un error real
            status_code = resultado.get('status_code', 500)
            message = resultado.get('message', '')
            description = resultado.get('description', '')
            data = resultado.get('data', [])
            
            # Si el status_code no es 200 pero hay datos, es un falso error
            # Si el message indica error o no hay data, es un error real
            if status_code != 200 and not data:
                messagebox.showerror(
                    "Error",
                    f"Error al obtener reporte:\n{description if description else 'Error desconocido'}"
                )
                # Asegurar que la interfaz quede limpia
                self._limpiar_interfaz()
                return
            
            # Guardar datos
            self.datos_reporte = data
            
            # Actualizar descripción
            self.descripcion_label.config(text=description)
            
            # Actualizar estadísticas
            self._actualizar_estadisticas()
            
            # Actualizar tabla
            self._actualizar_tabla()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar reporte: {str(e)}")
            # Limpiar interfaz en caso de error
            self.datos_reporte = []
            self._limpiar_interfaz()
    
    def _actualizar_estadisticas(self):
        """Actualiza las estadísticas basadas en los datos cargados"""
        total = len(self.datos_reporte)
        exitosos = sum(1 for d in self.datos_reporte if d.get('estadoDynamicos') == 1)
        pendientes = sum(1 for d in self.datos_reporte if d.get('estadoDynamicos') == 0)
        errores = sum(1 for d in self.datos_reporte if d.get('estadoDynamicos') not in [0, 1, 2, 6])
        
        self.total_label.config(text=str(total))
        self.exitosos_label.config(text=str(exitosos))
        self.pendientes_label.config(text=str(pendientes))
        self.errores_label.config(text=str(errores))
    
    def _actualizar_tabla(self):
        """Actualiza la tabla con los datos del reporte"""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Insertar nuevos datos
        for registro in self.datos_reporte:
            documento = registro.get('NoDocumento', '')
            tipo_doc = registro.get('Id_TipoIdentificacion', '')
            
            # Nombre completo
            nombre_completo = ' '.join(filter(None, [
                registro.get('Nombre1', ''),
                registro.get('Nombre2', ''),
                registro.get('Apellido1', ''),
                registro.get('Apellido2', '')
            ])).strip()
            
            orden_interna = registro.get('numero_orden_interna', '')
            cups = registro.get('C_Homologado', '')
            procedimiento = registro.get('Nbre', '') or registro.get('procedimiento', '')
            estado = registro.get('estadoDynamicos', '')
            descripcion_estado = registro.get('descripcion_estado', '')
            autorizacion = registro.get('NAutorizacion', '')
            fecha_factura = registro.get('fecha_factura', '')
            fecha_ingreso = registro.get('FechaIngreso', '')
            
            # Formatear fechas
            if fecha_factura:
                try:
                    # Si viene en formato ISO o con hora, extraer solo la fecha
                    if 'T' in fecha_factura or ' ' in fecha_factura:
                        fecha_factura = fecha_factura.split('T')[0].split(' ')[0]
                except:
                    pass
            
            if fecha_ingreso:
                try:
                    if 'T' in fecha_ingreso or ' ' in fecha_ingreso:
                        fecha_ingreso = fecha_ingreso.split('T')[0].split(' ')[0]
                except:
                    pass
            
            tag = self._get_estado_tag(estado)
            
            self.tree.insert(
                '',
                'end',
                values=(documento, tipo_doc, nombre_completo, orden_interna, cups, 
                        procedimiento, estado, descripcion_estado, autorizacion, 
                        fecha_factura, fecha_ingreso),
                tags=(tag,)
            )
    
    def _limpiar_interfaz(self):
        """Limpia la interfaz (estadísticas y tabla)"""
        # Limpiar estadísticas
        self.total_label.config(text="0")
        self.exitosos_label.config(text="0")
        self.pendientes_label.config(text="0")
        self.errores_label.config(text="0")
        self.descripcion_label.config(text="")
        
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def _exportar_excel(self):
        """Exporta los datos del reporte a Excel"""
        if not self.datos_reporte:
            messagebox.showwarning("Sin datos", "No hay datos para exportar. Realice primero una búsqueda.")
            return
        
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime
            
            # Solicitar ubicación de guardado
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"reporte_laboratorio_{timestamp}.csv"
            )
            
            if not filename:
                return
            
            # Escribir CSV
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                if self.datos_reporte:
                    # Obtener todas las claves del primer registro
                    headers = list(self.datos_reporte[0].keys())
                    writer = csv.DictWriter(f, fieldnames=headers)
                    
                    writer.writeheader()
                    writer.writerows(self.datos_reporte)
            
            messagebox.showinfo(
                "Éxito",
                f"Datos exportados exitosamente:\n{filename}\n\nTotal de registros: {len(self.datos_reporte)}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar datos: {str(e)}")
    
    def destroy(self):
        """Limpia recursos antes de destruir el panel"""
        if self.refresh_id:
            self.after_cancel(self.refresh_id)
        super().destroy()
