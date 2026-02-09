"""
Servicio para manejar la API de programación de órdenes
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime
from utils.logger import AdvancedLogger


class ProgramacionService:
    """Servicio para interactuar con API de programacion_ordenes"""
    
    def __init__(self, base_url: str = "http://localhost:5000", logger: Optional[AdvancedLogger] = None):
        """
        Args:
            base_url: URL base de la API
            logger: Logger
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logger or AdvancedLogger()
    
    def programar_orden(self, id_item_orden_proced: int, id_orden: int, usuario: str = "sistema") -> bool:
        """
        Programa una orden para automatización.
        
        Pasos:
        1. Actualiza estadoCaso a 2 (programado) en h-itemordenesproced
        2. Inserta registro en programacion_ordenes
        
        Args:
            id_item_orden_proced: ID del item de orden
            id_orden: ID de la orden
            usuario: Usuario que programa
        
        Returns:
            True si se programó exitosamente
        """
        try:
            self.logger.debug('API', f'Programando orden {id_item_orden_proced}...')
            
            # 1. Actualizar estadoCaso a 2 (programado)
            url_estado = f"{self.base_url}/h-itemordenesproced/{id_item_orden_proced}/estadoCaso"
            payload_estado = {"estadoCaso": 2}
            
            response = requests.put(url_estado, json=payload_estado, timeout=10)
            
            if response.status_code != 200:
                self.logger.error('API', f'Error actualizando estadoCaso: {response.status_code}')
                return False
            
            # 2. Insertar en programacion_ordenes
            url_prog = f"{self.base_url}/programacion-ordenes"
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            payload_prog = {
                "id_item_orden_proced": id_item_orden_proced,
                "id_orden": id_orden,
                "estado": "PENDIENTE",
                "fecha_programacion": fecha_actual,
                "intentos_maximos": 2,
                "usuario_programo": usuario
            }
            
            response = requests.post(url_prog, json=payload_prog, timeout=10)
            
            if response.status_code in [200, 201]:
                self.logger.success('API', f'✅ Orden {id_item_orden_proced} programada exitosamente')
                return True
            else:
                self.logger.error('API', f'Error insertando en programacion_ordenes: {response.status_code}')
                return False
            
        except Exception as e:
            self.logger.error('API', 'Error programando orden', e)
            return False
    
    def obtener_pendientes(self, limite: int = 100) -> List[Dict]:
        """
        Obtiene órdenes pendientes de programación.
        
        Args:
            limite: Número máximo de órdenes a obtener
        
        Returns:
            Lista de órdenes pendientes
        """
        try:
            url = f"{self.base_url}/programacion-ordenes?estado=PENDIENTE&per_page={limite}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # La estructura es: {data: {programaciones: [...]}}
                data_wrapper = data.get('data', {})
                ordenes = data_wrapper.get('programaciones', [])
                self.logger.debug('API', f'Obtenidas {len(ordenes)} órdenes pendientes')
                return ordenes
            else:
                self.logger.error('API', f'Error obteniendo pendientes: {response.status_code}')
                return []
            
        except Exception as e:
            self.logger.error('API', 'Error obteniendo pendientes', e)
            return []
    
    def actualizar_estado_programacion(
        self, 
        id_item_orden_proced: int, 
        estado: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
        usuario_ejecuto: Optional[str] = None,
        resultado: Optional[str] = None,
        mensaje_error: Optional[str] = None,
        incrementar_intentos: bool = False
    ) -> bool:
        """
        Actualiza el estado de una orden en programación.
        
        Args:
            id_item_orden_proced: ID del item
            estado: Nuevo estado (EN_PROGRESO, COMPLETADO, ERROR, etc)
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de finalización
            usuario_ejecuto: Usuario que ejecutó
            resultado: Resultado de la ejecución
            mensaje_error: Mensaje de error si aplica
            incrementar_intentos: Si incrementar contador de intentos
        
        Returns:
            True si se actualizó exitosamente
        """
        try:
            url = f"{self.base_url}/programacion-ordenes/item/{id_item_orden_proced}"
            
            payload = {"estado": estado}
            
            if incrementar_intentos:
                payload["incrementar_intentos"] = True
            if fecha_inicio:
                payload["fecha_inicio"] = fecha_inicio
            if fecha_fin:
                payload["fecha_fin"] = fecha_fin
            if usuario_ejecuto:
                payload["usuario_ejecuto"] = usuario_ejecuto
            if resultado:
                payload["resultado_ejecucion"] = resultado
            if mensaje_error:
                payload["mensaje_error"] = mensaje_error
            
            self.logger.debug('API', f'Actualizando estado: PUT {url}')
            self.logger.debug('API', f'Payload: {payload}')
            
            response = requests.put(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.success('API', f'✅ Estado actualizado a {estado} para orden {id_item_orden_proced}')
                return True
            else:
                self.logger.error('API', f'❌ Error actualizando estado: HTTP {response.status_code}')
                try:
                    error_data = response.json()
                    self.logger.error('API', f'   Respuesta: {error_data}')
                except:
                    self.logger.error('API', f'   Respuesta: {response.text}')
                return False
            
        except Exception as e:
            self.logger.error('API', f'Error actualizando estado programación para {id_item_orden_proced}', e)
            return False
    
    def actualizar_estado_caso(self, id_item_orden_proced: int, estado_caso: int) -> bool:
        """
        Actualiza el estadoCaso en h-itemordenesproced.
        
        Args:
            id_item_orden_proced: ID del item
            estado_caso: Código de estado (2=programado, 3=en proceso, 1=completado, 4=error)
        
        Returns:
            True si se actualizó exitosamente
        """
        try:
            url = f"{self.base_url}/h-itemordenesproced/{id_item_orden_proced}/estadoCaso"
            payload = {"estadoCaso": estado_caso}
            
            self.logger.debug('API', f'Actualizando estadoCaso: PUT {url}')
            self.logger.debug('API', f'Payload: {payload}')
            
            response = requests.put(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.success('API', f'✅ EstadoCaso actualizado a {estado_caso} para orden {id_item_orden_proced}')
                return True
            else:
                self.logger.error('API', f'❌ Error actualizando estadoCaso: HTTP {response.status_code}')
                try:
                    error_data = response.json()
                    self.logger.error('API', f'   Respuesta: {error_data}')
                except:
                    self.logger.error('API', f'   Respuesta: {response.text}')
                return False
            
        except Exception as e:
            self.logger.error('API', f'Error actualizando estadoCaso para {id_item_orden_proced}', e)
            return False

    def anular_orden(self, id_item_orden_proced: int) -> bool:
        """
        Anula una orden actualizando estadoCaso a 99 y limpiando numeroAutorizacion.

        Args:
            id_item_orden_proced: ID del item

        Returns:
            True si se actualizó exitosamente
        """
        try:
            url = f"{self.base_url}/h-itemordenesproced/{id_item_orden_proced}/estadoCaso"
            payload = {"estadoCaso": 99, "numeroAutorizacion": ""}

            self.logger.debug('API', f'Anulando orden: PUT {url}')
            self.logger.debug('API', f'Payload: {payload}')

            response = requests.put(url, json=payload, timeout=10)

            if response.status_code == 200:
                self.logger.success('API', f'✅ Orden {id_item_orden_proced} anulada')
                return True
            else:
                self.logger.error('API', f'❌ Error anulando orden: HTTP {response.status_code}')
                try:
                    error_data = response.json()
                    self.logger.error('API', f'   Respuesta: {error_data}')
                except:
                    self.logger.error('API', f'   Respuesta: {response.text}')
                return False

        except Exception as e:
            self.logger.error('API', f'Error anulando orden {id_item_orden_proced}', e)
            return False

    def cancelar_programacion(
        self,
        id_item_orden_proced: int,
        usuario_ejecuto: str = "worker1",
        resultado: str = "OK"
    ) -> bool:
        """
        Cancela la programacion de una orden en programacion-ordenes.

        Args:
            id_item_orden_proced: ID del item
            usuario_ejecuto: Usuario que ejecuta la cancelacion
            resultado: Resultado de la ejecucion

        Returns:
            True si se actualizo exitosamente
        """
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return self.actualizar_estado_programacion(
            id_item_orden_proced=id_item_orden_proced,
            estado="cancelado",
            fecha_inicio=fecha_actual,
            fecha_fin=fecha_actual,
            usuario_ejecuto=usuario_ejecuto,
            resultado=resultado
        )
    
    def obtener_datos_orden(self, id_item_orden_proced: int) -> Optional[Dict]:
        """
        Obtiene los datos completos de una orden desde lis-pacientes-ordeneshc.
        
        Args:
            id_item_orden_proced: ID del item de orden (idItemOrden)
        
        Returns:
            Diccionario con datos del paciente o None si no se encuentra
        """
        try:
            # Endpoint específico por idItemOrden
            url = f"{self.base_url}/lis-pacientes-ordeneshc/{id_item_orden_proced}"
            
            self.logger.debug('API', f'Solicitando datos: GET {url}')
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # La estructura es: {data: {Nombre1, Apellido1, ...}}
                orden = data.get('data')
                
                if orden:
                    self.logger.debug('API', f'✅ Datos de orden {id_item_orden_proced} obtenidos')
                    self.logger.debug('API', f'   Paciente: {orden.get("Nombre1")} {orden.get("Apellido1")} - Doc: {orden.get("NoDocumento")}')
                    return orden
                else:
                    self.logger.warning('API', f'Respuesta sin datos para orden {id_item_orden_proced}')
                    return None
            else:
                self.logger.error('API', f'Error obteniendo datos orden: HTTP {response.status_code}')
                return None
            
        except Exception as e:
            self.logger.error('API', f'Error obteniendo datos orden {id_item_orden_proced}', e)
            return None
