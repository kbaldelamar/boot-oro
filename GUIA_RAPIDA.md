# 🚀 GUÍA RÁPIDA DE USO - Sistema de Automatización Playwright

## ⚡ Instalación Rápida

### Opción 1: Instalación Automatizada (Recomendada)
```bash
python install_playwright.py
```

### Opción 2: Instalación Manual
```bash
pip install -r requirements.txt
playwright install chromium
python test_playwright_setup.py
```

---

## 📖 Cómo Usar el Sistema

### PASO 1: Iniciar la Aplicación
```bash
python main.py
```

### PASO 2: Programar Órdenes
1. Ve al menú **Procesos → Autorizar - Anexo 3**
2. Verás la tabla de Órdenes HC
3. **Click en el encabezado ☑** para seleccionar todas (o click individual en cada fila)
4. Click en **"📅 Programar Seleccionados"**
5. Confirma la programación

> ✅ Las órdenes ahora tienen estadoCaso=2 (Programado)

### PASO 3: Iniciar el Worker
1. Ve al menú **Procesos → Worker Automatización**
2. Click en **"▶️ Iniciar Worker"**
3. El navegador Chromium se abrirá automáticamente
4. **IMPORTANTE**: En el primer inicio, espera 30-60 segundos mientras resuelve el CAPTCHA con TwoCaptcha

### PASO 4: Monitorear el Proceso
El panel del Worker muestra:
- **Estado**: 🟢 ACTIVO / 🟡 PAUSADO / ⚪ INACTIVO
- **Estadísticas**: Procesados / Exitosos / Errores
- **Tabla**: Órdenes programadas con su estado actual
- **Logs en Vivo**: Cada acción del worker

### PASO 5: Controlar el Worker
- **⏸️ Pausar**: Detiene temporalmente (mantiene navegador abierto)
- **▶️ Reanudar**: Continúa desde donde se pausó
- **⏹️ Detener**: Cierra navegador y detiene completamente

---

## 🎯 Estados de las Órdenes

| Estado | Emoji | Descripción |
|--------|-------|-------------|
| **PENDIENTE** | ⏳ | Esperando ser procesada |
| **EN_PROGRESO** | 🔵 | Worker la está procesando ahora |
| **COMPLETADO** | ✅ | Procesada exitosamente |
| **ERROR** | ❌ | Falló después de 2 intentos |

---

## 🔊 Alertas del Sistema

### Sonidos
- **Beep corto (1000Hz)**: Todas las órdenes pendientes completadas
- **Beep largo (400Hz)**: 5+ errores consecutivos detectados

### Navegador
- **Se cierra automáticamente** después de 1 hora sin órdenes pendientes
- **Se abre automáticamente** cuando hay nuevas órdenes programadas
- **Sesión persistente**: No necesita resolver CAPTCHA en cada apertura

---

## 📁 Archivos Importantes

### Logs
```
logs/errors_2026-02-02.txt    # Errores del día
```

### Screenshots
```
screenshots/error_381561_*.png    # Capturas de errores
```

### Sesión del Navegador
```
session_data/session_state.json   # Sesión persistente
```

---

## 💡 Tips y Trucos

### 1. Resolver CAPTCHA Manualmente (Si Falla TwoCaptcha)
Si TwoCaptcha falla o tarda mucho:
1. El navegador quedará abierto en la página de login
2. Resuelve el CAPTCHA manualmente
3. Click en "Iniciar Sesión"
4. El worker continuará automáticamente

### 2. Programar Órdenes Específicas
- **Selecciona solo algunas**: Click individual en cada fila
- **Selecciona por estado**: Programa solo estadoCaso=0 (sin programar)

### 3. Monitorear Desde Lejos
Los logs en el panel se actualizan en tiempo real. Puedes:
- Minimizar la ventana
- Dejar el worker trabajando solo
- Los sonidos te notificarán cuando termine

### 4. Limpiar Sesión (Si Hay Problemas)
Si el navegador se comporta extraño:
```bash
# Eliminar sesión guardada
del session_data\session_state.json
```
El worker creará una nueva sesión en el siguiente inicio.

### 5. Ver Detalles de Errores
Cada error crea:
- ✅ Entrada en logs con timestamp
- ✅ Screenshot automático
- ✅ Mensaje en tabla de programados

---

## 🚨 Solución de Problemas Comunes

### ❌ "Worker no inicia"
**Solución**:
1. Verifica que el API esté corriendo: http://localhost:5000
2. Revisa logs en consola
3. Ejecuta: `python test_playwright_setup.py`

### ❌ "CAPTCHA no se resuelve"
**Solución**:
1. Verifica API key de TwoCaptcha en `login_playwright.py`
2. Verifica saldo en cuenta: https://2captcha.com/balance
3. Resuelve manualmente (ver Tips arriba)

### ❌ "Navegador se cierra solo"
**Solución**:
- Es normal después de 1 hora sin actividad
- Se reabrirá automáticamente cuando haya órdenes pendientes

### ❌ "No encuentra elementos en la página"
**Posibles causas**:
1. La página cambió de estructura (xpaths obsoletos)
2. Conexión lenta → aumentar timeouts
3. Sesión expirada → eliminar session_state.json

---

## 📊 Rendimiento Esperado

### Tiempos Promedio
- **Por paciente**: 2-4 minutos
- **500 pacientes**: ~16-33 horas (1-2 días)

### Optimización Futura
- ⏳ Procesamiento paralelo (múltiples tabs)
- ⏳ Cache de datos frecuentes
- ⏳ Predicción de errores

---

## 📞 Comandos Útiles

```bash
# Ver logs de hoy
type logs\errors_2026-02-02.txt

# Listar screenshots
dir screenshots\

# Verificar instalación
python test_playwright_setup.py

# Reinstalar Chromium
playwright install chromium --force

# Ver órdenes programadas (API directa)
curl http://localhost:5000/programacion-ordenes?estado=PENDIENTE
```

---

## ✅ Checklist Pre-Uso

Antes de usar el sistema, verifica:

- [ ] Python 3.7+ instalado
- [ ] `python install_playwright.py` ejecutado exitosamente
- [ ] API en http://localhost:5000 corriendo
- [ ] TwoCaptcha API key válida
- [ ] Conexión a internet estable

---

## 🎓 Flujo Completo Resumido

```
1. Abrir aplicación (main.py)
   ↓
2. Ir a "Autorizar - Anexo 3"
   ↓
3. Seleccionar pacientes (click en ☑)
   ↓
4. Click "Programar Seleccionados"
   ↓
5. Ir a "Worker Automatización"
   ↓
6. Click "Iniciar Worker"
   ↓
7. Esperar resolución de CAPTCHA (30-60 seg)
   ↓
8. Worker procesa automáticamente
   ↓
9. Monitorear en tabla y logs
   ↓
10. Sonido cuando termina todos
```

---

**¿Dudas?** Revisa `PLAYWRIGHT_README.md` para documentación técnica completa.

**¡Listo! 🚀 El sistema está completamente funcional.**
