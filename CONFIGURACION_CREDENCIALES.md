# ⚙️ Configuración de Credenciales - Playwright Automation

## 📝 Archivo: login_playwright.py

Este archivo contiene las credenciales de acceso. Por seguridad, deberías moverlas a variables de entorno.

### Ubicación del Archivo
```
src/modules/autorizar_anexo3/playwright/login_playwright.py
```

### Líneas 20-22 (aproximadamente)
```python
# Credenciales (considera moverlas a config)
self.usuario = "alejandra.garnica@biomedvida.com"
self.password = "Biomed123*"
```

---

## 🔐 Opciones de Configuración

### Opción 1: Variables de Entorno (Recomendada)

#### 1. Crear archivo `.env` en la raíz del proyecto:
```env
LOGIN_EMAIL=tu_email@ejemplo.com
LOGIN_PASSWORD=tu_password_seguro
TWOCAPTCHA_API_KEY=tu_api_key_aqui
```

#### 2. Instalar python-dotenv:
```bash
pip install python-dotenv
```

#### 3. Modificar login_playwright.py:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class LoginPlaywright:
    def __init__(self, page: Page, logger: AdvancedLogger):
        self.page = page
        self.logger = logger
        self.helper = PlaywrightHelper(page)
        
        # Cargar desde variables de entorno
        self.usuario = os.getenv('LOGIN_EMAIL')
        self.password = os.getenv('LOGIN_PASSWORD')
        self.captcha_api_key = os.getenv('TWOCAPTCHA_API_KEY')
        self.captcha_site_key = '6LdlqfwhAAAAANGjtq9te3mKQZwqgoey8tOZ44ua'
```

### Opción 2: Archivo de Configuración JSON

#### 1. Crear `credentials.json`:
```json
{
  "login": {
    "email": "tu_email@ejemplo.com",
    "password": "tu_password_seguro"
  },
  "twocaptcha": {
    "api_key": "tu_api_key_aqui"
  }
}
```

#### 2. Modificar login_playwright.py:
```python
import json

class LoginPlaywright:
    def __init__(self, page: Page, logger: AdvancedLogger):
        # Cargar credenciales
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        
        self.usuario = creds['login']['email']
        self.password = creds['login']['password']
        self.captcha_api_key = creds['twocaptcha']['api_key']
```

**⚠️ IMPORTANTE**: Agrega `credentials.json` a `.gitignore`

---

## 🔑 TwoCaptcha API Key

### Cómo Obtener
1. Registrarse en: https://2captcha.com
2. Ir a: https://2captcha.com/enterpage
3. Copiar tu API Key
4. Mínimo recomendado: $5 USD de saldo

### Costo
- **1000 reCAPTCHAs**: ~$2.99 USD
- **500 pacientes**: ~$1.50 USD (si resuelves CAPTCHA una vez y reutilizas sesión)

---

## 🌐 URL de la Aplicación

### Línea en login_playwright.py (método hacer_login):
```python
if not self.playwright_service.navegar_a("https://tuurl.com/login"):
```

### Modificar en automation_worker.py:
```python
def hacer_login(self) -> bool:
    try:
        # CAMBIAR ESTA URL
        if not self.playwright_service.navegar_a("https://tuurl.com/login"):
            return False
```

**Cambia** `"https://tuurl.com/login"` por la URL real de tu aplicación.

---

## 📋 Configuración Completa - Checklist

- [ ] Cambiar usuario y password en `login_playwright.py`
- [ ] Cambiar TwoCaptcha API Key
- [ ] Verificar saldo en TwoCaptcha
- [ ] Cambiar URL de login en `automation_worker.py`
- [ ] (Opcional) Mover a variables de entorno
- [ ] (Opcional) Agregar `.env` o `credentials.json` a `.gitignore`

---

## 🛡️ Seguridad

### ⚠️ NUNCA hagas:
- ❌ Subir credenciales a Git
- ❌ Compartir tu API Key de TwoCaptcha
- ❌ Dejar credenciales en código en producción

### ✅ Siempre:
- ✅ Usar variables de entorno en producción
- ✅ Agregar archivos sensibles a `.gitignore`
- ✅ Rotar passwords regularmente
- ✅ Usar diferentes credenciales para testing

---

## 📄 Ejemplo de .gitignore

Agrega esto a tu `.gitignore`:
```
# Credenciales
.env
credentials.json
session_data/
*.key
*.pem

# Logs y screenshots (opcional)
logs/
screenshots/

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
```

---

**Configuración actualizada y lista! ✅**
