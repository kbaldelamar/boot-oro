"""
Punto de entrada principal de la aplicación.
Sistema de Automatización - Boot ORO
"""
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio src al path
if getattr(sys, 'frozen', False):
    # Modo empaquetado: src ya está dentro del .exe
    src_path = Path(sys._MEIPASS) / 'src'
else:
    # Modo desarrollo
    src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from utils.paths import get_data_path, get_resource_path, get_runtime_path, get_base_path, is_frozen
from ui import MainWindow
from config import Config


def _log_startup_diagnostics(config: Config):
    """
    Escribe diagnóstico de arranque en logs/startup.log.
    Información clave para depurar el .exe en producción.
    """
    log_dir = get_data_path('logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"app_{datetime.now().strftime('%Y-%m-%d')}.log"

    lines = []
    lines.append("=" * 70)
    lines.append(f"  BOOT ORO - INICIO DE APLICACIÓN")
    lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append(f"  Modo:            {'FROZEN (.exe)' if is_frozen() else 'DESARROLLO'}")
    lines.append(f"  Python:          {sys.version}")
    lines.append(f"  Ejecutable:      {sys.executable}")
    lines.append(f"  Base path:       {get_base_path()}")
    lines.append(f"  Runtime path:    {get_runtime_path()}")
    lines.append(f"  Log dir:         {log_dir}")

    # Rutas de recursos empaquetados
    env_path = get_resource_path('endpoint.env')
    pem_path = get_resource_path('resources/keys/recarga_public.pem')
    logo_path = get_resource_path('resources/images/Anexo3.png')
    lines.append("")
    lines.append("  --- RECURSOS EMPAQUETADOS ---")
    lines.append(f"  endpoint.env:    {env_path}  (existe: {env_path.exists()})")
    lines.append(f"  recarga .pem:    {pem_path}  (existe: {pem_path.exists()})")
    lines.append(f"  logo Anexo3:     {logo_path}  (existe: {logo_path.exists()})")

    # URLs del endpoint.env
    lines.append("")
    lines.append("  --- URLS CONFIGURADAS ---")
    lines.append(f"  API Ordenes HC:       {config.api_url_ordenes_hc}")
    lines.append(f"  API Programación:     {config.api_url_programacion}")
    lines.append(f"  API Programación Base: {config.api_url_programacion_base}")
    lines.append(f"  URL Saldo:            {config.get('API_URL_PROGRAMACION_BASE', 'http://localhost:5000').rstrip('/')}/ips-saldos")

    # Información de la IPS
    lines.append("")
    lines.append("  --- IPS ---")
    lines.append(f"  Nombre:          {config.nombre_ips}")
    lines.append(f"  NIT:             {config.nit_ips}")
    lines.append(f"  Sede:            {config.sede_ips_nombre}")

    # Rutas de datos de runtime
    lines.append("")
    lines.append("  --- RUTAS DE RUNTIME (escritura) ---")
    lines.append(f"  Logs:            {get_data_path('logs')}")
    lines.append(f"  Session data:    {get_data_path('session_data')}")
    lines.append(f"  Screenshots:     {get_data_path('screenshots')}")
    lines.append(f"  PDFs output:     {config.get('PDF_OUTPUT_DIR', str(get_data_path('temp/anexos3')))}")
    lines.append(f"  Recargas usadas: {get_data_path('session_data/recargas_usadas.json')}")

    # Config recarga_public_key_path resuelto
    lines.append("")
    lines.append("  --- LLAVE PÚBLICA RECARGA ---")
    lines.append(f"  Config path:     {config.recarga_public_key_path}")
    lines.append(f"  Existe:          {Path(config.recarga_public_key_path).exists()}")

    lines.append("=" * 70)

    text = "\n".join(lines) + "\n"

    # Escribir al log
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(text)
        print(text)
    except Exception as e:
        print(f"Error escribiendo diagnóstico: {e}")
        print(text)


def main():
    """
    Función principal de la aplicación.
    """
    try:
        # Crear carpeta logs de inmediato
        get_data_path('logs').mkdir(parents=True, exist_ok=True)

        # Inicializar configuración
        config = Config()

        # Diagnóstico de arranque (se escribe a logs/app_*.log)
        _log_startup_diagnostics(config)
        
        # Crear y ejecutar la ventana principal
        app = MainWindow()
        app.run()
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Asegúrese de que el archivo endpoint.env existe en el directorio del proyecto.")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        # Intentar escribir error al log
        try:
            log_dir = get_data_path('logs')
            log_dir.mkdir(parents=True, exist_ok=True)
            err_file = log_dir / f"crash_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"
            with open(err_file, 'w', encoding='utf-8') as f:
                f.write(f"CRASH: {datetime.now()}\n")
                f.write(f"Error: {e}\n")
                import traceback as tb
                tb.print_exc(file=f)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
