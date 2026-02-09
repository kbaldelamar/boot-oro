"""
Script de instalación automatizada para Playwright Automation
Ejecuta todos los pasos necesarios para configurar el sistema
"""
import subprocess
import sys
import os
from pathlib import Path


def print_step(step_number, description):
    """Imprime un paso de instalación"""
    print(f"\n{'='*60}")
    print(f"PASO {step_number}: {description}")
    print('='*60)


def run_command(command, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n🔄 {description}...")
    print(f"   Comando: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - EXITOSO")
            if result.stdout:
                print(f"   Salida: {result.stdout[:200]}")
            return True
        else:
            print(f"❌ {description} - FALLÓ")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando comando: {e}")
        return False


def check_python_version():
    """Verifica la versión de Python"""
    print_step(1, "Verificando versión de Python")
    
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 7:
        print("✅ Versión de Python compatible (3.7+)")
        return True
    else:
        print("❌ Se requiere Python 3.7 o superior")
        return False


def install_dependencies():
    """Instala dependencias de requirements.txt"""
    print_step(2, "Instalando dependencias Python")
    
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("❌ No se encontró requirements.txt")
        return False
    
    return run_command(
        f'"{sys.executable}" -m pip install -r requirements.txt',
        "Instalación de dependencias"
    )


def install_playwright_browsers():
    """Instala los navegadores de Playwright"""
    print_step(3, "Instalando navegadores Playwright")
    
    # Instalar Chromium
    if not run_command(
        f'"{sys.executable}" -m playwright install chromium',
        "Instalación de Chromium"
    ):
        return False
    
    return True


def create_directories():
    """Crea directorios necesarios"""
    print_step(4, "Creando directorios del sistema")
    
    directories = [
        "logs",
        "screenshots",
        "session_data"
    ]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Directorio creado/verificado: {dir_name}")
    
    return True


def verify_installation():
    """Verifica que la instalación sea correcta"""
    print_step(5, "Verificando instalación")
    
    print("\n🔍 Ejecutando pruebas...")
    result = subprocess.run(
        f'"{sys.executable}" test_playwright_setup.py',
        shell=True
    )
    
    return result.returncode == 0


def main():
    """Ejecuta el proceso de instalación completo"""
    print("=" * 60)
    print("🚀 INSTALACIÓN AUTOMATIZADA - PLAYWRIGHT AUTOMATION")
    print("=" * 60)
    print("\nEste script instalará todo lo necesario para ejecutar el sistema.")
    print("Por favor espera, puede tardar varios minutos...")
    
    # Paso 1: Verificar Python
    if not check_python_version():
        print("\n❌ INSTALACIÓN ABORTADA: Versión de Python incompatible")
        return False
    
    # Paso 2: Instalar dependencias
    if not install_dependencies():
        print("\n⚠️ ADVERTENCIA: Algunas dependencias no se instalaron correctamente")
        respuesta = input("¿Deseas continuar? (s/n): ")
        if respuesta.lower() != 's':
            return False
    
    # Paso 3: Instalar navegadores Playwright
    if not install_playwright_browsers():
        print("\n❌ INSTALACIÓN ABORTADA: No se pudo instalar Chromium")
        print("\n💡 Intenta manualmente:")
        print("   playwright install chromium")
        return False
    
    # Paso 4: Crear directorios
    create_directories()
    
    # Paso 5: Verificar instalación
    print_step(5, "Verificación final")
    print("\n🧪 Ejecutando pruebas de verificación...")
    
    if verify_installation():
        print("\n" + "=" * 60)
        print("🎉 ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!")
        print("=" * 60)
        print("\n✅ El sistema está listo para usar")
        print("\n📖 Próximos pasos:")
        print("   1. Ejecuta: python main.py")
        print("   2. Ve a la pestaña 'Gestión casos Órdenes HC'")
        print("   3. Programa órdenes y ejecuta el Worker")
        print("\n📚 Documentación: Ver PLAYWRIGHT_README.md")
        return True
    else:
        print("\n" + "=" * 60)
        print("⚠️ INSTALACIÓN COMPLETADA CON ADVERTENCIAS")
        print("=" * 60)
        print("\nAlgunas pruebas fallaron. Revisa los mensajes de error.")
        print("\n💡 Solución de problemas:")
        print("   1. Verifica que todas las dependencias se instalaron")
        print("   2. Ejecuta: python test_playwright_setup.py")
        print("   3. Consulta PLAYWRIGHT_README.md")
        return False


if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print("\n✨ Presiona Enter para cerrar...")
            input()
            sys.exit(0)
        else:
            print("\n⚠️ Presiona Enter para cerrar...")
            input()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Instalación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
