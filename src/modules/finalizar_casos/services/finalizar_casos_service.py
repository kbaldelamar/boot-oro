"""
Servicio para operaciones con la API de Finalizar Casos Laboratorio.
Consume los endpoints:
  - GET  /pacientes-casos
  - PUT  /actualizar-item-orden-procedimiento
  - GET  /buscar-pdf-remision
  - GET  /consulta-encabezado
"""
import requests
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config.config import Config


class FinalizarCasosService:
    """Servicio para realizar llamadas a la API de Finalizar Casos Laboratorio"""

    def __init__(self):
        """Inicializa el servicio con la configuración del .env"""
        config = Config()
        self.base_url = config.api_url_programacion_base or 'http://localhost:5000'

    # ------------------------------------------------------------------
    # Obtener casos
    # ------------------------------------------------------------------

    def obtener_casos(
        self,
        id_orden: Optional[int] = None,
        id_ingreso: Optional[int] = None,
        caso: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de casos desde /pacientes-casos.

        Args:
            id_orden: Filtrar por ID de orden (opcional)
            id_ingreso: Filtrar por ID de ingreso (opcional)
            caso: Texto libre para filtrar por caso/radicado (opcional)

        Returns:
            Lista de casos
        """
        url = f"{self.base_url}/pacientes-casos"
        params: Dict[str, Any] = {}

        if id_orden is not None:
            params['idOrden'] = id_orden
        if id_ingreso is not None:
            params['idIngreso'] = id_ingreso
        if caso:
            params['caso'] = caso

        print(f"\n[FinalizarCasosService] GET {url}")
        print(f"[FinalizarCasosService] Params: {params}")

        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"[FinalizarCasosService] Status: {response.status_code}")
            print(f"[FinalizarCasosService] URL completa: {response.url}")
            response.raise_for_status()

            data = response.json()

            # Aceptar lista directa o estructura { data: [...] }
            if isinstance(data, dict) and 'data' in data:
                resultado = data['data']
            elif isinstance(data, list):
                resultado = data
            else:
                resultado = []

            print(f"[FinalizarCasosService] Registros: {len(resultado)}")
            return resultado

        except requests.RequestException as e:
            print(f"[FinalizarCasosService] ERROR: {e}")
            return []

    # ------------------------------------------------------------------
    # Actualizar estado de caso
    # ------------------------------------------------------------------

    def actualizar_caso(
        self,
        id_orden: int,
        estado: int,
    ) -> bool:
        """
        Actualiza el estado de un caso vía PUT /actualizar-item-orden-procedimiento.

        Args:
            id_orden: ID de la orden
            estado: Valor numérico de citasAsistidaDynamicos
                0=Pendiente, 1=Exitoso, 2=EnProceso, 3=FinalizadoPlataforma,
                4=ErrorGeneral, 5=SinPDFRemision, 6=SinPDFResultados, 7=ErrorCritico

        Returns:
            True si la actualización fue exitosa
        """
        url = f"{self.base_url}/actualizar-item-orden-procedimiento"
        payload = {
            'idOrden': id_orden,
            'citasAsistidaDynamicos': estado
        }

        try:
            import json
            print(f"[FinalizarCasosService] PUT {url}")
            print(f"[FinalizarCasosService] Payload: {json.dumps(payload, indent=2)}")
            response = requests.put(url, json=payload, timeout=30)

            if response.status_code != 200:
                print(f"[FinalizarCasosService] Error status: {response.status_code}")
                try:
                    print(f"[FinalizarCasosService] Resp: {response.json()}")
                except Exception:
                    print(f"[FinalizarCasosService] Resp text: {response.text}")

            response.raise_for_status()
            print(f"[FinalizarCasosService] Actualización OK idOrden={id_orden} estado={estado}")
            return True
        except requests.RequestException as e:
            print(f"[FinalizarCasosService] Error actualizando caso {id_orden}: {e}")
            return False

    # ------------------------------------------------------------------
    # Métodos convenience de estado
    # ------------------------------------------------------------------

    def marcar_pendiente(self, id_orden: int) -> bool:
        """Estado 0: Pendiente"""
        return self.actualizar_caso(id_orden, estado=0)

    def marcar_exitoso(self, id_orden: int) -> bool:
        """Estado 1: Exitoso"""
        return self.actualizar_caso(id_orden, estado=1)

    def marcar_en_proceso(self, id_orden: int) -> bool:
        """Estado 2: En proceso"""
        return self.actualizar_caso(id_orden, estado=2)

    def marcar_finalizado_plataforma(self, id_orden: int) -> bool:
        """Estado 3: Confirmado como finalizado en la plataforma"""
        return self.actualizar_caso(id_orden, estado=3)

    def marcar_error(self, id_orden: int) -> bool:
        """Estado 4: Error general"""
        return self.actualizar_caso(id_orden, estado=4)

    def marcar_sin_pdf_remision(self, id_orden: int) -> bool:
        """Estado 5: PDF de remisión no encontrado"""
        return self.actualizar_caso(id_orden, estado=5)

    def marcar_sin_pdf_resultados(self, id_orden: int) -> bool:
        """Estado 6: PDF de resultados no encontrado"""
        return self.actualizar_caso(id_orden, estado=6)

    def marcar_error_critico(self, id_orden: int) -> bool:
        """Estado 7: Error crítico (navegador cerrado, etc.)"""
        return self.actualizar_caso(id_orden, estado=7)

    def marcar_error_captura_evidencia(self, id_orden: int) -> bool:
        """Estado 8: Error capturando screenshot de evidencia"""
        return self.actualizar_caso(id_orden, estado=8)

    def marcar_error_pdf_evidencia(self, id_orden: int) -> bool:
        """Estado 9: Error generando PDF de evidencia (PNG→PDF)"""
        return self.actualizar_caso(id_orden, estado=9)

    def marcar_error_crear_registro(self, id_orden: int) -> bool:
        """Estado 10: Error creando registro en /ingreso-documento"""
        return self.actualizar_caso(id_orden, estado=10)

    def marcar_error_renombrar(self, id_orden: int) -> bool:
        """Estado 11: Error renombrando archivo de evidencia"""
        return self.actualizar_caso(id_orden, estado=11)

    def marcar_error_smb(self, id_orden: int) -> bool:
        """Estado 12: Error subiendo archivo a servidor SMB"""
        return self.actualizar_caso(id_orden, estado=12)

    def marcar_error_actualizar_ruta(self, id_orden: int) -> bool:
        """Estado 13: Error actualizando ruta en /ingreso-documento"""
        return self.actualizar_caso(id_orden, estado=13)

    def marcar_remision_no_encontrada_smb(self, id_orden: int) -> bool:
        """Estado 14: PDF de remisión no encontrado en servidor SMB"""
        return self.actualizar_caso(id_orden, estado=14)

    def marcar_error_api_remision(self, id_orden: int) -> bool:
        """Estado 15: Error en API /buscar-pdf-remision (500/400/sin respuesta)"""
        return self.actualizar_caso(id_orden, estado=15)

    # ------------------------------------------------------------------
    # Ingreso Documento (evidencias)
    # ------------------------------------------------------------------

    def crear_ingreso_documento(
        self,
        id_ingreso: int,
        id_tipo_doc: int = 6,
        usuario: str = "robot"
    ) -> Optional[Dict[str, Any]]:
        """
        Crea un registro de documento de ingreso.
        POST /ingreso-documento

        Returns:
            Dict con la respuesta completa { data: { Id, ... }, statusCode, message }
            o None si hubo error.
        """
        url = f"{self.base_url}/ingreso-documento"
        from datetime import datetime
        payload = {
            "Id_Ingreso": id_ingreso,
            "IdTipoDoc": id_tipo_doc,
            "UsuarioS": usuario,
            "Estado": 1,
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Id_Remoto": 0
        }

        try:
            import json
            print(f"[FinalizarCasosService] POST {url}")
            print(f"[FinalizarCasosService] Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, json=payload, timeout=30)
            print(f"[FinalizarCasosService] Status crear_ingreso_documento: {response.status_code}")

            data = response.json()
            print(f"[FinalizarCasosService] Response: {data}")
            return data

        except requests.RequestException as e:
            print(f"[FinalizarCasosService] Error creando ingreso documento: {e}")
            return None

    def actualizar_ruta_documento(
        self,
        id_documento: int,
        ruta: str
    ) -> bool:
        """
        Actualiza la ruta del documento de ingreso.
        PUT /ingreso-documento/{id}

        Args:
            id_documento: ID del documento (retornado por crear_ingreso_documento)
            ruta: Nombre/ruta del PDF final

        Returns:
            True si la actualización fue exitosa
        """
        url = f"{self.base_url}/ingreso-documento/{id_documento}"
        payload = {
            "Ruta": ruta
        }

        try:
            import json
            print(f"[FinalizarCasosService] PUT {url}")
            print(f"[FinalizarCasosService] Payload: {json.dumps(payload, indent=2)}")
            response = requests.put(url, json=payload, timeout=30)
            print(f"[FinalizarCasosService] Status actualizar_ruta_documento: {response.status_code}")

            response.raise_for_status()
            print(f"[FinalizarCasosService] Ruta actualizada OK id={id_documento} ruta={ruta}")
            return True

        except requests.RequestException as e:
            print(f"[FinalizarCasosService] Error actualizando ruta documento: {e}")
            return False

    # ------------------------------------------------------------------
    # Consultas adicionales
    # ------------------------------------------------------------------

    def buscar_pdf_remision(self, id_recepcion: int) -> Optional[Dict[str, Any]]:
        """
        Busca PDFs de remisión para una recepción.
        GET /buscar-pdf-remision?idRecepcion=X

        Returns:
            Dict con la respuesta completa o None si hubo error.
            Estructura esperada: {data: {idRecepcion, pdfs: [...], total}, statusCode, message}
        """
        url = f"{self.base_url}/buscar-pdf-remision"
        params = {'idRecepcion': id_recepcion}

        try:
            print(f"[FinalizarCasosService] GET {url}?idRecepcion={id_recepcion}")
            response = requests.get(url, params=params, timeout=30)
            print(f"[FinalizarCasosService] Status buscar_pdf_remision: {response.status_code}")

            data = response.json()
            return data

        except requests.RequestException as e:
            print(f"[FinalizarCasosService] Error buscando PDF remisión: {e}")
            return None

    def consulta_encabezado(self, id_recepcion: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos completos del encabezado de recepción.
        GET /consulta-encabezado?id_recepcion=X

        Returns:
            Dict con la respuesta completa o None si hubo error.
            Estructura esperada: {data: {nombreUsuario, listDetalle: [...], ...}, statusCode, message}
        """
        url = f"{self.base_url}/consulta-encabezado"
        params = {'id_recepcion': id_recepcion}

        try:
            print(f"[FinalizarCasosService] GET {url}?id_recepcion={id_recepcion}")
            response = requests.get(url, params=params, timeout=30)
            print(f"[FinalizarCasosService] Status consulta_encabezado: {response.status_code}")

            response.raise_for_status()
            data = response.json()
            return data

        except requests.RequestException as e:
            print(f"[FinalizarCasosService] Error consultando encabezado: {e}")
            return None
