"""
Cliente HTTP base para estandarizar el consumo de APIs en todo el proyecto.
"""
import requests
from typing import Dict, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime


class HTTPMethod(Enum):
    """Métodos HTTP soportados"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIResponse:
    """
    Clase para estandarizar las respuestas de la API.
    """
    success: bool
    status_code: int
    data: Optional[Any] = None
    message: str = ""
    error: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        """Inicializa el timestamp si no se proporciona"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convierte la respuesta a diccionario"""
        return {
            'success': self.success,
            'status_code': self.status_code,
            'data': self.data,
            'message': self.message,
            'error': self.error,
            'timestamp': self.timestamp
        }


class APIError(Exception):
    """
    Excepción personalizada para errores de API.
    """
    def __init__(self, message: str, status_code: int = None, response: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class APIClient:
    """
    Cliente HTTP base para realizar peticiones a APIs de forma estandarizada.
    
    Características:
    - Manejo centralizado de headers
    - Timeouts configurables
    - Logging de peticiones
    - Manejo estandarizado de errores
    - Retry automático (opcional)
    """
    
    def __init__(
        self,
        base_url: str = "",
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True
    ):
        """
        Inicializa el cliente API.
        
        Args:
            base_url: URL base de la API
            timeout: Timeout en segundos para las peticiones
            headers: Headers por defecto para todas las peticiones
            verify_ssl: Si se debe verificar el certificado SSL
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        # Headers por defecto
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'BootORO/1.0'
        }
        
        if headers:
            self.default_headers.update(headers)
        
        self.session.headers.update(self.default_headers)
    
    def _build_url(self, endpoint: str) -> str:
        """
        Construye la URL completa.
        
        Args:
            endpoint: Endpoint de la API
            
        Returns:
            URL completa
        """
        endpoint = endpoint.lstrip('/')
        if self.base_url:
            return f"{self.base_url}/{endpoint}"
        return endpoint
    
    def _make_request(
        self,
        method: HTTPMethod,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> APIResponse:
        """
        Realiza una petición HTTP de forma estandarizada.
        
        Args:
            method: Método HTTP a utilizar
            endpoint: Endpoint de la API
            params: Parámetros query string
            data: Datos para enviar como form-data
            json_data: Datos para enviar como JSON
            headers: Headers adicionales para esta petición
            timeout: Timeout específico para esta petición
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            APIResponse con el resultado de la petición
        """
        url = self._build_url(endpoint)
        timeout = timeout or self.timeout
        
        # Mergear headers si se proporcionan
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            # Log de la petición
            self._log_request(method, url, params, json_data)
            
            # Realizar la petición
            response = self.session.request(
                method=method.value,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers,
                timeout=timeout,
                verify=self.verify_ssl,
                **kwargs
            )
            
            # Log de la respuesta
            self._log_response(response)
            
            # Parsear la respuesta
            return self._parse_response(response)
            
        except requests.exceptions.Timeout:
            return APIResponse(
                success=False,
                status_code=408,
                error="Timeout: La petición tardó demasiado tiempo",
                message="Timeout de la petición"
            )
        except requests.exceptions.ConnectionError:
            return APIResponse(
                success=False,
                status_code=503,
                error="Error de conexión: No se pudo conectar con el servidor",
                message="Error de conexión"
            )
        except requests.exceptions.RequestException as e:
            return APIResponse(
                success=False,
                status_code=500,
                error=f"Error en la petición: {str(e)}",
                message="Error en la petición HTTP"
            )
        except Exception as e:
            return APIResponse(
                success=False,
                status_code=500,
                error=f"Error inesperado: {str(e)}",
                message="Error inesperado"
            )
    
    def _parse_response(self, response: requests.Response) -> APIResponse:
        """
        Parsea la respuesta HTTP y la convierte en APIResponse.
        
        Args:
            response: Respuesta de requests
            
        Returns:
            APIResponse estandarizada
        """
        success = 200 <= response.status_code < 300
        
        # Intentar parsear JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = response.text if response.text else None
        
        # Construir mensaje y error basado en el código de estado
        if success:
            message = "Petición exitosa"
            error_msg = None
        elif response.status_code == 500:
            message = "Error 500 - Error Interno del Servidor"
            error_msg = "El servidor encontró un error interno al procesar la solicitud. Por favor, intente nuevamente más tarde o contacte al administrador del sistema."
        elif response.status_code == 404:
            message = "Error 404 - No Encontrado"
            error_msg = "El recurso solicitado no fue encontrado."
        elif response.status_code == 401:
            message = "Error 401 - No Autorizado"
            error_msg = "No tiene autorización para acceder a este recurso."
        elif response.status_code == 403:
            message = "Error 403 - Prohibido"
            error_msg = "No tiene permisos para acceder a este recurso."
        else:
            message = f"Error {response.status_code}"
            error_msg = f"Error en la petición: código {response.status_code}"
        
        return APIResponse(
            success=success,
            status_code=response.status_code,
            data=data,
            message=message,
            error=error_msg
        )
    
    def _log_request(
        self,
        method: HTTPMethod,
        url: str,
        params: Optional[Dict],
        json_data: Optional[Dict]
    ):
        """
        Registra información de la petición (para debugging).
        
        Args:
            method: Método HTTP
            url: URL completa
            params: Parámetros de la petición
            json_data: Datos JSON de la petición
        """
        # Por ahora solo print, se puede implementar logging más sofisticado
        print(f"[API] {method.value} {url}")
        if params:
            print(f"[API] Params: {params}")
        if json_data:
            print(f"[API] JSON: {json_data}")
    
    def _log_response(self, response: requests.Response):
        """
        Registra información de la respuesta (para debugging).
        
        Args:
            response: Respuesta HTTP
        """
        print(f"[API] Response: {response.status_code}")
    
    # Métodos de conveniencia para cada tipo de petición HTTP
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> APIResponse:
        """
        Realiza una petición GET.
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros query string
            **kwargs: Argumentos adicionales
            
        Returns:
            APIResponse
        """
        return self._make_request(HTTPMethod.GET, endpoint, params=params, **kwargs)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> APIResponse:
        """
        Realiza una petición POST.
        
        Args:
            endpoint: Endpoint de la API
            data: Datos form-data
            json_data: Datos JSON
            **kwargs: Argumentos adicionales
            
        Returns:
            APIResponse
        """
        return self._make_request(
            HTTPMethod.POST,
            endpoint,
            data=data,
            json_data=json_data,
            **kwargs
        )
    
    def put(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> APIResponse:
        """
        Realiza una petición PUT.
        
        Args:
            endpoint: Endpoint de la API
            data: Datos form-data
            json_data: Datos JSON
            **kwargs: Argumentos adicionales
            
        Returns:
            APIResponse
        """
        return self._make_request(
            HTTPMethod.PUT,
            endpoint,
            data=data,
            json_data=json_data,
            **kwargs
        )
    
    def delete(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> APIResponse:
        """
        Realiza una petición DELETE.
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros query string
            **kwargs: Argumentos adicionales
            
        Returns:
            APIResponse
        """
        return self._make_request(HTTPMethod.DELETE, endpoint, params=params, **kwargs)
    
    def patch(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> APIResponse:
        """
        Realiza una petición PATCH.
        
        Args:
            endpoint: Endpoint de la API
            data: Datos form-data
            json_data: Datos JSON
            **kwargs: Argumentos adicionales
            
        Returns:
            APIResponse
        """
        return self._make_request(
            HTTPMethod.PATCH,
            endpoint,
            data=data,
            json_data=json_data,
            **kwargs
        )
    
    def set_auth_token(self, token: str, token_type: str = "Bearer"):
        """
        Establece el token de autenticación en los headers.
        
        Args:
            token: Token de autenticación
            token_type: Tipo de token (Bearer, Token, etc.)
        """
        self.session.headers['Authorization'] = f"{token_type} {token}"
    
    def remove_auth_token(self):
        """Elimina el token de autenticación de los headers"""
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def close(self):
        """Cierra la sesión HTTP"""
        self.session.close()
