# 🚀 Sistema de Automatización Boot-ORO con Playwright

## 📋 Descripción
Sistema de automatización de órdenes HC con worker en background usando Playwright (Chromium).

## 🔧 Instalación

### 1. Instalar dependencias Python
```bash
pip install -r requirements.txt
```

### 2. Instalar navegador Chromium de Playwright
```bash
playwright install chromium
```

### 3. Verificar instalación
```bash
python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright OK')"
```

## 🎯 Características

### ✨ Worker de Automatización
- ✅ Procesamiento en background con Thread
- ✅ Navegador Chromium visible
- ✅ Sesión persistente (1 hora de inactividad)
- ✅ Auto-reabrir navegador si se cierra
- ✅ Máximo 2 intentos por paciente
- ✅ Sonidos de notificación
- ✅ Screenshots automáticos en errores

### 📊 Logging Triple
- **Consola**: Todos los eventos con emojis
- **UI**: Actualización en tiempo real
- **Archivo**: Solo warnings y errores (`logs/errors_YYYY-MM-DD.txt`)

### 🔄 Estados de Orden
| Estado Programación | Estado Caso | Descripción |
|---------------------|-------------|-------------|
| PENDIENTE | 2 | Programado, esperando procesamiento |
| EN_PROGRESO | 3 | Siendo procesado por el worker |
| COMPLETADO | 1 | Procesado exitosamente |
| ERROR | 4+ | Error después de 2 intentos |

## 📁 Estructura de Archivos

```
src/
├── utils/
│   └── logger.py                          # Sistema de logging
│
└── modules/autorizar_anexo3/
    ├── services/
    │   ├── programacion_service.py        # API de programación
    │   └── automation_worker.py           # Worker principal
    │
    └── playwright/
        ├── playwright_service.py          # Core Playwright
        ├── helpers_playwright.py          # Utilidades
        ├── login_playwright.py            # Login + CAPTCHA
        ├── home_playwright.py             # Navegación
        ├── ejecutar_casos_playwright.py   # Lógica casos
        └── ingreso_items_playwright.py    # CUPS
```

## 🔐 CAPTCHA

El sistema usa **TwoCaptcha** para resolver reCAPTCHA v2 automáticamente.
- API Key configurada en `login_playwright.py`
- Costo aproximado: $2.99 por cada 1000 CAPTCHAs
- Tiempo de resolución: 30-60 segundos

## 📸 Screenshots

Los screenshots de error se guardan en `screenshots/` con formato:
```
error_{id_orden}_{timestamp}.png
```

## 🔊 Sonidos

- **Completado**: Beep 1000Hz por 500ms (todos procesados)
- **Error**: Beep 400Hz por 1000ms (5+ errores consecutivos)

## ⚙️ Configuración

### Timeout de Inactividad
Editar en `automation_worker.py`:
```python
self.timeout_inactividad = 3600  # 1 hora (en segundos)
```

### Intervalo de Polling
```python
self.poll_interval = 5  # Consultar cada 5 segundos
```

### Intentos Máximos
```python
"intentos_maximos": 2  # En programacion_service.py
```

## 🐛 Debugging

### Ver logs en vivo
Los logs se muestran en consola con formato:
```
[2026-02-02 14:35:22.123] [ℹ️ INFO] [Worker] Mensaje
```

### Ver logs de errores
```bash
type logs\errors_2026-02-02.txt
```

### Screenshots de errores
```bash
dir screenshots\
```

## ❓ Solución de Problemas

### Error: "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### Error: "TwoCaptcha timeout"
- Verificar API key
- Verificar saldo en cuenta TwoCaptcha
- Verificar conexión a internet

### Navegador se cierra solo
- Revisar logs en `logs/errors_*.txt`
- El worker intentará reabrirlo automáticamente
- Si persiste, revisar memoria RAM del sistema

### Sesión se pierde constantemente
- Eliminar archivo `session_data/session_state.json`
- Dejar que resuelva CAPTCHA nuevamente
- El sistema guardará la nueva sesión

## 📞 API Endpoints Usados

- `GET /lis-pacientes-ordeneshc` - Listar órdenes
- `GET /programacion-ordenes?estado=PENDIENTE` - Órdenes pendientes
- `POST /programacion-ordenes` - Programar orden
- `PUT /programacion-ordenes/item/{id}` - Actualizar estado
- `PUT /h-itemordenesproced/{id}/estadoCaso` - Actualizar estado caso

## 🎨 Próximas Mejoras

- [ ] Procesamiento paralelo (múltiples tabs)
- [ ] Dashboard web de monitoreo
- [ ] Notificaciones de Windows
- [ ] Exportar reportes Excel
- [ ] Integración con Telegram/WhatsApp

---

**Versión**: 2.0 con Playwright  
**Última actualización**: Febrero 2026
