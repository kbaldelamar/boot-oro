"""
Servicio para operaciones con la API de Laboratorio
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config


class LaboratorioService:
    """Servicio para realizar llamadas a la API de Laboratorio"""
    
    def __init__(self):
        """Inicializa el servicio con la configuración"""
        config = Config()
        self.base_url = config.api_url_programacion_base
        
    def obtener_pacientes(
        self, 
        estado: int = 0, 
        documento: Optional[str] = None, 
        nombre: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de pacientes de laboratorio
        
        Args:
            estado: Estado del paciente (0=Pendiente, 1=Exitoso, 2=En proceso)
            documento: Número de documento para filtrar
            nombre: Nombre del paciente para filtrar
            
        Returns:
            Lista de pacientes
        """
        import requests
        
        params = {'estado': estado}
        
        if documento:
            params['documento'] = documento
        if nombre:
            params['nombre'] = nombre
            
        url = f"{self.base_url}/list-pacientes-evento"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Si la respuesta tiene una estructura con 'data' o similar
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except requests.RequestException as e:
            print(f"Error obteniendo pacientes: {e}")
            return []
    
    def obtener_procedimientos_orden(self, id_orden: int) -> List[Dict[str, Any]]:
        """
        Obtiene los procedimientos (CUPS) de una orden específica
        
        Args:
            id_orden: ID de la orden (facturaEvento)
            
        Returns:
            Lista de procedimientos con sus CUPS
        """
        import requests
        
        url = f"{self.base_url}/procedimientos-orden"
        params = {'idOrden': id_orden}
        
        try:
            print(f"[LaboratorioService] GET {url}?idOrden={id_orden}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            print(f"[LaboratorioService] Respuesta procedimientos: {data}")
            # Si la respuesta tiene estructura con 'data'
            if isinstance(data, dict) and 'data' in data:
                resultado = data['data']
                print(f"[LaboratorioService] ✓ Procedimientos encontrados: {len(resultado)}")
                return resultado
            resultado = data if isinstance(data, list) else []
            print(f"[LaboratorioService] ✓ Procedimientos (lista directa): {len(resultado)}")
            return resultado
        except requests.RequestException as e:
            print(f"[LaboratorioService] Error obteniendo procedimientos de orden {id_orden}: {e}")
            return []
    
    def actualizar_item_orden_procedimiento(
        self,
        id_orden_procedimiento: int,
        estado_dynamicos: int,
        id_item: Optional[int] = None,
        error_mensaje: Optional[str] = None,
        n_autorizacion: Optional[str] = None
    ) -> bool:
        """
        Actualiza el estado de un item de orden de procedimiento
        
        Mapeo de estados (igual que Anexo 3):
        - 0 = Pendiente (para reintentar)
        - 1 = Completado/OK 
        - 2 = En proceso
        - 3 = En proceso (con número de orden)
        - 4 = Error - tipo de documento incorrecto
        - 11 = Error - No se encontró paciente
        - 12 = Error - Sesión perdida
        - 13 = Error - Timeout
        - 14 = Error - Elemento no encontrado
        - 15 = Error - Elemento obsoleto
        - 16 = Error - Conexión/network
        - 17 = Error - PDF no encontrado
        - 18 = Error - Permisos
        - 19 = Error - No se pudo determinar resultado
        
        Args:
            id_orden_procedimiento: ID de idOrdenProcedimiento (NO facturaEvento)
            estado_dynamicos: Nuevo estado (ver mapeo arriba)
            id_item: ID del item específico (opcional)
            error_mensaje: Mensaje de error si aplica
            
        Returns:
            True si la actualización fue exitosa, False en caso contrario
        """
        import requests
        
        url = f"{self.base_url}/actualizar-item-orden-procedimiento"
        
        data = {
            'idOrden': id_orden_procedimiento,  # API espera 'idOrden', no 'idOrdenProcedimiento'
            'estadoDynamicos': estado_dynamicos
        }
        
        if id_item is not None:
            data['idItem'] = id_item
        if error_mensaje:
            data['errorMensaje'] = error_mensaje
        if n_autorizacion:
            data['nAutorizacion'] = n_autorizacion
            
        try:
            print(f"[LaboratorioService] PUT {url} - Data: {data}")
            response = requests.put(url, json=data, timeout=30)
            
            # Depurar respuesta de error
            if response.status_code != 200:
                print(f"[LaboratorioService] ❌ Status: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"[LaboratorioService] ❌ Respuesta API: {error_detail}")
                except:
                    print(f"[LaboratorioService] ❌ Respuesta texto: {response.text}")
            
            response.raise_for_status()
            print(f"[LaboratorioService] ✓ Actualización exitosa - Status: {response.status_code}")
            return True
        except requests.RequestException as e:
            print(f"[LaboratorioService] ✗ Error actualizando idOrdenProcedimiento {id_orden_procedimiento}: {e}")
            return False
    
    def marcar_como_en_proceso(self, id_orden_procedimiento: int) -> bool:
        """
        Marca una orden como en proceso (estado = 2)
        
        Args:
            id_orden_procedimiento: ID de idOrdenProcedimiento
            
        Returns:
            True si la actualización fue exitosa
        """
        return self.actualizar_item_orden_procedimiento(
            id_orden_procedimiento=id_orden_procedimiento,
            estado_dynamicos=2  # En proceso
        )
    
    def marcar_como_exitoso(self, id_orden_procedimiento: int) -> bool:
        """
        Marca una orden como exitosa (estado = 1)
        
        Args:
            id_orden_procedimiento: ID de idOrdenProcedimiento
            
        Returns:
            True si la actualización fue exitosa
        """
        return self.actualizar_item_orden_procedimiento(
            id_orden_procedimiento=id_orden_procedimiento,
            estado_dynamicos=1  # Exitoso
        )
    
    def marcar_como_pendiente(self, id_orden_procedimiento: int) -> bool:
        """
        Marca una orden como pendiente (estado = 0)
        
        Args:
            id_orden_procedimiento: ID de idOrdenProcedimiento
            
        Returns:
            True si la actualización fue exitosa
        """
        return self.actualizar_item_orden_procedimiento(
            id_orden_procedimiento=id_orden_procedimiento,
            estado_dynamicos=0  # Pendiente
        )
    
    def marcar_como_error(self, id_orden_procedimiento: int, mensaje: str) -> bool:
        """
        Marca una orden como pendiente con mensaje de error
        
        Args:
            id_orden_procedimiento: ID de idOrdenProcedimiento
            mensaje: Mensaje de error
            
        Returns:
            True si la actualización fue exitosa
        """
        return self.actualizar_item_orden_procedimiento(
            id_orden_procedimiento=id_orden_procedimiento,
            estado_dynamicos=0,  # Pendiente para reintentar
            error_mensaje=mensaje
        )
    
    def obtener_reporte_laboratorio(
        self,
        estado: Optional[int] = None,
        fecha_inicio: Optional[str] = None,
        fecha_final: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene el reporte de laboratorio con filtros opcionales
        
        Args:
            estado: Estado del paciente (opcional)
            fecha_inicio: Fecha inicio en formato YYYY-MM-DD (opcional)
            fecha_final: Fecha final en formato YYYY-MM-DD (opcional)
            
        Returns:
            Diccionario con status_code, message, description y data
        """
        import requests
        
        params = {}
        
        if estado is not None:
            params['estado'] = estado
        if fecha_inicio:
            params['fechaInicio'] = fecha_inicio
        if fecha_final:
            params['fechaFinal'] = fecha_final
            
        url = f"{self.base_url}/reporte-laboratorio"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"Error obteniendo reporte: {e}")
            return {
                "status_code": 500,
                "message": "Error",
                "description": str(e),
                "data": []
            }
