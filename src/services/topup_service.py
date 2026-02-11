"""
Servicio para validar y aplicar recargas de saldo.
"""
import base64
import json
from pathlib import Path
from typing import Dict, List, Optional

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from utils.paths import get_resource_path, get_data_path
from utils.logger import AdvancedLogger


class TopupService:
    """Servicio para validar archivos de recarga y aplicar saldo"""

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        public_key_path: Optional[str] = None,
        used_store_path: Optional[str] = None
    ):
        self.logger = AdvancedLogger()
        self.base_url = base_url.rstrip("/")
        # Llave pública: recurso empaquetado (solo lectura)
        if public_key_path:
            self.public_key_path = Path(public_key_path)
        else:
            self.public_key_path = get_resource_path("resources/keys/recarga_public.pem")
        # Recargas usadas: datos de runtime (lectura/escritura)
        self.used_store_path = Path(used_store_path) if used_store_path else get_data_path("session_data/recargas_usadas.json")

    def _load_public_key(self):
        if not self.public_key_path.exists():
            raise FileNotFoundError(
                f"No se encontro la llave publica: {self.public_key_path}"
            )
        pem = self.public_key_path.read_bytes()
        return load_pem_public_key(pem)

    @staticmethod
    def _canonical_payload(data: Dict) -> str:
        payload = {k: v for k, v in data.items() if k != "signature"}
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def _verificar_firma(self, data: Dict) -> bool:
        signature_b64 = data.get("signature")
        if not signature_b64:
            return False
        try:
            signature = base64.urlsafe_b64decode(signature_b64.encode("utf-8"))
            payload = self._canonical_payload(data).encode("utf-8")
            public_key = self._load_public_key()
            public_key.verify(signature, payload)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    def _cargar_usadas(self) -> List[str]:
        if not self.used_store_path.exists():
            return []
        try:
            data = json.loads(self.used_store_path.read_text(encoding="utf-8"))
            return data.get("usadas", [])
        except Exception:
            return []

    def _guardar_usada(self, tx_id: str) -> None:
        usadas = self._cargar_usadas()
        if tx_id in usadas:
            return
        usadas.append(tx_id)
        self.used_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.used_store_path.write_text(
            json.dumps({"usadas": usadas}, ensure_ascii=True, indent=2),
            encoding="utf-8"
        )

    @staticmethod
    def _cliente_autorizado(cliente: Optional[str], permitidos: List[str]) -> bool:
        if not cliente:
            return False
        cliente_norm = cliente.strip().upper()
        permitidos_norm = [p.strip().upper() for p in permitidos if p.strip()]
        return cliente_norm in permitidos_norm

    def aplicar_recarga(self, data: Dict) -> bool:
        url = f"{self.base_url}/ips-saldos"
        response = requests.post(url, json=data, timeout=10)
        return response.status_code in (200, 201)

    def recargar_desde_archivo(self, file_path: str, permitidos: List[str]) -> Dict:
        result = {"success": False, "message": "", "error": None}
        self.logger.info('Topup', f'=== INICIO RECARGA ===')
        self.logger.info('Topup', f'Archivo: {file_path}')
        self.logger.info('Topup', f'Base URL: {self.base_url}')
        self.logger.info('Topup', f'Public key: {self.public_key_path} (existe: {self.public_key_path.exists()})')
        self.logger.info('Topup', f'Used store: {self.used_store_path}')

        try:
            raw = Path(file_path).read_text(encoding="utf-8")
            data = json.loads(raw)
            self.logger.info('Topup', f'JSON parseado OK - keys: {list(data.keys())}')
            self.logger.info('Topup', f'cliente: {data.get("cliente")}')
            self.logger.info('Topup', f'txId: {data.get("txId")}')
            self.logger.info('Topup', f'saldoRobot: {data.get("saldoRobot")}')
            self.logger.info('Topup', f'signature presente: {bool(data.get("signature"))}')
        except Exception as exc:
            self.logger.error('Topup', f'Error leyendo/parseando archivo: {exc}', exc)
            result["message"] = "Archivo invalido"
            result["error"] = str(exc)
            return result

        try:
            self.logger.info('Topup', 'Verificando firma...')
            canonical = self._canonical_payload(data)
            self.logger.info('Topup', f'Payload canonico: {canonical[:150]}...')
            firma_ok = self._verificar_firma(data)
            self.logger.info('Topup', f'Firma valida: {firma_ok}')
            if not firma_ok:
                result["message"] = "Firma invalida"
                return result
        except FileNotFoundError as exc:
            self.logger.error('Topup', f'Llave publica no encontrada: {exc}', exc)
            result["message"] = str(exc)
            return result
        except Exception as exc:
            self.logger.error('Topup', f'Error verificando firma: {exc}', exc)
            result["message"] = f"Error verificando firma: {exc}"
            result["error"] = str(exc)
            return result

        cliente = data.get("cliente")
        self.logger.info('Topup', f'Verificando cliente: "{cliente}" vs permitidos: {permitidos}')
        if not self._cliente_autorizado(cliente, permitidos):
            self.logger.warning('Topup', f'Cliente NO autorizado: "{cliente}"')
            result["message"] = "Cliente no autorizado"
            return result
        self.logger.info('Topup', 'Cliente autorizado OK')

        tx_id = data.get("txId")
        if not tx_id:
            self.logger.warning('Topup', 'Falta txId en el archivo')
            result["message"] = "Falta txId"
            return result

        usadas = self._cargar_usadas()
        self.logger.info('Topup', f'Recargas usadas: {usadas}')
        if tx_id in usadas:
            self.logger.warning('Topup', f'txId {tx_id} ya fue usado')
            result["message"] = "Recarga ya aplicada"
            return result

        post_data = {
            "saldoRobot": data.get("saldoRobot"),
            "cliente": data.get("cliente"),
            "txId": data.get("txId"),
            "issuedAt": data.get("issuedAt")
        }
        post_url = f"{self.base_url}/ips-saldos"
        self.logger.info('Topup', f'POST {post_url} - body: {post_data}')
        
        try:
            response = requests.post(post_url, json=post_data, timeout=10)
            self.logger.info('Topup', f'Respuesta: HTTP {response.status_code} - {response.text[:200]}')
            if response.status_code not in (200, 201):
                result["message"] = f"No se pudo aplicar la recarga (HTTP {response.status_code})"
                result["error"] = response.text[:200]
                return result
        except Exception as exc:
            self.logger.error('Topup', f'Error en POST: {exc}', exc)
            result["message"] = "No se pudo aplicar la recarga"
            result["error"] = str(exc)
            return result

        self._guardar_usada(tx_id)
        self.logger.success('Topup', f'Recarga aplicada exitosamente - txId: {tx_id}')
        self.logger.info('Topup', '=== FIN RECARGA ===')
        result["success"] = True
        result["message"] = "Recarga aplicada"
        return result
