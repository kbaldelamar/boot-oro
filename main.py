"""
Punto de entrada principal de la aplicación.
Sistema de Automatización - Boot ORO
"""
import sys
from pathlib import Path

# Agregar el directorio src al path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from ui import MainWindow
from config import Config


def main():
    """
    Función principal de la aplicación.
    """
    try:
        # Inicializar configuración
        config = Config()
        
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
        sys.exit(1)


if __name__ == "__main__":
    main()
