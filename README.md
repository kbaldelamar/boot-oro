# Sistema de Automatización - Boot ORO

Aplicación de escritorio para automatizar procesos de autorización y gestión de órdenes médicas.

## 🚀 Características

- **Interfaz Gráfica Intuitiva**: Menú de navegación para acceder a diferentes módulos
- **Gestión Centralizada de Configuración**: Todas las credenciales y endpoints en un solo archivo
- **Panel de Autorización Anexo 3**: Búsqueda y autorización de órdenes
- **Arquitectura Limpia**: Código organizado y modular

## 📁 Estructura del Proyecto

```
boot-oro/
├── main.py                 # Punto de entrada de la aplicación
├── endpoint.env            # Configuración de endpoints y credenciales
├── requirements.txt        # Dependencias del proyecto
├── README.md              # Este archivo
└── src/
    ├── __init__.py
    ├── config/            # Módulo de configuración
    │   ├── __init__.py
    │   └── config.py      # Clase Config (Singleton)
    ├── ui/                # Interfaz de usuario
    │   ├── __init__.py
    │   └── main_window.py # Ventana principal
    └── panels/            # Paneles de funcionalidad
        ├── __init__.py
        └── autorizar_anexo3.py
```

## ⚙️ Instalación

1. **Clonar o descargar el proyecto**

2. **Crear un entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # En Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el archivo endpoint.env**
   - Editar el archivo `endpoint.env` con tus credenciales y endpoints

## 🎯 Uso

Para ejecutar la aplicación:

```bash
python main.py
```

## 🔧 Configuración

Todas las configuraciones se gestionan a través del archivo `endpoint.env`:

- **Endpoints de API**: URLs de los servicios
- **Credenciales**: Email y contraseña de acceso
- **Información de la IPS**: Nombre, NIT, sede

### Acceder a la configuración en el código:

```python
from config import Config

config = Config()
url = config.api_url_ordenes_hc
email = config.login_email
```

## 📋 Módulos Disponibles

### 1. Autorizar - Anexo 3
- Búsqueda de órdenes por número o documento
- Visualización de resultados en tabla
- Autorización de órdenes seleccionadas
- Log de actividad en tiempo real

## 🔜 Próximas Funcionalidades

Para agregar nuevos paneles:

1. Crear un nuevo archivo en `src/panels/`
2. Implementar la clase heredando de `ttk.Frame`
3. Registrar el panel en `main_window.py`
4. Agregar opción en el menú

## 📝 Notas

- La aplicación usa `tkinter` que viene incluido con Python
- Las llamadas a API están preparadas pero comentadas (se usan datos de ejemplo)
- Para producción, descomentar las secciones de llamadas HTTP reales

## 🛠️ Desarrollo

### Agregar un nuevo panel:

```python
# En src/panels/nuevo_panel.py
import tkinter as tk
from tkinter import ttk

class NuevoPanelPanel(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        # Tu código aquí
```

### Registrar en main_window.py:

```python
from panels.nuevo_panel import NuevoPanelPanel
self.panels_registry['nuevo_panel'] = NuevoPanelPanel
```

## 📄 Licencia

© 2026 - Todos los derechos reservados

---

**Versión**: 1.0.0  
**Fecha**: Enero 2026
