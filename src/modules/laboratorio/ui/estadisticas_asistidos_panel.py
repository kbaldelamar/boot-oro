"""
Panel de Estadísticas de Casos Asistidos en Laboratorio
Muestra métricas de casos que han sido procesados por el worker
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, Any, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config
from modules.laboratorio.services.laboratorio_service import LaboratorioService


class EstadisticasAsistidosPanel(ttk.Frame):
    """Panel para visualizar estadísticas de casos asistidos en laboratorio"""
    
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
        
        self._create_widgets()
        self._load_statistics()
        self._start_auto_refresh()
    
    def _create_widgets(self):
        """Crea todos los widgets del panel"""
        # =========================
        # ENCABEZADO
        # =========================
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = ttk.Label(
            header_frame,
            text="📈 Estadísticas - Casos Asistidos Laboratorio",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        refresh_button = ttk.Button(
            header_frame,
            text="🔄 Actualizar",
            command=self._load_statistics
        )
        refresh_button.pack(side=tk.RIGHT, padx=5)
        
        # =========================
        # MARCO DE ESTADÍSTICAS
        # =========================
        stats_container = ttk.Frame(self)
        stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Estadísticas generales
        general_frame = ttk.LabelFrame(stats_container, text="Resumen de Procesamiento", padding=15)
        general_frame.pack(fill=tk.X, pady=5)
        
        # Grid para estadísticas generales
        stats_grid = ttk.Frame(general_frame)
        stats_grid.pack(fill=tk.X)
        
        # Total asistidos
        ttk.Label(stats_grid, text="Total Asistidos:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, sticky='w', padx=10, pady=5
        )
        self.total_label = ttk.Label(stats_grid, text="0", font=('Arial', 10))
        self.total_label.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        # Casos exitosos
        ttk.Label(stats_grid, text="Exitosos:", font=('Arial', 10, 'bold')).grid(
            row=0, column=2, sticky='w', padx=10, pady=5
        )
        self.exitosos_label = ttk.Label(stats_grid, text="0", font=('Arial', 10), foreground='green')
        self.exitosos_label.grid(row=0, column=3, sticky='w', padx=10, pady=5)
        
        # Casos con error
        ttk.Label(stats_grid, text="Con Errores:", font=('Arial', 10, 'bold')).grid(
            row=1, column=0, sticky='w', padx=10, pady=5
        )
        self.errores_label = ttk.Label(stats_grid, text="0", font=('Arial', 10), foreground='red')
        self.errores_label.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        # Tasa de éxito
        ttk.Label(stats_grid, text="Tasa de Éxito:", font=('Arial', 10, 'bold')).grid(
            row=1, column=2, sticky='w', padx=10, pady=5
        )
        self.tasa_label = ttk.Label(stats_grid, text="0%", font=('Arial', 10))
        self.tasa_label.grid(row=1, column=3, sticky='w', padx=10, pady=5)
        
        # Última actualización
        ttk.Label(stats_grid, text="Última Actualización:", font=('Arial', 10, 'bold')).grid(
            row=2, column=0, sticky='w', padx=10, pady=5
        )
        self.fecha_label = ttk.Label(stats_grid, text="-", font=('Arial', 10))
        self.fecha_label.grid(row=2, column=1, columnspan=3, sticky='w', padx=10, pady=5)
        
        # =========================
        # CONTEO POR RESULTADO
        # =========================
        resultados_frame = ttk.LabelFrame(stats_container, text="Detalle por Resultado", padding=15)
        resultados_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Crear treeview para mostrar conteos por resultado
        tree_frame = ttk.Frame(resultados_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=('estado', 'descripcion', 'cantidad', 'porcentaje'),
            show='headings',
            yscrollcommand=scrollbar.set,
            height=10
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Configurar columnas
        self.tree.heading('estado', text='Estado')
        self.tree.heading('descripcion', text='Descripción')
        self.tree.heading('cantidad', text='Cantidad')
        self.tree.heading('porcentaje', text='% Asistidos')
        
        self.tree.column('estado', width=80, anchor='center')
        self.tree.column('descripcion', width=200, anchor='w')
        self.tree.column('cantidad', width=100, anchor='center')
        self.tree.column('porcentaje', width=100, anchor='center')
        
        # Tags para colores
        self.tree.tag_configure('exitoso', background='#d4edda')
        self.tree.tag_configure('error', background='#f8d7da')
        self.tree.tag_configure('proceso', background='#d1ecf1')
    
    def _get_estado_texto(self, estado_code: str) -> str:
        """Obtiene el texto descriptivo del código de estado"""
        estados_map = {
            "1": "Exitoso",
            "2": "En proceso",
            "4": "Doc incorrecto",
            "5": "PDF no encontrado",
            "6": "Solicitud activa",
            "11": "Error no clasificado",
            "12": "Sesión perdida",
            "13": "Timeout",
            "14": "Elemento no encontrado",
            "15": "Elemento obsoleto",
            "16": "Error de conexión",
            "18": "Error de permisos"
        }
        return estados_map.get(estado_code, f"Estado {estado_code}")
    
    def _get_estado_tag(self, estado_code: str) -> str:
        """Obtiene el tag de color para el estado"""
        if estado_code == "1":
            return "exitoso"
        elif estado_code in ["2", "6"]:
            return "proceso"
        else:
            return "error"
    
    def _load_statistics(self):
        """Carga las estadísticas desde la API"""
        try:
            # Obtener todos los pacientes
            pacientes = self.api_service.obtener_pacientes()
            
            if not pacientes:
                messagebox.showinfo("Sin datos", "No hay casos registrados")
                return
            
            # Filtrar solo casos asistidos (estado != 0)
            asistidos = [p for p in pacientes if str(p.get('estadoDynamicos', '0')) != '0']
            
            if not asistidos:
                self.total_label.config(text="0")
                self.exitosos_label.config(text="0")
                self.errores_label.config(text="0")
                self.tasa_label.config(text="0%")
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.fecha_label.config(text=now)
                
                # Limpiar árbol
                for item in self.tree.get_children():
                    self.tree.delete(item)
                return
            
            # Contar por estado
            conteos: Dict[str, int] = {}
            exitosos = 0
            errores = 0
            
            for paciente in asistidos:
                estado = str(paciente.get('estadoDynamicos', '0'))
                conteos[estado] = conteos.get(estado, 0) + 1
                
                if estado == "1":
                    exitosos += 1
                elif estado not in ["2", "6"]:  # Excluir "en proceso" y "solicitud activa" de errores
                    errores += 1
            
            # Actualizar totales
            total_asistidos = len(asistidos)
            self.total_label.config(text=str(total_asistidos))
            self.exitosos_label.config(text=str(exitosos))
            self.errores_label.config(text=str(errores))
            
            # Calcular tasa de éxito
            tasa = (exitosos / total_asistidos * 100) if total_asistidos > 0 else 0
            self.tasa_label.config(text=f"{tasa:.1f}%")
            
            # Actualizar fecha
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.fecha_label.config(text=now)
            
            # Limpiar árbol
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Ordenar por estado
            estados_ordenados = sorted(conteos.items(), key=lambda x: x[0])
            
            # Insertar en árbol
            for estado, cantidad in estados_ordenados:
                descripcion = self._get_estado_texto(estado)
                porcentaje = (cantidad / total_asistidos * 100) if total_asistidos > 0 else 0
                tag = self._get_estado_tag(estado)
                
                self.tree.insert(
                    '',
                    'end',
                    values=(estado, descripcion, cantidad, f"{porcentaje:.1f}%"),
                    tags=(tag,)
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar estadísticas: {str(e)}")
    
    def _start_auto_refresh(self):
        """Inicia el refresco automático cada 30 segundos"""
        self._load_statistics()
        self.refresh_id = self.after(30000, self._start_auto_refresh)
    
    def destroy(self):
        """Limpia recursos antes de destruir el panel"""
        if self.refresh_id:
            self.after_cancel(self.refresh_id)
        super().destroy()
