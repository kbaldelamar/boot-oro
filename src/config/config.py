"""
Clase de configuración singleton para gestionar las variables de entorno.
Permite acceder a la configuración desde cualquier parte del proyecto.
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """
    Clase Singleton para manejar la configuración de la aplicación.
    Carga las variables desde el archivo endpoint.env
    """
    _instance: Optional['Config'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa la configuración cargando el archivo .env"""
        if not Config._initialized:
            self._load_env_file()
            Config._initialized = True
    
    def _load_env_file(self):
        """Carga las variables desde el archivo endpoint.env"""
        # Obtener el directorio raíz del proyecto
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / 'endpoint.env'
        
        if not env_file.exists():
            raise FileNotFoundError(f"No se encontró el archivo de configuración: {env_file}")
        
        # Leer y parsear el archivo .env
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Ignorar comentarios y líneas vacías
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parsear la línea KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
    
    @staticmethod
    def get(key: str, default: str = '') -> str:
        """
        Obtiene el valor de una variable de configuración.
        
        Args:
            key: Nombre de la variable
            default: Valor por defecto si no existe
            
        Returns:
            Valor de la variable o el valor por defecto
        """
        return os.environ.get(key, default)
    
    # ===================================
    # ENDPOINTS DE API
    # ===================================
    @property
    def api_url_ordenes_hc(self) -> str:
        """URL del endpoint para órdenes HC"""
        return self.get('API_URL_ORDENES_HC')
    
    @property
    def api_url_programacion(self) -> str:
        """URL del endpoint para programación de órdenes"""
        return self.get('API_URL_PROGRAMACION')
    
    @property
    def api_url_programacion_base(self) -> str:
        """URL base para programación"""
        return self.get('API_URL_PROGRAMACION_BASE')
    
    # ===================================
    # CREDENCIALES DE LOGIN
    # ===================================
    @property
    def login_email(self) -> str:
        """Email para login"""
        return self.get('LOGIN_EMAIL')
    
    @property
    def login_password(self) -> str:
        """Contraseña para login"""
        return self.get('LOGIN_PASSWORD')
    
    # ===================================
    # TWOCAPTCHA
    # ===================================
    @property
    def twocaptcha_api_key(self) -> str:
        """API Key de TwoCaptcha"""
        return self.get('TWOCAPTCHA_API_KEY')
    
    @property
    def twocaptcha_site_key(self) -> str:
        """Site Key de reCAPTCHA"""
        return self.get('TWOCAPTCHA_SITE_KEY')
    
    # ===================================
    # INFORMACIÓN DE LA IPS
    # ===================================
    @property
    def nombre_ips(self) -> str:
        """Nombre de la IPS"""
        return self.get('NOMBREIPS')
    
    @property
    def nit_ips(self) -> str:
        """NIT de la IPS"""
        return self.get('NITIPS')
    
    @property
    def sede_ips(self) -> str:
        """Código de sede de la IPS"""
        return self.get('SEDEIPS')
    
    @property
    def sede_ips_nombre(self) -> str:
        """Nombre completo de la sede de la IPS"""
        return self.get('SEDEIPSNOMBRE')
    
    # ===================================
    # RUTAS DE ARCHIVOS
    # ===================================
    @property
    def anexo3_logo_path(self) -> str:
        """Ruta del logo del encabezado del Anexo 3"""
        return self.get('ANEXO3_LOGO_PATH', '')


# Crear una instancia global para facilitar el acceso
config = Config()
