"""
Servicio SMB para subir archivos al servidor de archivos compartido.
Módulo Finalizar Casos - Independiente de autorizar_anexo3 y laboratorio.

Usa smbprotocol para conectarse al servidor SMB y copiar archivos.
Configuración desde endpoint.env:
  SMB_SERVER, SMB_SHARE, SMB_USERNAME, SMB_PASSWORD,
  SMB_EVIDENCIA_PATH, SMB_RESULTADOS_PATH
"""
import os
from typing import Optional, Callable, List

from config.config import Config


class SMBServiceFC:
    """
    Cliente SMB para subir archivos de evidencia y resultados
    al servidor de archivos compartido.

    Si el servidor SMB no está disponible, guarda una copia local
    en SMB_FALLBACK_LOCAL_PATH como respaldo.
    """

    def __init__(self, log_function: Optional[Callable[[str], None]] = None):
        config = Config()

        self.server = config.smb_server
        self.share = config.smb_share
        self.username = config.smb_username
        self.password = config.smb_password
        self.evidencia_path = config.smb_evidencia_path
        self.resultados_path = config.smb_resultados_path
        self.remision_search_path = config.smb_remision_search_path
        self.fallback_local_path = config.smb_fallback_local_path

        # Flag para indicar si la última operación usó SMB real o fallback local
        self.ultimo_metodo = None  # 'smb' | 'fallback' | None

        self.log = log_function or print

    # ==================================================================
    # Subir archivo a SMB
    # ==================================================================

    def subir_archivo(
        self,
        local_path: str,
        remote_filename: str,
        remote_folder: Optional[str] = None,
    ) -> bool:
        """
        Sube un archivo local al servidor SMB.

        Args:
            local_path: Ruta completa del archivo local
            remote_filename: Nombre del archivo en el servidor
            remote_folder: Carpeta destino dentro del share (default: SMB_EVIDENCIA_PATH)

        Returns:
            True si se subió correctamente, False si falló
        """
        if not remote_folder:
            remote_folder = self.evidencia_path

        if not os.path.exists(local_path):
            self.log(f"❌ Archivo local no encontrado: {local_path}")
            return False

        if not self.server or not self.share:
            self.log("❌ Configuración SMB incompleta (SMB_SERVER o SMB_SHARE vacíos)")
            return False

        try:
            import smbclient
            from smbclient import shutil as smb_shutil

            # Registrar sesión SMB
            smbclient.register_session(
                self.server,
                username=self.username,
                password=self.password,
            )

            # Construir ruta remota UNC
            # \\servidor\share\carpeta\archivo
            remote_dir = f"\\\\{self.server}\\{self.share}\\{remote_folder}"
            remote_path = f"{remote_dir}\\{remote_filename}"

            self.log(f"📤 Subiendo a SMB: {remote_path}")

            # Crear directorio remoto si no existe
            try:
                smbclient.makedirs(remote_dir, exist_ok=True)
            except Exception:
                pass  # Puede fallar si ya existe

            # Copiar archivo
            smb_shutil.copy2(local_path, remote_path)

            self.log(f"✅ Archivo subido exitosamente a SMB: {remote_path}")
            self.ultimo_metodo = 'smb'
            return True

        except ImportError:
            self.log("❌ smbprotocol no instalado. Ejecutar: pip install smbprotocol")
            resultado = self._guardar_fallback_local(local_path, remote_filename, remote_folder)
            if resultado:
                self.ultimo_metodo = 'fallback'
            return resultado
        except Exception as e:
            self.log(f"⚠️ SMB no disponible: {e}")
            import traceback
            traceback.print_exc()
            resultado = self._guardar_fallback_local(local_path, remote_filename, remote_folder)
            if resultado:
                self.ultimo_metodo = 'fallback'
            return resultado

    # ==================================================================
    # Fallback local cuando SMB no está disponible
    # ==================================================================

    def _guardar_fallback_local(
        self,
        local_path: str,
        remote_filename: str,
        remote_folder: Optional[str] = None,
    ) -> bool:
        """
        Guarda el archivo en una ruta local de fallback cuando el servidor
        SMB no está disponible.

        La estructura replica la carpeta remota:
          SMB_FALLBACK_LOCAL_PATH / remote_folder / remote_filename

        Returns:
            True si se guardó correctamente, False si falló
        """
        if not self.fallback_local_path:
            self.log("❌ SMB_FALLBACK_LOCAL_PATH no configurado en .env — no se puede guardar fallback local")
            return False

        try:
            import shutil

            # Replicar estructura de carpetas del SMB
            if remote_folder:
                # Normalizar separadores para Windows
                safe_folder = remote_folder.replace("/", os.sep).replace("\\\\", os.sep)
                dest_dir = os.path.join(self.fallback_local_path, safe_folder)
            else:
                dest_dir = self.fallback_local_path

            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, remote_filename)

            shutil.copy2(local_path, dest_path)
            self.log(f"📂 Fallback local: archivo guardado en {dest_path}")
            return True

        except Exception as e:
            self.log(f"❌ Error guardando fallback local: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ==================================================================
    # Subir evidencia (convenience method)
    # ==================================================================

    def subir_evidencia(self, local_path: str, remote_filename: str) -> bool:
        """Sube archivo de evidencia a SMB_EVIDENCIA_PATH."""
        return self.subir_archivo(local_path, remote_filename, self.evidencia_path)

    def subir_resultado(self, local_path: str, remote_filename: str) -> bool:
        """Sube archivo de resultado a SMB_RESULTADOS_PATH."""
        return self.subir_archivo(local_path, remote_filename, self.resultados_path)

    # ==================================================================
    # Buscar archivo en SMB
    # ==================================================================

    def buscar_archivo_remision(
        self,
        patron: str,
        remote_folder: Optional[str] = None,
    ) -> Optional[str]:
        """
        Busca un archivo en el servidor SMB cuyo nombre contenga `patron`.

        Args:
            patron: Texto parcial que debe aparecer en el nombre del archivo
            remote_folder: Carpeta remota (default: SMB_REMISION_SEARCH_PATH)

        Returns:
            Nombre del primer archivo que coincida, o None si no se encontró.
        """
        if not remote_folder:
            remote_folder = self.remision_search_path

        if not self.server or not self.share:
            self.log("❌ Configuración SMB incompleta para buscar remisión")
            return None

        try:
            import smbclient

            smbclient.register_session(
                self.server,
                username=self.username,
                password=self.password,
            )

            remote_dir = f"\\\\{self.server}\\{self.share}\\{remote_folder}"
            self.log(f"🔍 Buscando en SMB: {remote_dir} (patrón: {patron})")

            archivos = smbclient.listdir(remote_dir)
            for archivo in archivos:
                if patron in archivo and archivo.lower().endswith('.pdf'):
                    self.log(f"✅ Archivo remisión encontrado en SMB: {archivo}")
                    return archivo

            self.log(f"❌ No se encontró archivo con patrón '{patron}' en {remote_dir}")
            return None

        except ImportError:
            self.log("❌ smbprotocol no instalado para buscar remisión")
            return None
        except Exception as e:
            self.log(f"❌ Error buscando archivo en SMB: {e}")
            return None

    def descargar_archivo_smb(
        self,
        remote_filename: str,
        local_dest_path: str,
        remote_folder: Optional[str] = None,
    ) -> Optional[str]:
        """
        Descarga un archivo del servidor SMB a una ruta local.

        Args:
            remote_filename: Nombre del archivo remoto
            local_dest_path: Carpeta local de destino
            remote_folder: Carpeta remota (default: SMB_REMISION_SEARCH_PATH)

        Returns:
            Ruta local completa del archivo descargado, o None si falló.
        """
        if not remote_folder:
            remote_folder = self.remision_search_path

        try:
            import smbclient
            from smbclient import shutil as smb_shutil

            smbclient.register_session(
                self.server,
                username=self.username,
                password=self.password,
            )

            remote_path = f"\\\\{self.server}\\{self.share}\\{remote_folder}\\{remote_filename}"
            os.makedirs(local_dest_path, exist_ok=True)
            local_path = os.path.join(local_dest_path, remote_filename)

            self.log(f"📥 Descargando de SMB: {remote_path}")
            smb_shutil.copy2(remote_path, local_path)
            self.log(f"✅ Descargado a: {local_path}")
            return local_path

        except Exception as e:
            self.log(f"❌ Error descargando de SMB: {e}")
            return None
