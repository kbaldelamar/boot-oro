# 📸 Instrucciones para el Logo del Anexo 3

## 📁 Ubicación de la imagen

Guarda la imagen del encabezado del Anexo 3 en:

```
c:\python\boot-oro\resources\images\anexo3_header.png
```

## 🖼️ Características de la imagen

La imagen debe contener:
- **Escudo de Colombia** (lado izquierdo)
- **Texto:** "MINISTERIO DE SALUD Y PROTECCIÓN SOCIAL" (centro)
- **Texto:** "ANEXO TÉCNICO No. 3" (derecha)
- **Texto:** "SOLICITUD DE AUTORIZACIÓN DE SERVICIOS DE SALUD" (abajo)

### Especificaciones técnicas:
- **Formato:** PNG (preferido) o JPG
- **Ancho recomendado:** 1800-2000 píxeles
- **Alto recomendado:** 250-300 píxeles
- **Resolución:** 300 DPI para mejor calidad de impresión
- **Fondo:** Blanco o transparente

## 🎨 Cómo obtener la imagen

### Opción 1: Captura de pantalla del PDF oficial
1. Abre el PDF oficial del Anexo 3
2. Toma una captura de pantalla solo del encabezado
3. Recorta la imagen para incluir solo el header
4. Guárdala como `anexo3_header.png`

### Opción 2: Crear la imagen (si tienes los recursos)
Si tienes acceso a las imágenes oficiales:
1. Usa un editor de imágenes (Photoshop, GIMP, etc.)
2. Coloca el escudo de Colombia
3. Agrega los textos con las fuentes correctas
4. Exporta como PNG de alta calidad

### Opción 3: Extraer del documento Word oficial
Si tienes el documento Word del Anexo 3:
1. Abre el documento
2. Haz clic derecho en la imagen del encabezado
3. Selecciona "Guardar como imagen..."
4. Guarda como `anexo3_header.png`

## 📝 Pasos para agregar la imagen

1. **Guarda la imagen** en la carpeta correcta:
   ```
   c:\python\boot-oro\resources\images\anexo3_header.png
   ```

2. **Verifica la ruta** (la carpeta ya existe):
   ```
   c:\python\boot-oro\resources\
   └── images\
       └── anexo3_header.png  ← Coloca tu imagen aquí
   ```

3. **Prueba el PDF:**
   ```bash
   python test_generar_pdf_anexo3.py
   ```

## ✅ Verificación

Cuando ejecutes el script de prueba, verás en los logs:

**Si la imagen existe:**
```
✅ Logo cargado desde: c:\python\boot-oro\resources\images\anexo3_header.png
```

**Si la imagen NO existe:**
```
⚠️ Logo no encontrado en: c:\python\boot-oro\resources\images\anexo3_header.png
```

En este caso, el PDF se generará con un header de texto alternativo.

## 🔧 Solución de problemas

### La imagen no se carga
1. Verifica que el archivo se llame **exactamente** `anexo3_header.png`
2. Verifica que esté en la carpeta correcta
3. Verifica que el formato sea PNG o JPG

### La imagen se ve distorsionada
Ajusta las dimensiones en el código (`pdf_anexo3_service.py`):
```python
img = Image(str(self.logo_path), width=180*mm, height=25*mm)
```

Modifica `width` y `height` según sea necesario.

### La imagen se ve borrosa
- Usa una imagen de mayor resolución (300 DPI mínimo)
- Verifica que la imagen original sea de buena calidad

## 📋 Nombre del archivo

**Importante:** El archivo debe llamarse **exactamente**:
```
anexo3_header.png
```

No uses:
- ❌ `Anexo3_Header.png`
- ❌ `anexo 3 header.png`
- ❌ `logo.png`
- ❌ `header.png`

## 🎯 Resultado final

Una vez agregada la imagen correctamente, el PDF generado tendrá:
1. ✅ Logo oficial del Ministerio de Salud en el encabezado
2. ✅ Apariencia profesional e idéntica al formato oficial
3. ✅ Lista para ser impresa o enviada digitalmente
