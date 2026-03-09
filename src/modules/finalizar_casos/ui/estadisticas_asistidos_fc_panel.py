"""
Panel de Estadísticas de Casos Asistidos - Finalizar Casos Laboratorio
Usa el endpoint /reporte-laboratorio-finalizado
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
from modules.finalizar_casos.services.finalizar_casos_service import FinalizarCasosService


class EstadisticasAsistidosFCPanel(ttk.Frame):
    """Panel para visualizar estadísticas de casos asistidos en Finalizar Casos"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.global_config = Config()
        self.api_service = FinalizarCasosService()
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
            text="📊 Estadísticas - Casos Asistidos Finalizar Casos",
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
            ("Finalizado plataforma", "3"),
            ("Error general", "4"),
            ("Sin PDF remisión", "5"),
            ("Sin PDF resultados", "6"),
            ("Error crítico", "7"),
            ("Error captura evidencia", "8"),
            ("Error PDF evidencia", "9"),
            ("Error crear registro", "10"),
            ("Error renombrar", "11"),
            ("Error SMB", "12"),
            ("Error actualizar ruta", "13"),
            ("Remisión no encontrada SMB", "14"),
            ("Error API remisión", "15"),
        ]

        self.combo_estado = ttk.Combobox(
            fila1,
            textvariable=self.estado_var,
            values=[e[0] for e in estados],
            state='readonly',
            width=30
        )
        self.combo_estado.pack(side=tk.LEFT, padx=5)
        self.combo_estado.current(0)

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
        if estado_code == 1:
            return "exitoso"
        elif estado_code == 0:
            return "pendiente"
        elif estado_code in [2, 3]:
            return "proceso"
        else:
            return "error"

    def _limpiar_filtros(self):
        self.combo_estado.current(0)
        self.fecha_inicio.set_date(datetime.now())
        self.fecha_fin.set_date(datetime.now())
        self._buscar_reporte()

    def _buscar_reporte(self):
        try:
            self.datos_reporte = []
            self._limpiar_interfaz()

            estado_texto = self.estado_var.get()
            estado_codigo = self.estados_map.get(estado_texto, "")

            fecha_inicio_str = self.fecha_inicio.get_date().strftime('%Y-%m-%d')
            fecha_fin_str = self.fecha_fin.get_date().strftime('%Y-%m-%d')

            estado_param = int(estado_codigo) if estado_codigo != "" else None

            resultado = self.api_service.obtener_reporte_finalizado(
                estado=estado_param,
                fecha_inicio=fecha_inicio_str,
                fecha_final=fecha_fin_str
            )

            status_code = resultado.get('status_code', 500)
            description = resultado.get('description', '')
            data = resultado.get('data', [])

            if status_code != 200 and not data:
                messagebox.showerror(
                    "Error",
                    f"Error al obtener reporte:\n{description if description else 'Error desconocido'}"
                )
                self._limpiar_interfaz()
                return

            self.datos_reporte = data
            self.descripcion_label.config(text=description)
            self._actualizar_estadisticas()
            self._actualizar_tabla()

        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar reporte: {str(e)}")
            self.datos_reporte = []
            self._limpiar_interfaz()

    def _actualizar_estadisticas(self):
        total = len(self.datos_reporte)
        exitosos = sum(1 for d in self.datos_reporte if d.get('citasAsistidaDynamicos') == 1)
        pendientes = sum(1 for d in self.datos_reporte if d.get('citasAsistidaDynamicos') == 0)
        errores = sum(1 for d in self.datos_reporte if d.get('citasAsistidaDynamicos') not in [0, 1, 2, 3])

        self.total_label.config(text=str(total))
        self.exitosos_label.config(text=str(exitosos))
        self.pendientes_label.config(text=str(pendientes))
        self.errores_label.config(text=str(errores))

    def _actualizar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for registro in self.datos_reporte:
            documento = registro.get('NoDocumento', '')
            tipo_doc = registro.get('Id_TipoIdentificacion', '')

            nombre_completo = ' '.join(filter(None, [
                registro.get('Nombre1', ''),
                registro.get('Nombre2', ''),
                registro.get('Apellido1', ''),
                registro.get('Apellido2', '')
            ])).strip()

            orden_interna = registro.get('numero_orden_interna', '')
            cups = registro.get('C_Homologado', '')
            procedimiento = registro.get('Nbre', '') or registro.get('procedimiento', '')
            estado = registro.get('citasAsistidaDynamicos', '')
            descripcion_estado = registro.get('descripcion_estado', '')
            autorizacion = registro.get('NAutorizacion', '')
            fecha_factura = registro.get('fecha_factura', '')
            fecha_ingreso = registro.get('FechaIngreso', '')

            if fecha_factura:
                try:
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
        self.total_label.config(text="0")
        self.exitosos_label.config(text="0")
        self.pendientes_label.config(text="0")
        self.errores_label.config(text="0")
        self.descripcion_label.config(text="")

        for item in self.tree.get_children():
            self.tree.delete(item)

    def _exportar_excel(self):
        if not self.datos_reporte:
            messagebox.showwarning("Sin datos", "No hay datos para exportar. Realice primero una búsqueda.")
            return

        try:
            from tkinter import filedialog
            import csv

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"reporte_fc_asistidos_{timestamp}.csv"
            )

            if not filename:
                return

            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                if self.datos_reporte:
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
        if self.refresh_id:
            self.after_cancel(self.refresh_id)
        super().destroy()
