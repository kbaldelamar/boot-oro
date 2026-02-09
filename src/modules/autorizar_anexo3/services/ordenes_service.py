"""
Servicio específico del módulo Autorizar Anexo 3.
Maneja la lógica de negocio para órdenes HC.
"""
from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services import APIClient


class AutorizarAnexo3Service:
    """
    Servicio para manejar la lógica de autorización de anexo 3.
    """
    
    def __init__(self, config):
        """
        Inicializa el servicio.
        
        Args:
            config: Instancia de configuración
        """
        self.config = config
        self.api_client = APIClient(base_url="http://localhost:5000")
    
    def obtener_ordenes_hc(self, estado_caso: Optional[int] = None) -> Dict:
        """
        Obtiene todas las órdenes HC desde el API.
        
        Returns:
            Respuesta del API con las órdenes
        """
        if estado_caso is None:
            endpoint = "/lis-pacientes-ordeneshc"
        else:
            endpoint = f"/lis-pacientes-ordeneshc?estadoCaso={estado_caso}"

        response = self.api_client.get(endpoint)
        return {
            'success': response.success,
            'data': response.data.get('data', []) if response.data else [],
            'message': response.message,
            'status_code': response.status_code,
            'error': response.error
        }
    
    def formatear_orden_para_tabla(self, orden: Dict) -> tuple:
        """
        Formatea una orden para mostrar en la tabla.
        
        Args:
            orden: Diccionario con datos de la orden
            
        Returns:
            Tupla con los valores formateados
        """
        # Construir nombre completo del paciente
        nombre_completo = f"{orden.get('Nombre1', '')} {orden.get('Nombre2', '')} {orden.get('Apellido1', '')} {orden.get('Apellido2', '')}".strip()
        
        # Formatear fecha
        fecha_orden = orden.get('FechaOrden', '')
        if fecha_orden and ',' in fecha_orden:
            try:
                partes = fecha_orden.split(',')[1].strip().split(' ')
                fecha_orden = f"{partes[0]} {partes[1]} {partes[2]}"
            except:
                pass
        
        # Estado como texto
        estado = "Pendiente" if orden.get('estadoCaso', 0) == 0 else "Procesado"
        
        return (
            orden.get('idOrden', ''),
            orden.get('idItemOrden', ''),
            orden.get('NoDocumento', ''),
            nombre_completo,
            orden.get('cups', ''),
            orden.get('procedimiento', ''),
            fecha_orden,
            estado,
            orden.get('telefono', '').strip()
        )
    
    def close(self):
        """Cierra las conexiones del cliente API"""
        if hasattr(self, 'api_client'):
            self.api_client.close()
