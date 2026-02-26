"""
Clase de configuración singleton para gestionar las variables de entorno.
Permite acceder a la configuración desde cualquier parte del proyecto.
"""
import os
from pathlib import Path
from typing import Optional
from utils.paths import get_resource_path, get_data_path, get_runtime_path


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
        env_file = get_resource_path('endpoint.env')
        
        if not env_file.exists():
            raise FileNotFoundError(f"No se encontró el archivo de configuración: {env_file}")
        
        # Diccionario temporal para almacenar variables
        temp_vars = {}
        
        # Primera pasada: leer todas las variables
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        temp_vars[key.strip()] = value.strip()
        
        # Segunda pasada: resolver interpolación de variables
        for key, value in temp_vars.items():
            # Reemplazar variables ${VAR} en el valor
            resolved_value = value
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for var_name in matches:
                if var_name in temp_vars:
                    resolved_value = resolved_value.replace(f'${{{var_name}}}', temp_vars[var_name])
            
            # Establecer la variable de entorno con el valor resuelto
            os.environ[key] = resolved_value
    
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
    # CONFIGURACIÓN DEL SERVIDOR
    # ===================================
    @property
    def server_ip(self) -> str:
        """IP del servidor"""
        return self.get('SERVER_IP', 'localhost')
    
    @property
    def server_port(self) -> str:
        """Puerto del servidor"""
        return self.get('SERVER_PORT', '5000')
    
    def build_server_url(self, endpoint: str = "") -> str:
        """
        Construye una URL usando la IP y puerto del servidor configurados.
        
        Args:
            endpoint: Endpoint a agregar (opcional)
        
        Returns:
            URL completa del servidor
        """
        base_url = f"http://{self.server_ip}:{self.server_port}"
        if endpoint:
            endpoint = endpoint.lstrip('/')
            return f"{base_url}/{endpoint}"
        return base_url
    
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
    # LICENCIA / IPS PERMITIDAS
    # ===================================
    @property
    def ips_nombres_permitidos(self) -> list:
        """Lista de IPS permitidas para uso de la app"""
        return [
            "OROSALUD CAUCASIA IPS S.A.S",
            "SERVICIOS EMERGENCY IPS S.A.S"
        ]

    @property
    def recarga_public_key_path(self) -> str:
        """Ruta de la llave publica para recargas (recurso empaquetado)"""
        relative = self.get('RECARGA_PUBLIC_KEY_PATH', 'resources/keys/recarga_public.pem')
        return str(get_resource_path(relative))
    
    # ===================================
    # RUTAS DE ARCHIVOS
    # ===================================
    @property
    def anexo3_logo_path(self) -> str:
        """Ruta del logo del encabezado del Anexo 3"""
        path = self.get('ANEXO3_LOGO_PATH', '')
        if path:
            # Si es ruta absoluta, verificar si existe; si no, buscar en resources
            p = Path(path)
            if p.exists():
                return str(p)
            # Intentar como recurso empaquetado
            return str(get_resource_path('resources/images/Anexo3.png'))
        return ''
    
    @property
    def laboratorio_pdf_path(self) -> str:
        """Ruta donde están los PDFs de órdenes médicas para laboratorio"""
        return self.get('LABORATORIO_PDF_PATH', 'C:\\boot\\temp\\laboratorio')

    # ===================================
    # FINALIZAR CASOS LABORATORIO
    # ===================================
    @property
    def fc_profesional(self) -> str:
        """Nombre del profesional para asignar cita (Finalizar Casos)"""
        return self.get('FC_PROFESIONAL', '')

    @property
    def fc_direccion(self) -> str:
        """Dirección de la IPS para asignar cita (Finalizar Casos)"""
        return self.get('FC_DIRECCION', '')

    @property
    def fc_observacion(self) -> str:
        """Texto de observación para Finalizar Casos"""
        return self.get('FC_OBSERVACION', 'EXAMENES DE LABORATORIOS CLINICOS')

    @property
    def fc_logo_path(self) -> str:
        """Ruta al logo de la IPS para PDF de resultados (Finalizar Casos)"""
        return self.get('FC_LOGO_PATH', '')

    @property
    def fc_firmas_path(self) -> str:
        """Carpeta base de firmas. Se concatena con url_FirmaValida del API."""
        return self.get('FC_FIRMAS_PATH', '')

    @property
    def fc_pdf_output_dir(self) -> str:
        """Carpeta de salida de PDFs generados (Finalizar Casos)"""
        return self.get('FC_PDF_OUTPUT_DIR', '')

    # ===================================
    # EVIDENCIAS - RUTAS LOCALES
    # ===================================
    @property
    def ruta_evidencia(self) -> str:
        """Carpeta local para capturas de pantalla (screenshots PNG)"""
        return self.get('RUTA_EVIDENCIA', '')

    @property
    def ruta_genera_evidencia(self) -> str:
        """Carpeta local donde se generan los PDFs de evidencia"""
        return self.get('RUTA_GENERA_EVIDENCIA', '')

    # ===================================
    # SERVIDOR SMB
    # ===================================
    @property
    def smb_server(self) -> str:
        """IP del servidor SMB"""
        return self.get('SMB_SERVER', '')

    @property
    def smb_share(self) -> str:
        """Nombre del share SMB"""
        return self.get('SMB_SHARE', '')

    @property
    def smb_username(self) -> str:
        """Usuario para autenticación SMB"""
        return self.get('SMB_USERNAME', '')

    @property
    def smb_password(self) -> str:
        """Contraseña para autenticación SMB"""
        return self.get('SMB_PASSWORD', '')

    @property
    def smb_evidencia_path(self) -> str:
        """Ruta relativa en el share SMB para evidencias"""
        return self.get('SMB_EVIDENCIA_PATH', '')

    @property
    def smb_resultados_path(self) -> str:
        """Ruta relativa en el share SMB para resultados externos"""
        return self.get('SMB_RESULTADOS_PATH', '')

    @property
    def smb_fallback_local_path(self) -> str:
        """Ruta local de fallback cuando el servidor SMB no está disponible"""
        return self.get('SMB_FALLBACK_LOCAL_PATH', '')


# Crear una instancia global para facilitar el acceso
config = Config()
