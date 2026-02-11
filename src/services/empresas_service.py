"""
Servicio para CRUD de empresas_casos_boot.
"""
from typing import Dict, List, Optional

from services import APIClient
from utils.logger import AdvancedLogger


class EmpresasCasosBootService:
    """Servicio para manejar empresas_casos_boot"""

    def __init__(self, config, logger: Optional[AdvancedLogger] = None):
        self.logger = logger or AdvancedLogger()
        base_url = config.api_url_programacion_base or "http://localhost:5000"
        self.api_client = APIClient(base_url=base_url)
        self.logger.info("EmpresasService", f"Base URL: {base_url}")

    def listar_empresas(self) -> Dict:
        response = self.api_client.get("/empresas-casos-boot")
        data = response.data.get("data", []) if response.data else []
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def obtener_empresa(self, empresa_id: int) -> Dict:
        response = self.api_client.get(f"/empresas-casos-boot/{empresa_id}")
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def crear_empresa(self, payload: Dict) -> Dict:
        response = self.api_client.post("/empresas-casos-boot", json_data=payload)
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def actualizar_empresa(self, empresa_id: int, payload: Dict) -> Dict:
        response = self.api_client.put(f"/empresas-casos-boot/{empresa_id}", json_data=payload)
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }

    def eliminar_empresa(self, empresa_id: int) -> Dict:
        response = self.api_client.delete(f"/empresas-casos-boot/{empresa_id}")
        data = response.data.get("data", {}) if response.data else {}
        return {
            "success": response.success,
            "data": data,
            "message": response.message,
            "status_code": response.status_code,
            "error": response.error,
        }
