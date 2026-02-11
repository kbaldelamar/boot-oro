"""
Utilidades para resolución de rutas.
Soporta ejecución normal (desarrollo) y empaquetado con PyInstaller (.exe).

- Recursos empaquetados (solo lectura): endpoint.env, .pem, imágenes
  → Se resuelven con get_resource_path() usando sys._MEIPASS en modo frozen.

- Datos de runtime (lectura/escritura): logs, session_data, screenshots, temp
  → Se resuelven con get_runtime_path() junto al .exe o al project_root en dev.
"""
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Retorna True si la app está corriendo como .exe empaquetado."""
    return getattr(sys, 'frozen', False)


def get_base_path() -> Path:
    """
    Retorna la ruta base donde PyInstaller extrae los archivos empaquetados.
    En desarrollo, retorna la raíz del proyecto.
    """
    if is_frozen():
        # PyInstaller extrae aquí los archivos --add-data
        return Path(sys._MEIPASS)
    # Desarrollo: src/utils/paths.py → ../../ = project_root
    return Path(__file__).parent.parent.parent


def get_runtime_path() -> Path:
    """
    Retorna la ruta donde se almacenan datos de runtime (escritura).
    - Frozen: directorio donde está el .exe
    - Desarrollo: raíz del proyecto
    """
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def get_resource_path(relative_path: str) -> Path:
    """
    Resuelve la ruta de un recurso empaquetado (solo lectura).
    
    Args:
        relative_path: Ruta relativa al proyecto, ej: 'endpoint.env',
                       'resources/keys/recarga_public.pem'
    
    Returns:
        Path absoluto al recurso.
    """
    return get_base_path() / relative_path


def get_data_path(relative_path: str) -> Path:
    """
    Resuelve la ruta de un archivo/directorio de datos de runtime (lectura/escritura).
    
    Args:
        relative_path: Ruta relativa, ej: 'logs', 'session_data', 'temp/anexos3'
    
    Returns:
        Path absoluto para datos de runtime.
    """
    return get_runtime_path() / relative_path
