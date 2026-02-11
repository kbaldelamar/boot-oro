"""
Panel para administrar empresas_casos_boot.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from services.empresas_service import EmpresasCasosBootService
from utils.logger import AdvancedLogger


class EmpresasCasosBootPanel(ttk.Frame):
    """Panel CRUD para empresas_casos_boot"""

    def __init__(self, parent, config: Config):
        super().__init__(parent)
        self.config = config
        self.logger = AdvancedLogger()
        self.service = EmpresasCasosBootService(config, logger=self.logger)

        self._build_ui()
        self._load_empresas()

    def _build_ui(self):
        title = ttk.Label(self, text="Empresas (casos boot)", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        form_frame = ttk.LabelFrame(self, text="Datos", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="ID").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.id_var = tk.StringVar()
        self.id_label = ttk.Label(form_frame, textvariable=self.id_var, width=10, foreground="gray")
        self.id_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)

        ttk.Label(form_frame, text="nombreIps").grid(row=0, column=2, sticky=tk.W, padx=5, pady=4)
        self.nombre_var = tk.StringVar()
        self.nombre_entry = ttk.Entry(form_frame, textvariable=self.nombre_var, width=50)
        self.nombre_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=4)

        ttk.Label(form_frame, text="sede").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        self.sede_var = tk.StringVar()
        self.sede_entry = ttk.Entry(form_frame, textvariable=self.sede_var, width=30)
        self.sede_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)

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

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Crear", command=self._crear).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Actualizar", command=self._actualizar).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Eliminar", command=self._eliminar).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Limpiar", command=self._limpiar).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="Refrescar", command=self._load_empresas).pack(side=tk.LEFT, padx=4)

        self.result_label = ttk.Label(self, text="", foreground="gray")
        self.result_label.pack(pady=3)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("id", "nombreIps", "sede", "estado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.heading("nombreIps", text="nombreIps")
        self.tree.heading("sede", text="sede")
        self.tree.heading("estado", text="estado")
        self.tree.column("id", width=60, anchor=tk.W)
        self.tree.column("nombreIps", width=420, anchor=tk.W)
        self.tree.column("sede", width=180, anchor=tk.W)
        self.tree.column("estado", width=80, anchor=tk.W)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_empresas(self):
        self.result_label.config(text="Cargando...", foreground="gray")
        for item in self.tree.get_children():
            self.tree.delete(item)

        result = self.service.listar_empresas()
        if not result.get("success"):
            msg = result.get("message", "Error")
            self.result_label.config(text=msg, foreground="red")
            self.logger.error("EmpresasUI", f"Error listando: {result}")
            return

        for row in result.get("data", []):
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row.get("id", ""),
                    row.get("nombreIps", ""),
                    row.get("sede", ""),
                    str(row.get("estado", 0))
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
        self.nombre_var.set(values[1])
        self.sede_var.set(values[2])
        self.estado_var.set(str(values[3]))

    def _crear(self):
        payload = self._payload_from_form()
        if not payload.get("nombreIps"):
            messagebox.showwarning("Validacion", "nombreIps es obligatorio")
            return
        result = self.service.crear_empresa(payload)
        if result.get("success"):
            self.result_label.config(text="Creado", foreground="green")
            self._load_empresas()
        else:
            msg = result.get("message", "Error creando")
            self.result_label.config(text=msg, foreground="red")

    def _actualizar(self):
        empresa_id = self.id_var.get().strip()
        if not empresa_id:
            messagebox.showwarning("Validacion", "Seleccione una empresa")
            return
        payload = self._payload_from_form()
        result = self.service.actualizar_empresa(int(empresa_id), payload)
        if result.get("success"):
            self.result_label.config(text="Actualizado", foreground="green")
            self._load_empresas()
        else:
            msg = result.get("message", "Error actualizando")
            self.result_label.config(text=msg, foreground="red")

    def _eliminar(self):
        empresa_id = self.id_var.get().strip()
        if not empresa_id:
            messagebox.showwarning("Validacion", "Seleccione una empresa")
            return
        if not messagebox.askyesno("Eliminar", "Desea eliminar esta empresa?"):
            return
        result = self.service.eliminar_empresa(int(empresa_id))
        if result.get("success"):
            self.result_label.config(text="Eliminado", foreground="green")
            self._limpiar()
            self._load_empresas()
        else:
            msg = result.get("message", "Error eliminando")
            self.result_label.config(text=msg, foreground="red")

    def _payload_from_form(self) -> dict:
        return {
            "nombreIps": self.nombre_var.get().strip(),
            "sede": self.sede_var.get().strip(),
            "estado": int(self.estado_var.get().strip() or "0"),
        }

    def _limpiar(self):
        self.id_var.set("")
        self.nombre_var.set("")
        self.sede_var.set("")
        self.estado_var.set("1")
        self.result_label.config(text="", foreground="gray")
        self.tree.selection_remove(self.tree.selection())
