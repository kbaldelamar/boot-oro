"""
Panel para administrar procedimientos_boot.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from services.procedimientos_service import ProcedimientosBootService
from services.empresas_service import EmpresasCasosBootService
from utils.logger import AdvancedLogger


class ProcedimientosBootPanel(ttk.Frame):
    """Panel CRUD para procedimientos_boot"""

    def __init__(self, parent, config: Config):
        super().__init__(parent)
        self.config = config
        self.logger = AdvancedLogger()
        self.service = ProcedimientosBootService(config, logger=self.logger)
        self.empresas_service = EmpresasCasosBootService(config, logger=self.logger)

        self.activos = []
        self.activos_display = []
        self.empresas = []
        self.empresas_display = []

        self._build_ui()
        self._load_activos()
        self._load_empresas()
        self._load_procedimientos()

    def _build_ui(self):
        title = ttk.Label(self, text="Procedimientos (boot)", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        form_frame = ttk.LabelFrame(self, text="Datos", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="Procedimiento activo").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.activo_var = tk.StringVar()
        self.activo_combo = ttk.Combobox(form_frame, textvariable=self.activo_var, width=80)
        self.activo_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)
        self.activo_combo.bind("<<ComboboxSelected>>", self._on_activo_select)
        self.activo_combo.bind("<KeyRelease>", self._on_activo_typed)

        ttk.Label(form_frame, text="ID").grid(row=0, column=2, sticky=tk.W, padx=5, pady=4)
        self.id_var = tk.StringVar()
        self.id_label = ttk.Label(form_frame, textvariable=self.id_var, width=12, foreground="gray")
        self.id_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=4)

        ttk.Label(form_frame, text="cups").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        self.cups_var = tk.StringVar()
        self.cups_entry = ttk.Entry(form_frame, textvariable=self.cups_var, width=20)
        self.cups_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)

        ttk.Label(form_frame, text="estado").grid(row=1, column=2, sticky=tk.W, padx=5, pady=4)
        self.estado_var = tk.StringVar(value="1")
        self.estado_combo = ttk.Combobox(
            form_frame,
            textvariable=self.estado_var,
            values=["0", "1"],
            width=5,
            state="readonly"
        )
        self.estado_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=4)

        ttk.Label(form_frame, text="Empresa").grid(row=2, column=0, sticky=tk.W, padx=5, pady=4)
        self.empresa_var = tk.StringVar()
        self.empresa_combo = ttk.Combobox(form_frame, textvariable=self.empresa_var, width=40, state="readonly")
        self.empresa_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=4)
        self.empresa_combo.bind("<<ComboboxSelected>>", self._on_empresa_select)

        ttk.Label(form_frame, text="idEmpresa").grid(row=2, column=2, sticky=tk.W, padx=5, pady=4)
        self.id_empresa_var = tk.StringVar(value="0")
        self.id_empresa_label = ttk.Label(form_frame, textvariable=self.id_empresa_var, width=10, foreground="gray")
        self.id_empresa_label.grid(row=2, column=3, sticky=tk.W, padx=5, pady=4)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Crear", command=self._crear).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Actualizar", command=self._actualizar).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Eliminar", command=self._eliminar).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Limpiar", command=self._limpiar).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Refrescar", command=self._refresh_all).pack(side=tk.LEFT, padx=4)

        self.result_label = ttk.Label(self, text="", foreground="gray")
        self.result_label.pack(pady=3)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("id", "cups", "estado", "idEmpresa")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("cups", text="cups")
        self.tree.heading("estado", text="estado")
        self.tree.heading("idEmpresa", text="idEmpresa")
        self.tree.column("id", width=100, anchor=tk.W)
        self.tree.column("cups", width=150, anchor=tk.W)
        self.tree.column("estado", width=80, anchor=tk.W)
        self.tree.column("idEmpresa", width=100, anchor=tk.W)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_all(self):
        self._load_activos()
        self._load_empresas()
        self._load_procedimientos()

    def _load_activos(self):
        result = self.service.listar_activos()
        if not result.get("success"):
            msg = result.get("message", "Error")
            self.result_label.config(text=msg, foreground="red")
            self.logger.error("ProcedimientosUI", f"Error listando activos: {result}")
            self.activos = []
            self.activos_display = []
            self.activo_combo["values"] = []
            return

        self.activos = result.get("data", [])
        self.activos_display = [self._format_activo(a) for a in self.activos]
        self.activo_combo["values"] = self.activos_display

    def _load_empresas(self):
        """Cargar empresas desde el servicio"""
        result = self.empresas_service.listar_empresas()
        if not result.get("success"):
            msg = result.get("message", "Error cargando empresas")
            self.logger.error("ProcedimientosUI", f"Error listando empresas: {result}")
            self.empresas = []
            self.empresas_display = []
            self.empresa_combo["values"] = []
            return

        self.empresas = result.get("data", [])
        self.empresas_display = [self._format_empresa(e) for e in self.empresas]
        self.empresa_combo["values"] = self.empresas_display
        
        # Seleccionar la primera empresa por defecto si hay empresas disponibles
        if self.empresas_display:
            self.empresa_combo.current(0)
            self._on_empresa_select()

    def _load_procedimientos(self):
        self.result_label.config(text="Cargando...", foreground="gray")
        for item in self.tree.get_children():
            self.tree.delete(item)

        result = self.service.listar_procedimientos()
        if not result.get("success"):
            msg = result.get("message", "Error")
            self.result_label.config(text=msg, foreground="red")
            self.logger.error("ProcedimientosUI", f"Error listando: {result}")
            return

        for row in result.get("data", []):
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row.get("id", ""),
                    row.get("cups", ""),
                    str(row.get("estado", 0)),
                    row.get("idEmpresa", 0)
                )
            )

        self.result_label.config(text=f"Registros: {len(result.get('data', []))}", foreground="green")

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item.get("values", [])
        if len(values) < 4:
            return
        self.id_var.set(values[0])
        self.cups_var.set(values[1])
        self.estado_var.set(str(values[2]))
        
        # Buscar y seleccionar la empresa correspondiente al idEmpresa
        id_empresa_str = str(values[3])
        self.id_empresa_var.set(id_empresa_str)
        self._select_empresa_by_id(id_empresa_str)

    def _on_activo_select(self, _event=None):
        selected = self.activo_var.get().strip()
        activo = self._find_activo(selected)
        if not activo:
            return
        proc_id = activo.get("id") or activo.get("Id") or ""
        cups = activo.get("cups") or activo.get("C_Homologado") or ""
        self.id_var.set(proc_id)
        self.cups_var.set(cups)

    def _on_activo_typed(self, _event=None):
        term = self.activo_var.get().strip().lower()
        if not term:
            self.activo_combo["values"] = self.activos_display
            return
        filtered = [v for v in self.activos_display if term in v.lower()]
        self.activo_combo["values"] = filtered

    def _find_activo(self, display: str) -> dict:
        for idx, item in enumerate(self.activos_display):
            if item == display and idx < len(self.activos):
                return self.activos[idx]
        return {}
    
    def _format_empresa(self, empresa: dict) -> str:
        """Formatear empresa para mostrar en el combo"""
        empresa_id = empresa.get("id", "")
        nombre_ips = empresa.get("nombreIps", "")
        sede = empresa.get("sede", "")
        
        # Formato: "ID - nombreIps (sede)" o "ID - nombreIps" si no hay sede
        display = f"{empresa_id}"
        if nombre_ips:
            display += f" - {nombre_ips}"
        if sede:
            display += f" ({sede})"
        return display
    
    def _find_empresa(self, display: str) -> dict:
        """Encontrar empresa por texto mostrado"""
        for idx, item in enumerate(self.empresas_display):
            if item == display and idx < len(self.empresas):
                return self.empresas[idx]
        return {}
    
    def _select_empresa_by_id(self, empresa_id: str):
        """Seleccionar empresa en el combo por ID"""
        for idx, empresa in enumerate(self.empresas):
            if str(empresa.get("id", "")) == empresa_id:
                if idx < len(self.empresas_display):
                    self.empresa_combo.current(idx)
                    self.empresa_var.set(self.empresas_display[idx])
                    break
        else:
            # Si no se encuentra la empresa, limpiar selection
            self.empresa_combo.set("")
    
    def _on_empresa_select(self, _event=None):
        """Manejar selección de empresa"""
        selected = self.empresa_var.get().strip()
        empresa = self._find_empresa(selected)
        if empresa:
            self.id_empresa_var.set(str(empresa.get("id", "0")))
        else:
            self.id_empresa_var.set("0")

    def _format_activo(self, activo: dict) -> str:
        proc_id = activo.get("id") or activo.get("Id") or ""
        nombre = activo.get("nombre") or activo.get("Nbre") or ""
        cups = activo.get("cups") or activo.get("C_Homologado") or ""
        parts = [str(proc_id).strip()]
        if nombre:
            parts.append(str(nombre).strip())
        display = " - ".join([p for p in parts if p])
        if cups:
            return f"{display} ({cups})" if display else f"{proc_id} ({cups})"
        return display or str(proc_id)

    def _crear(self):
        payload = self._payload_from_form()
        if payload.get("id") in (None, ""):
            messagebox.showwarning("Validacion", "Debe seleccionar un procedimiento activo")
            return
        result = self.service.crear_procedimiento(payload)
        if result.get("success"):
            self.result_label.config(text="Creado", foreground="green")
            self._load_procedimientos()
        else:
            msg = result.get("message", "Error creando")
            self.result_label.config(text=msg, foreground="red")

    def _actualizar(self):
        proc_id = self.id_var.get().strip()
        if not proc_id:
            messagebox.showwarning("Validacion", "Seleccione un procedimiento")
            return
        payload = self._payload_from_form(include_id=False)
        result = self.service.actualizar_procedimiento(int(proc_id), payload)
        if result.get("success"):
            self.result_label.config(text="Actualizado", foreground="green")
            self._load_procedimientos()
        else:
            msg = result.get("message", "Error actualizando")
            self.result_label.config(text=msg, foreground="red")

    def _eliminar(self):
        proc_id = self.id_var.get().strip()
        if not proc_id:
            messagebox.showwarning("Validacion", "Seleccione un procedimiento")
            return
        if not messagebox.askyesno("Eliminar", "Desea eliminar este procedimiento?"):
            return
        result = self.service.eliminar_procedimiento(int(proc_id))
        if result.get("success"):
            self.result_label.config(text="Eliminado", foreground="green")
            self._limpiar()
            self._load_procedimientos()
        else:
            msg = result.get("message", "Error eliminando")
            self.result_label.config(text=msg, foreground="red")

    def _payload_from_form(self, include_id: bool = True) -> dict:
        proc_id = self.id_var.get().strip()
        cups = self.cups_var.get().strip()
        estado = self.estado_var.get().strip() or "0"
        id_empresa = self.id_empresa_var.get().strip() or "0"

        payload = {
            "cups": cups,
            "estado": int(estado),
            "idEmpresa": int(id_empresa)
        }
        if include_id:
            payload["id"] = int(proc_id) if proc_id else None
        return payload

    def _limpiar(self):
        self.activo_var.set("")
        self.id_var.set("")
        self.cups_var.set("")
        self.estado_var.set("1")
        self.empresa_var.set("")
        self.id_empresa_var.set("0")
        self.result_label.config(text="", foreground="gray")
        self.tree.selection_remove(self.tree.selection())
