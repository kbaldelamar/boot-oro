"""
Servicio para CRUD de procedimientos_boot y lista de procedimientos activos.
"""
from typing import Dict, Optional

from services import APIClient
from utils.logger import AdvancedLogger


class ProcedimientosBootService:
    """Servicio para manejar procedimientos_boot"""

    def __init__(self, config, logger: Optional[AdvancedLogger] = None):
        self.logger = logger or AdvancedLogger()
        base_url = config.api_url_programacion_base or "http://localhost:5000"
        self.api_client = APIClient(base_url=base_url)
        self.logger.info("ProcedimientosService", f"Base URL: {base_url}")

    def listar_procedimientos(self) -> Dict:
        response = self.api_client.get("/procedimientos-boot")
        data = response.data.get("data", []) if response.data else []
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def listar_activos(self) -> Dict:
        response = self.api_client.get("/procedimientos-activos")
        data = response.data.get("data", []) if response.data else []
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def crear_procedimiento(self, payload: Dict) -> Dict:
        response = self.api_client.post("/procedimientos-boot", json_data=payload)
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def actualizar_procedimiento(self, proc_id: int, payload: Dict) -> Dict:
        response = self.api_client.put(f"/procedimientos-boot/{proc_id}", json_data=payload)
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def eliminar_procedimiento(self, proc_id: int) -> Dict:
        response = self.api_client.delete(f"/procedimientos-boot/{proc_id}")
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }
