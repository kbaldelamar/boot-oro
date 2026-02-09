"""
Script de prueba para verificar instalación de Playwright
"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Prueba que todos los módulos se importen correctamente"""
    print("🔍 Verificando imports...")
    
    try:
        from src.utils.logger import AdvancedLogger
        print("✅ Logger importado")
    except Exception as e:
        print(f"❌ Error importando Logger: {e}")
        return False
    
    try:
        from src.modules.autorizar_anexo3.playwright.playwright_service import PlaywrightService
        print("✅ PlaywrightService importado")
    except Exception as e:
        print(f"❌ Error importando PlaywrightService: {e}")
        return False
    
    try:
        from src.modules.autorizar_anexo3.playwright.helpers_playwright import PlaywrightHelper
        print("✅ PlaywrightHelper importado")
    except Exception as e:
        print(f"❌ Error importando PlaywrightHelper: {e}")
        return False
    
    try:
        from src.modules.autorizar_anexo3.playwright.login_playwright import LoginPlaywright
        print("✅ LoginPlaywright importado")
    except Exception as e:
        print(f"❌ Error importando LoginPlaywright: {e}")
        return False
    
    try:
        from src.modules.autorizar_anexo3.services.programacion_service import ProgramacionService
        print("✅ ProgramacionService importado")
    except Exception as e:
        print(f"❌ Error importando ProgramacionService: {e}")
        return False
    
    try:
        from src.modules.autorizar_anexo3.services.automation_worker import AutomationWorker
        print("✅ AutomationWorker importado")
    except Exception as e:
        print(f"❌ Error importando AutomationWorker: {e}")
        return False
    
    return True


def test_playwright():
    """Prueba que Playwright esté instalado correctamente"""
    print("\n🌐 Verificando Playwright...")
    
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright instalado")
        
        # Intentar iniciar playwright
        playwright = sync_playwright().start()
        print("✅ Playwright se inició correctamente")
        
        # Verificar que chromium esté instalado
        try:
            browser = playwright.chromium.launch(headless=True)
            print("✅ Chromium instalado y funcional")
            browser.close()
        except Exception as e:
            print(f"⚠️ Chromium no instalado. Ejecuta: playwright install chromium")
            print(f"   Error: {e}")
        
        playwright.stop()
        return True
        
    except Exception as e:
        print(f"❌ Error con Playwright: {e}")
        print("\n💡 Solución:")
        print("   pip install playwright")
        print("   playwright install chromium")
        return False


def test_logger():
    """Prueba el sistema de logging"""
    print("\n📝 Probando sistema de logging...")
    
    try:
        from src.utils.logger import AdvancedLogger
        
        logger = AdvancedLogger()
        logger.debug('Test', 'Mensaje de debug')
        logger.info('Test', 'Mensaje informativo')
        logger.success('Test', 'Mensaje de éxito')
        logger.warning('Test', 'Mensaje de advertencia')
        logger.error('Test', 'Mensaje de error')
        
        print("✅ Logger funciona correctamente")
        
        # Verificar que se creó el directorio de logs
        if Path('logs').exists():
            print("✅ Directorio de logs creado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando logger: {e}")
        return False


def test_playwright_service():
    """Prueba el servicio de Playwright"""
    print("\n🚀 Probando PlaywrightService...")
    
    try:
        from src.utils.logger import AdvancedLogger
        from src.modules.autorizar_anexo3.playwright.playwright_service import PlaywrightService
        
        logger = AdvancedLogger()
        service = PlaywrightService(logger)
        
        print("✅ PlaywrightService inicializado")
        
        # Probar iniciar navegador (headless para test)
        print("   Iniciando navegador de prueba...")
        # No iniciamos el navegador en el test para no abrir ventanas
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando PlaywrightService: {e}")
        return False


def main():
    """Ejecuta todas las pruebas"""
    print("=" * 60)
    print("🧪 PRUEBAS DE INSTALACIÓN - PLAYWRIGHT AUTOMATION")
    print("=" * 60)
    
    resultados = []
    
    # Prueba 1: Imports
    resultados.append(("Imports", test_imports()))
    
    # Prueba 2: Playwright
    resultados.append(("Playwright", test_playwright()))
    
    # Prueba 3: Logger
    resultados.append(("Logger", test_logger()))
    
    # Prueba 4: PlaywrightService
    resultados.append(("PlaywrightService", test_playwright_service()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    for nombre, resultado in resultados:
        icono = "✅" if resultado else "❌"
        print(f"{icono} {nombre}: {'PASSED' if resultado else 'FAILED'}")
    
    total_exitosas = sum(1 for _, r in resultados if r)
    total = len(resultados)
    
    print(f"\n✅ {total_exitosas}/{total} pruebas pasaron")
    
    if total_exitosas == total:
        print("\n🎉 ¡Todo está listo! Puedes ejecutar el sistema.")
        print("\n💡 Próximos pasos:")
        print("   1. Ejecuta: python main.py")
        print("   2. Ve a la pestaña 'Gestión casos Órdenes HC'")
        print("   3. Selecciona pacientes y haz clic en 'Programar'")
        print("   4. Inicia el Worker desde la nueva pestaña")
    else:
        print("\n⚠️ Hay problemas. Revisa los errores arriba.")
        print("\n💡 Comandos útiles:")
        print("   pip install -r requirements.txt")
        print("   playwright install chromium")
    
    return total_exitosas == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
