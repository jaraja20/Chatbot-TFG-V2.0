# 🚀 Guía Rápida: Cómo Probar el Sistema en el Frontend

## 📋 Pre-requisitos

Antes de iniciar el frontend, asegúrate de tener estos servicios corriendo:

### 1. ✅ LM Studio (Ya está corriendo)
```
✅ Modelo: Llama 3.1 cargado
✅ URL: http://localhost:1234
✅ Estado: Verificado en los tests (93.3% precisión)
```

### 2. 🔄 Rasa Server (Necesitas iniciarlo)
```powershell
# En una nueva terminal:
cd "c:\tfg funcional\Chatbot-TFG-V2.0"
rasa run --enable-api --cors "*" --port 5005
```

### 3. 🔄 Rasa Actions Server (Necesitas iniciarlo)
```powershell
# En otra terminal:
cd "c:\tfg funcional\Chatbot-TFG-V2.0"
rasa run actions
```

### 4. 🔄 Base de Datos PostgreSQL (Debería estar corriendo)
```
✅ Database: chatbotdb
✅ User: botuser
✅ Host: localhost
```

---

## 🎯 Iniciar el Frontend

### Opción 1: Flask Chatbot Principal (Recomendado)
```powershell
# Desde la raíz del proyecto:
cd "c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot"
& "C:/tfg funcional/.venv/Scripts/python.exe" app.py
```

**URL del Frontend:** http://localhost:5000

### Opción 2: Copilot Agent (Interfaz alternativa)
```powershell
cd "c:\tfg funcional\Chatbot-TFG-V2.0\copilot_agent"
& "C:/tfg funcional/.venv/Scripts/python.exe" app.py
```

**URL del Frontend:** http://localhost:5001

---

## 🧪 Casos de Prueba en el Frontend

Una vez que el frontend esté corriendo, prueba estos mensajes:

### ✅ Casos que Funcionan al 100%

1. **Saludos**
   - "hola"
   - "buenas tardes"
   - "qué tal"

2. **Agendar Turno**
   - "quiero sacar un turno"
   - "necesito una cita"
   - "quiero agendar"

3. **Consultas de Disponibilidad**
   - "qué horarios hay disponibles"
   - "hay turnos para mañana"
   - "cuándo puedo ir"

4. **Datos Personales**
   - "mi nombre es Juan Pérez"
   - "me llamo María"
   - "soy 12345678" (cédula)

5. **Fechas y Horas**
   - "para mañana"
   - "el lunes"
   - "a las 10 de la mañana"

6. **Consultas de Tiempo de Espera (MOTOR DIFUSO)**
   - "cuánto voy a esperar"
   - "cuánto demora"
   - "hay mucha gente"

7. **Información General**
   - "dónde queda la oficina"
   - "qué requisitos necesito"
   - "cuánto cuesta"

8. **Cancelaciones**
   - "quiero cancelar mi turno"
   - "necesito cancelar"
   - "no puedo ir"

9. **Confirmaciones**
   - "sí confirmo"
   - "está bien"
   - "no gracias"

---

## 🔍 Verificar que Todo Funciona

### 1. Verificar que LM Studio responde:
```powershell
curl http://localhost:1234/v1/models
```

Deberías ver información del modelo cargado.

### 2. Verificar que Rasa responde:
```powershell
curl http://localhost:5005/status
```

Deberías ver `{"status": "ok"}`

### 3. Abrir el navegador:
```
http://localhost:5000
```

---

## 🎯 Flujo de Conversación Completo

Prueba este flujo completo en el chat:

```
Usuario: hola
Bot: [Saludo]

Usuario: quiero sacar un turno
Bot: [Solicita nombre]

Usuario: me llamo Juan Pérez
Bot: [Confirma nombre, solicita cédula]

Usuario: 12345678
Bot: [Confirma cédula, solicita fecha]

Usuario: para mañana
Bot: [Confirma fecha, solicita hora]

Usuario: a las 10
Bot: [Confirma turno completo]

Usuario: sí confirmo
Bot: [Turno confirmado con QR]
```

---

## 🧠 Prueba del Motor Difuso

Para probar que el motor difuso está integrado con Llama 3.1:

```
Usuario: cuánto voy a esperar?
Bot: [El sistema usa motor_difuso.calcular_espera() y responde]

Usuario: recomiéndame un horario
Bot: [El sistema usa motor_difuso.evaluar_recomendacion() y responde]
```

---

## 📊 Dashboard (Opcional)

Para ver las estadísticas de las conversaciones:

```
http://localhost:5000/dashboard
```

---

## ⚠️ Solución de Problemas

### Problema: "Error conectando con Rasa"
**Solución:** Verifica que Rasa esté corriendo en el puerto 5005
```powershell
rasa run --enable-api --cors "*" --port 5005
```

### Problema: "LM Studio no disponible"
**Solución:** Verifica que LM Studio esté corriendo y tenga un modelo cargado

### Problema: "Error de base de datos"
**Solución:** Verifica que PostgreSQL esté corriendo:
```powershell
# Verificar servicio PostgreSQL
Get-Service postgresql*
```

### Problema: "Actions server no responde"
**Solución:** Inicia el servidor de actions:
```powershell
rasa run actions
```

---

## 🎉 ¡Listo!

Ahora tienes:
- ✅ Llama 3.1 con contexto completo del proyecto
- ✅ Motor difuso integrado
- ✅ 93.3% de precisión en clasificación
- ✅ Frontend funcional para pruebas

**Disfruta tu chatbot inteligente! 🚀**
