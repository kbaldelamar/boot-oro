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
            "valor_caso": None,
            "numero_casos_exitosos": None,
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
            result["valor_caso"] = item.get("ValorCaso")
            result["numero_casos_exitosos"] = item.get("NumeroCasosExitosos")
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
    
    def actualizar_saldo(self, nuevo_saldo: float) -> Dict:
        """
        Actualiza el saldo del robot en la API
        
        Args:
            nuevo_saldo: Nuevo valor del saldo
            
        Returns:
            Dict con success, message, error
        """
        result = {
            "success": False,
            "message": "",
            "error": None
        }
        
        try:
            url = f"{self.base_url}/ips-saldos"
            data = {"saldoRobot": nuevo_saldo}
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code not in (200, 201):
                result["message"] = f"HTTP {response.status_code}"
                return result
            
            result["success"] = True
            result["message"] = "Saldo actualizado correctamente"
            return result
            
        except Exception as exc:
            result["error"] = str(exc)
            result["message"] = "Error actualizando saldo"
            return result
    
    def descontar_caso_exitoso(self) -> Dict:
        """
        Consulta el saldo actual, descuenta el valor de un caso y actualiza
        
        Returns:
            Dict con success, saldo_anterior, saldo_nuevo, valor_descontado, message, error
        """
        result = {
            "success": False,
            "saldo_anterior": None,
            "saldo_nuevo": None,
            "valor_descontado": None,
            "saldo_agotado": False,
            "message": "",
            "error": None
        }
        
        try:
            # Obtener saldo actual
            info_saldo = self.obtener_saldo()
            
            if not info_saldo.get("success"):
                result["message"] = "No se pudo consultar saldo actual"
                result["error"] = info_saldo.get("error")
                return result
            
            saldo_actual = info_saldo.get("saldo_robot")
            valor_caso = info_saldo.get("valor_caso")
            
            if saldo_actual is None or valor_caso is None:
                result["message"] = "Datos de saldo o valor de caso no disponibles"
                return result
            
            # Convertir a float
            try:
                saldo_float = float(saldo_actual)
                valor_float = float(valor_caso)
            except (TypeError, ValueError) as e:
                result["message"] = f"Error convirtiendo valores: {e}"
                return result
            
            # Calcular nuevo saldo
            nuevo_saldo = saldo_float - valor_float
            
            # No permitir saldo negativo
            if nuevo_saldo < 0:
                nuevo_saldo = 0
            
            # Actualizar saldo
            resultado_actualizacion = self.actualizar_saldo(nuevo_saldo)
            
            if not resultado_actualizacion.get("success"):
                result["message"] = "Error actualizando saldo en API"
                result["error"] = resultado_actualizacion.get("error")
                return result
            
            # Éxito
            result["success"] = True
            result["saldo_anterior"] = saldo_float
            result["saldo_nuevo"] = nuevo_saldo
            result["valor_descontado"] = valor_float
            result["saldo_agotado"] = (nuevo_saldo <= 0)
            result["message"] = f"Saldo descontado: {valor_float}"
            
            return result
            
        except Exception as exc:
            result["error"] = str(exc)
            result["message"] = f"Error en descuento de caso: {str(exc)}"
            return result

