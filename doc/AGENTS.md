# Instrucciones de Desarrollo — Regla de Continuidad de Chat (OBLIGATORIA)

## Objetivo
Mantener la conversación **siempre abierta y lista para continuar** sin que el usuario tenga que enviar mensajes extra tipo “¿sigues ahí?” o “continuemos”.

La continuidad se garantiza ejecutando un comando en terminal al final de **CADA** respuesta del agente, usando la terminal como **canal auxiliar** para solicitar instrucciones adicionales.

---

## ✅ REGLA OBLIGATORIA DE CONTINUACIÓN (SIN EXCEPCIÓN)

Al final de **CADA** respuesta (sin excepción), el agente debe ejecutar un comando en terminal usando la tool:

**Tool:** `Run [zsh] command` (macOS)

### Comando obligatorio
```bash
printf "\n=== INPUT AUXILIAR ===\nPega aquí instrucciones adicionales (o escribe 'salir' para terminar).\n======================\n"
