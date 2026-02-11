"""
Builder para empaquetar Boot ORO como .exe con PyInstaller.

Empaqueta dentro del .exe:
  - endpoint.env       → configuración (no visible al usuario)
  - resources/keys/    → llave pública Ed25519 (protegida)
  - resources/images/  → logos y firmas

Datos de runtime (junto al .exe):
  - logs/              → archivos de log
  - session_data/      → sesión y recargas usadas
  - screenshots/       → capturas de Playwright
  - temp/              → PDFs generados
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class BootOroBuilder:
    """Clase builder para generar el ejecutable de Boot ORO."""

    # Nombre del ejecutable de salida
    APP_NAME = "BootORO"
    # Icono (opcional, cambiar si se tiene un .ico)
    ICON_PATH = None

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent)
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / f"{self.APP_NAME}.spec"

    # ──────────────────────────────────────────
    # Archivos empaquetados dentro del .exe
    # ──────────────────────────────────────────
    @property
    def bundled_data(self) -> list:
        """
        Retorna lista de tuplas (origen, destino_en_exe) para --add-data.
        Estos archivos quedan DENTRO del .exe y se extraen en sys._MEIPASS.
        """
        sep = ";"  # Windows
        items = []

        # endpoint.env → raíz del bundle
        env_file = self.project_root / "endpoint.env"
        if env_file.exists():
            items.append((str(env_file), "."))

        # Llave pública Ed25519 → resources/keys/
        keys_dir = self.project_root / "resources" / "keys"
        if keys_dir.exists():
            items.append((str(keys_dir), "resources/keys"))

        # Imágenes (logos, firmas) → resources/images/
        images_dir = self.project_root / "resources" / "images"
        if images_dir.exists():
            items.append((str(images_dir), "resources/images"))

        # Código fuente src/ → src/
        src_dir = self.project_root / "src"
        if src_dir.exists():
            items.append((str(src_dir), "src"))

        return items

    # ──────────────────────────────────────────
    # Módulos ocultos requeridos
    # ──────────────────────────────────────────
    @property
    def hidden_imports(self) -> list:
        """Módulos que PyInstaller no detecta automáticamente."""
        return [
            "cryptography",
            "cryptography.hazmat.primitives.serialization",
            "cryptography.hazmat.primitives.asymmetric.ed25519",
            "cryptography.hazmat.primitives.kdf.pbkdf2",
            "cryptography.fernet",
            "requests",
            "fitz",
            "tkinter",
            "tkinter.ttk",
            "tkinter.messagebox",
            "tkinter.filedialog",
        ]

    # ──────────────────────────────────────────
    # Exclusiones para reducir tamaño
    # ──────────────────────────────────────────
    @property
    def excludes(self) -> list:
        """Módulos a excluir del empaquetado."""
        return [
            "matplotlib",
            "numpy",
            "scipy",
            "pandas",
            "pytest",
            "black",
            "flake8",
            "colorlog",
            "pydantic",
            "notebook",
            "IPython",
        ]

    # ──────────────────────────────────────────
    # Generar el .spec de PyInstaller
    # ──────────────────────────────────────────
    def _build_spec_content(self) -> str:
        """Genera el contenido del archivo .spec para PyInstaller."""
        # Construir add-data tuples
        datas_lines = []
        for src, dest in self.bundled_data:
            datas_lines.append(f"    (r'{src}', r'{dest}'),")
        datas_str = "\n".join(datas_lines)

        # Hidden imports
        hidden_str = ",\n    ".join(f"'{h}'" for h in self.hidden_imports)

        # Excludes
        excludes_str = ",\n    ".join(f"'{e}'" for e in self.excludes)

        # Icono
        icon_line = f"icon=r'{self.ICON_PATH}'," if self.ICON_PATH else ""

        spec = f"""# -*- mode: python ; coding: utf-8 -*-
# Auto-generado por BootOroBuilder - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

block_cipher = None

a = Analysis(
    [r'{self.project_root / "main.py"}'],
    pathex=[
        r'{self.project_root}',
        r'{self.project_root / "src"}',
    ],
    binaries=[],
    datas=[
{datas_str}
    ],
    hiddenimports=[
    {hidden_str}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
    {excludes_str}
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_line}
)
"""
        return spec

    # ──────────────────────────────────────────
    # Limpiar builds anteriores
    # ──────────────────────────────────────────
    def limpiar(self):
        """Elimina directorios build/ y dist/ previos."""
        for d in [self.build_dir, self.dist_dir]:
            if d.exists():
                print(f"  Limpiando: {d}")
                shutil.rmtree(d)
        if self.spec_file.exists():
            self.spec_file.unlink()
        print("  ✅ Limpieza completada")

    # ──────────────────────────────────────────
    # Validar requisitos
    # ──────────────────────────────────────────
    def validar_requisitos(self) -> bool:
        """Verifica que PyInstaller esté instalado y los archivos necesarios existan."""
        errores = []

        # Verificar PyInstaller
        try:
            import PyInstaller
            print(f"  PyInstaller: {PyInstaller.__version__}")
        except ImportError:
            errores.append("PyInstaller no está instalado. Ejecute: pip install pyinstaller")

        # Verificar archivos críticos
        archivos_requeridos = [
            ("main.py", "Punto de entrada"),
            ("endpoint.env", "Archivo de configuración"),
            ("resources/keys/recarga_public.pem", "Llave pública Ed25519"),
            ("src/config/config.py", "Módulo de configuración"),
        ]
        for rel_path, descripcion in archivos_requeridos:
            full_path = self.project_root / rel_path
            if not full_path.exists():
                errores.append(f"Falta {descripcion}: {rel_path}")
            else:
                print(f"  ✅ {descripcion}: {rel_path}")

        if errores:
            print("\n❌ Errores encontrados:")
            for e in errores:
                print(f"  - {e}")
            return False

        print("  ✅ Todos los requisitos cumplidos")
        return True

    # ──────────────────────────────────────────
    # Crear directorios de runtime
    # ──────────────────────────────────────────
    def crear_directorios_runtime(self):
        """Crea los directorios de datos junto al .exe en dist/."""
        exe_dir = self.dist_dir
        dirs_runtime = ["logs", "session_data", "screenshots", "temp/anexos3"]
        for d in dirs_runtime:
            dr = exe_dir / d
            dr.mkdir(parents=True, exist_ok=True)
            print(f"  📁 {d}/")
        print("  ✅ Directorios de runtime creados en dist/")

    # ──────────────────────────────────────────
    # BUILD principal
    # ──────────────────────────────────────────
    def build(self, limpiar_previo: bool = True):
        """
        Ejecuta el proceso completo de build:
        1. Validar requisitos
        2. Limpiar builds previos
        3. Generar .spec
        4. Ejecutar PyInstaller
        5. Crear directorios de runtime
        """
        print("=" * 60)
        print(f"  🔨 Boot ORO Builder - {self.APP_NAME}.exe")
        print("=" * 60)

        # 1. Validar
        print("\n📋 Paso 1: Validando requisitos...")
        if not self.validar_requisitos():
            print("\n❌ Build cancelado por errores de validación.")
            return False

        # 2. Limpiar
        if limpiar_previo:
            print("\n🧹 Paso 2: Limpiando builds anteriores...")
            self.limpiar()

        # 3. Generar .spec
        print("\n📝 Paso 3: Generando archivo .spec...")
        spec_content = self._build_spec_content()
        self.spec_file.write_text(spec_content, encoding="utf-8")
        print(f"  Archivo: {self.spec_file}")

        # 4. Ejecutar PyInstaller
        print("\n⚙️  Paso 4: Ejecutando PyInstaller...")
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(self.spec_file),
            "--distpath", str(self.dist_dir),
            "--workpath", str(self.build_dir),
            "--noconfirm",
        ]
        print(f"  Comando: {' '.join(cmd)}\n")

        result = subprocess.run(cmd, cwd=str(self.project_root))

        if result.returncode != 0:
            print(f"\n❌ PyInstaller falló con código: {result.returncode}")
            return False

        # 5. Crear directorios de runtime junto al .exe
        print("\n📁 Paso 5: Creando directorios de runtime...")
        self.crear_directorios_runtime()

        # Verificar resultado
        exe_path = self.dist_dir / f"{self.APP_NAME}.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print(f"  ✅ BUILD EXITOSO")
            print(f"  📦 Ejecutable: {exe_path}")
            print(f"  📊 Tamaño: {size_mb:.1f} MB")
            print(f"\n  📌 Para distribuir, copie toda la carpeta dist/")
            print(f"     (incluye el .exe y los directorios de datos)")
            print("=" * 60)
            return True
        else:
            print(f"\n❌ No se encontró el ejecutable: {exe_path}")
            return False


# ──────────────────────────────────────────
# Ejecución directa
# ──────────────────────────────────────────
if __name__ == "__main__":
    builder = BootOroBuilder()
    success = builder.build()
    sys.exit(0 if success else 1)
