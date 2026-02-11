"""
Servicio específico del módulo Autorizar Anexo 3.
Maneja la lógica de negocio para órdenes HC.
"""
from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services import APIClient
from utils.logger import AdvancedLogger


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
        base_url = config.api_url_programacion_base or 'http://localhost:5000'
        self.api_client = APIClient(base_url=base_url)
        self.logger = AdvancedLogger()
        self.logger.info('OrdenesService', f'Inicializado - base_url: {base_url}')
    
    def obtener_ordenes_hc(
        self,
        estado_caso: Optional[int] = None,
        nombre: Optional[str] = None,
        documento: Optional[str] = None
    ) -> Dict:
        """
        Obtiene todas las órdenes HC desde el API.
        
        Returns:
            Respuesta del API con las órdenes
        """
        params = []
        if estado_caso is not None:
            params.append(f"estadoCaso={estado_caso}")
        if nombre:
            params.append(f"nombre={nombre}")
        if documento:
            params.append(f"documento={documento}")

        if params:
            endpoint = f"/lis-pacientes-ordeneshc?{'&'.join(params)}"
        else:
            endpoint = "/lis-pacientes-ordeneshc"

        full_url = f"{self.api_client.base_url}{endpoint}"
        self.logger.info('OrdenesService', f'GET {full_url}')

        response = self.api_client.get(endpoint)
        
        self.logger.info('OrdenesService', f'HTTP {response.status_code} - success: {response.success}')
        data_list = response.data.get('data', []) if response.data else []
        self.logger.info('OrdenesService', f'Registros recibidos: {len(data_list)}')
        if response.error:
            self.logger.error('OrdenesService', f'Error: {response.error}')
        if not response.success:
            self.logger.warning('OrdenesService', f'Mensaje: {response.message}')

        return {
            'success': response.success,
            'data': data_list,
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
