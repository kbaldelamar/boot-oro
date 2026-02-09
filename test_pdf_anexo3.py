"""
Script de prueba para generar PDF del Anexo 3
"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import AdvancedLogger
from src.config.config import Config
from src.modules.autorizar_anexo3.services.pdf_anexo3_service import PDFAnexo3Service


def main():
    print("=" * 80)
    print("🧪 PRUEBA DE GENERACIÓN DE PDF ANEXO 3")
    print("=" * 80)
    
    # Inicializar logger y config
    logger = AdvancedLogger()
    config = Config()
    
    logger.info('TestPDF', 'Iniciando prueba de generación de PDF')
    
    # Datos de prueba
    id_atencion = 265552
    id_orden = 122465
    id_procedimiento = 881301
    
    print(f"\n📋 Datos de prueba:")
    print(f"   - ID Atención: {id_atencion}")
    print(f"   - ID Orden: {id_orden}")
    print(f"   - ID Procedimiento (CUPS): {id_procedimiento}")
    
    try:
        # Crear servicio de PDF
        pdf_service = PDFAnexo3Service(logger, config)
        
        print(f"\n🌐 Consultando: http://localhost:5000/datos-orden-atencion")
        print(f"   ?idAtencion={id_atencion}&idOrden={id_orden}&idProcedimiento={id_procedimiento}")
        
        # Generar PDF
        print(f"\n📄 Generando PDF del Anexo 3...")
        filepath = pdf_service.generar_anexo3(
            id_atencion=id_atencion,
            id_orden=id_orden,
            id_procedimiento=id_procedimiento
        )
        
        print(f"\n✅ PDF generado exitosamente!")
        print(f"📁 Ubicación: {filepath}")
        
        # Intentar abrir el PDF
        try:
            import os
            os.startfile(filepath)
            print(f"👀 Abriendo PDF en visor predeterminado...")
        except Exception as e:
            print(f"⚠️ No se pudo abrir automáticamente: {e}")
            print(f"   Abre manualmente: {filepath}")
        
        return True
        
    except Exception as e:
        logger.error('TestPDF', 'Error durante la prueba', e)
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 Prueba completada exitosamente")
        print("\n💡 El PDF usa PyMuPDF con:")
        print("   ✅ Casillas individuales para caracteres")
        print("   ✅ Checkboxes para selecciones")
        print("   ✅ Logo oficial (si está configurado)")
        print("   ✅ Layout preciso del Anexo 3")
    else:
        print("❌ La prueba falló")
        print("\n💡 Verifica:")
        print("   1. La API debe estar corriendo en http://localhost:5000")
        print("   2. PyMuPDF debe estar instalado: pip install PyMuPDF")
        print("   3. La carpeta de salida debe existir (se crea automáticamente)")
    print("=" * 80)
    
    sys.exit(0 if success else 1)
