"""
Test de conexión SMB - Finalizar Casos.
Verifica:
  1. Conexión al servidor SMB
  2. Listar archivos en la carpeta
  3. Verificar que un archivo específico existe
  4. Copiar el archivo a local

Uso:
    python test_smb_fc.py
"""
import sys
import os
from pathlib import Path

# Asegurar que src/ esté en el path
src_path = str(Path(__file__).parent / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from config.config import Config


def main():
    print("=" * 60)
    print("  TEST: Conexión SMB - Finalizar Casos")
    print("=" * 60)

    config = Config()

    server = config.smb_server
    share = config.smb_share
    username = config.smb_username
    password = config.smb_password
    evidencia_path = config.smb_evidencia_path

    print(f"\n📋 Configuración SMB:")
    print(f"   Servidor:  {server}")
    print(f"   Share:     {share}")
    print(f"   Usuario:   {username}")
    print(f"   Password:  {'*' * len(password)}")
    print(f"   Carpeta:   {evidencia_path}")

    # Archivo a buscar
    archivo_buscar = "1000_2669_HISTORIA CLINICA.pdf"
    ruta_local_destino = os.path.join(
        config.ruta_genera_evidencia or "C:\\Casosboot\\evidencias\\generadas",
        archivo_buscar
    )

    # ============================================================
    # 1. Conectar al servidor SMB
    # ============================================================
    print(f"\n{'=' * 60}")
    print("  PASO 1: Conectar al servidor SMB")
    print(f"{'=' * 60}")

    try:
        import smbclient

        smbclient.register_session(
            server,
            username=username,
            password=password,
        )
        print(f"   ✅ Conexión exitosa a {server}")
    except ImportError:
        print("   ❌ smbprotocol no instalado. Ejecutar: pip install smbprotocol")
        return
    except Exception as e:
        print(f"   ❌ Error conectando: {e}")
        import traceback
        traceback.print_exc()
        return

    # ============================================================
    # 2. Listar archivos en la carpeta
    # ============================================================
    print(f"\n{'=' * 60}")
    print("  PASO 2: Listar archivos en la carpeta")
    print(f"{'=' * 60}")

    remote_dir = f"\\\\{server}\\{share}\\{evidencia_path}"
    print(f"   Carpeta remota: {remote_dir}")

    try:
        archivos = smbclient.listdir(remote_dir)
        print(f"   ✅ {len(archivos)} archivos encontrados")
        # Mostrar primeros 10
        for i, f in enumerate(archivos[:10]):
            print(f"      [{i+1}] {f}")
        if len(archivos) > 10:
            print(f"      ... y {len(archivos) - 10} más")
    except Exception as e:
        print(f"   ❌ Error listando archivos: {e}")
        import traceback
        traceback.print_exc()
        return

    # ============================================================
    # 3. Verificar que el archivo existe
    # ============================================================
    print(f"\n{'=' * 60}")
    print(f"  PASO 3: Buscar '{archivo_buscar}'")
    print(f"{'=' * 60}")

    remote_file = f"{remote_dir}\\{archivo_buscar}"
    print(f"   Ruta completa: {remote_file}")

    try:
        stat = smbclient.stat(remote_file)
        size = stat.st_size
        print(f"   ✅ Archivo encontrado! Tamaño: {size:,} bytes")
    except FileNotFoundError:
        print(f"   ❌ Archivo NO encontrado: {archivo_buscar}")
        print(f"\n   Archivos disponibles que contienen 'HISTORIA':")
        for f in archivos:
            if 'HISTORIA' in f.upper() or '1000' in f or '2669' in f:
                print(f"      - {f}")
        return
    except Exception as e:
        print(f"   ❌ Error verificando archivo: {e}")
        import traceback
        traceback.print_exc()
        return

    # ============================================================
    # 4. Copiar archivo a local
    # ============================================================
    print(f"\n{'=' * 60}")
    print("  PASO 4: Copiar archivo a local")
    print(f"{'=' * 60}")

    print(f"   Destino local: {ruta_local_destino}")

    # Crear carpeta destino si no existe
    os.makedirs(os.path.dirname(ruta_local_destino), exist_ok=True)

    try:
        from smbclient import shutil as smb_shutil

        smb_shutil.copy2(remote_file, ruta_local_destino)

        if os.path.exists(ruta_local_destino):
            local_size = os.path.getsize(ruta_local_destino)
            print(f"   ✅ Archivo copiado exitosamente!")
            print(f"      Tamaño local: {local_size:,} bytes")
            print(f"      Tamaño remoto: {size:,} bytes")
            if local_size == size:
                print(f"      ✅ Tamaños coinciden - copia íntegra")
            else:
                print(f"      ⚠️ Tamaños no coinciden!")
        else:
            print(f"   ❌ Archivo no se copió correctamente")

    except Exception as e:
        print(f"   ❌ Error copiando archivo: {e}")
        import traceback
        traceback.print_exc()
        return

    # ============================================================
    # Resumen
    # ============================================================
    print(f"\n{'=' * 60}")
    print("  ✅ TEST COMPLETADO EXITOSAMENTE")
    print(f"{'=' * 60}")
    print(f"   - Conexión SMB: OK")
    print(f"   - Listar archivos: OK ({len(archivos)} archivos)")
    print(f"   - Archivo encontrado: {archivo_buscar}")
    print(f"   - Copiado a: {ruta_local_destino}")


if __name__ == '__main__':
    main()
