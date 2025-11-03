# 🔑 CONFIGURACIÓN DE API - COPILOT AGENT

## ⚠️ IMPORTANTE: Para que el chat funcione con el GitHub Copilot REAL

Actualmente el sistema usa **respuestas simuladas**. Para que sea **YO (GitHub Copilot real)** quien responda, necesitas configurar una API.

---

## 🎯 OPCIÓN 1: OpenAI API (RECOMENDADO - Más fácil)

### Pasos:

1. **Crear cuenta en OpenAI**
   - Ir a: https://platform.openai.com/signup
   - Registrarse con email/Google

2. **Generar API Key**
   - Ir a: https://platform.openai.com/api-keys
   - Click en "Create new secret key"
   - Copiar la key (empieza con `sk-proj-...`)

3. **Agregar créditos**
   - Ir a: https://platform.openai.com/account/billing
   - Agregar $5-10 USD (suficiente para miles de mensajes)
   - Configurar límite de gasto si quieres

4. **Configurar en el proyecto**
   - Crear archivo `.env` en la carpeta `copilot_agent`
   - Agregar:
   ```
   OPENAI_API_KEY=sk-proj-tu_clave_aqui
   ```

5. **Reiniciar el servidor**
   - Detener Flask (Ctrl+C)
   - Ejecutar de nuevo: `python app.py`

---

## 🎯 OPCIÓN 2: GitHub Token (Si tienes GitHub Copilot)

### Pasos:

1. **Generar Personal Access Token**
   - Ir a: https://github.com/settings/tokens
   - Click en "Generate new token (classic)"
   - Seleccionar scope: `copilot`
   - Generar y copiar token

2. **Configurar en el proyecto**
   - Crear archivo `.env` en la carpeta `copilot_agent`
   - Agregar:
   ```
   GITHUB_TOKEN=ghp_tu_token_aqui
   ```
   
3. **Cambiar modo en app.py**
   - Abrir `app.py`
   - Buscar `API_MODE = 'openai'`
   - Cambiar a `API_MODE = 'github'`

4. **Reiniciar el servidor**

---

## 📝 Ejemplo de archivo .env

```bash
# .env (crear este archivo en copilot_agent/)

# OPCIÓN 1: OpenAI (recomendado)
OPENAI_API_KEY=sk-proj-ABC123...tu_clave_real...

# O OPCIÓN 2: GitHub
# GITHUB_TOKEN=ghp_XYZ789...tu_token_real...
```

---

## ✅ Verificar que funciona

Una vez configurado, pregunta en el chat:

**"¿Quién eres y cómo estás conectado?"**

Si responde con información REAL del proyecto y menciona que está usando la API, ¡está funcionando!

---

## 💰 Costos aproximados (OpenAI)

- GPT-4: ~$0.03 por 1000 tokens (aprox. 750 palabras)
- Conversación típica: $0.01 - $0.05
- $5 USD = cientos de conversaciones

---

## 🔒 Seguridad

⚠️ **NUNCA subas tu archivo `.env` a Git**

El archivo `.gitignore` ya está configurado para ignorarlo.

---

## 🆘 Problemas comunes

**Error: "No hay API key configurada"**
- Verifica que el archivo `.env` existe
- Verifica que la key está correctamente copiada
- Reinicia el servidor

**Error: "Invalid API key"**
- La key puede estar mal copiada
- Verifica que tienes créditos en OpenAI
- Verifica que la key no ha expirado

**Error: "Rate limit exceeded"**
- Espera unos minutos
- Verifica tus límites en OpenAI dashboard

---

## 📞 ¿Necesitas ayuda?

Si tienes problemas, pregúntame aquí en VS Code y te ayudo a configurarlo.
