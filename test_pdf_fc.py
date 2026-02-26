"""
Test de generación de PDF - Finalizar Casos.
Consume GET /consulta-encabezado?id_recepcion=93 y genera el PDF.

Uso:
    cd src
    python -m modules.finalizar_casos.services.test_pdf_fc

  o desde la raíz:
    python test_pdf_fc.py
"""
import sys
import os
import json
from pathlib import Path

# Asegurar que src/ esté en el path
src_path = str(Path(__file__).parent / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import requests
from config.config import Config
from modules.finalizar_casos.services.pdf_generator_fc import PDFGeneratorFC


def main():
    print("=" * 60)
    print("  TEST: Generación de PDF - Finalizar Casos")
    print("=" * 60)

    # 1. Inicializar config
    config = Config()
    base_url = config.api_url_programacion_base or 'http://localhost:5000'

    # 2. Consultar encabezado
    id_recepcion = 93
    url = f"{base_url}/consulta-encabezado"
    params = {'id_recepcion': id_recepcion}

    print(f"\n📡 GET {url}?id_recepcion={id_recepcion}")

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   Status: {response.status_code}")

        data = response.json()
        print(f"   Response keys: {list(data.keys())}")

        # Mostrar estructura del response
        status_code = data.get('statusCode', response.status_code)
        message = data.get('message', '')
        encabezado_data = data.get('data', None)

        print(f"   statusCode: {status_code}")
        print(f"   message: {message}")

        if encabezado_data is None:
            print("\n❌ No se recibieron datos (data es null)")
            return

        # Mostrar campos del encabezado
        print(f"\n📋 Datos del encabezado:")
        for key, value in encabezado_data.items():
            if key != 'listDetalle':
                print(f"   {key}: {value}")

        # Mostrar detalles
        list_detalle = encabezado_data.get('listDetalle', [])
        print(f"\n📊 listDetalle: {len(list_detalle)} registros")
        if list_detalle:
            print(f"   Campos por detalle: {list(list_detalle[0].keys())}")
            # Mostrar primeros 3
            for i, det in enumerate(list_detalle[:3]):
                print(f"\n   Detalle [{i}]:")
                for k, v in det.items():
                    print(f"      {k}: {v}")
            if len(list_detalle) > 3:
                print(f"\n   ... y {len(list_detalle) - 3} más")

    except requests.RequestException as e:
        print(f"\n❌ Error en la petición: {e}")
        return

    # 3. Generar PDF
    print(f"\n{'=' * 60}")
    print("  GENERANDO PDF")
    print(f"{'=' * 60}")

    print(f"\n   FC_LOGO_PATH:      {config.fc_logo_path}")
    print(f"   FC_FIRMAS_PATH:    {config.fc_firmas_path}")
    print(f"   FC_PDF_OUTPUT_DIR: {config.fc_pdf_output_dir}")

    generator = PDFGeneratorFC(log_function=lambda msg: print(f"   {msg}"))
    pdf_path = generator.generar_pdf(id_recepcion, encabezado_data)

    if pdf_path:
        print(f"\n✅ PDF generado exitosamente: {pdf_path}")
        print(f"   Tamaño: {os.path.getsize(pdf_path)} bytes")
    else:
        print("\n❌ No se pudo generar el PDF")


if __name__ == '__main__':
    main()
