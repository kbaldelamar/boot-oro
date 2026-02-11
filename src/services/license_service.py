"""
Servicio para validar licencia y saldo de IPS.
"""
import base64
import re
from typing import Dict, List, Optional

import requests

try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.fernet import Fernet, InvalidToken
except ImportError as exc:
    PBKDF2HMAC = None
    hashes = None
    Fernet = None
    InvalidToken = Exception
    _CRYPTO_IMPORT_ERROR = exc
else:
    _CRYPTO_IMPORT_ERROR = None


class LicenseService:
    """Servicio para validar saldo y nombre de IPS"""

    DEFAULT_KEY = "LICENSE_DB_ENCRYPTION_KEY_2024"
    DEFAULT_SALT = "license_salt_2024_stable"

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        key: str = DEFAULT_KEY,
        salt: str = DEFAULT_SALT
    ):
        if _CRYPTO_IMPORT_ERROR is not None:
            raise ImportError(
                "cryptography no esta instalado. Instale el paquete cryptography."
            )

        self.base_url = base_url.rstrip("/")
        self.key = key
        self.salt = salt

    def _derive_key(self) -> bytes:
        """Deriva la clave para Fernet usando PBKDF2HMAC"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt.encode("utf-8"),
            iterations=100000
        )
        return base64.urlsafe_b64encode(kdf.derive(self.key.encode("utf-8")))

    def decrypt_name(self, token: str) -> Optional[str]:
        """Desencripta el nombre (Nbre)"""
        if not token:
            return None
        try:
            fernet = Fernet(self._derive_key())
            token_clean = str(token).strip()
            if not token_clean:
                return None
            try:
                token_bytes = base64.urlsafe_b64decode(token_clean.encode("utf-8"))
            except Exception:
                token_bytes = token_clean.encode("utf-8")
            decrypted = fernet.decrypt(token_bytes)
            return decrypted.decode("utf-8").strip()
        except (InvalidToken, ValueError, TypeError):
            # Fallback: algunos servicios entregan base64 del texto plano
            try:
                decoded = base64.urlsafe_b64decode(str(token).strip().encode("utf-8"))
                decoded_text = decoded.decode("utf-8").strip()
                return decoded_text or None
            except Exception:
                return None

    def obtener_saldo(self) -> Dict:
        """Consulta el saldo y retorna datos normalizados"""
        result = {
            "success": False,
            "saldo_robot": None,
            "nombre_encriptado": None,
            "nombre_desencriptado": None,
            "message": "",
            "error": None
        }

        try:
            url = f"{self.base_url}/ips-saldos"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                result["message"] = f"HTTP {response.status_code}"
                return result

            payload = response.json()
            data_list = payload.get("data", []) or []
            if not data_list:
                result["message"] = "Respuesta sin datos"
                return result

            item = data_list[0]
            result["saldo_robot"] = item.get("saldoRobot")
            result["nombre_encriptado"] = item.get("Nbre")
            result["nombre_desencriptado"] = self.decrypt_name(item.get("Nbre"))
            result["success"] = True
            result["message"] = payload.get("message", "")
            return result

        except Exception as exc:
            result["error"] = str(exc)
            result["message"] = "Error consultando saldo"
            return result

    @staticmethod
    def nombre_autorizado(nombre: Optional[str], permitidos: List[str]) -> bool:
        """Valida si el nombre esta dentro de la lista permitida"""
        if not nombre:
            return False
        def normalizar(valor: str) -> str:
            limpio = valor.replace('\u00a0', ' ').strip().upper()
            limpio = re.sub(r"\s+", " ", limpio)
            return limpio

        nombre_norm = normalizar(nombre)
        permitidos_norm = [normalizar(p) for p in permitidos if p.strip()]
        return nombre_norm in permitidos_norm
