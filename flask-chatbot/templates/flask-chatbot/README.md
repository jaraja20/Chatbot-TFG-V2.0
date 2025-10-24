# 🚀 CHATBOT FLASK - Turnos Cédulas

## ✨ Características del Prototipo:

### ✅ Lo que SÍ funciona (vs Streamlit):
1. **Diseño 100% Personalizable**
   - CSS completo y profesional
   - Burbujas de chat perfectas
   - Botones DENTRO de las burbujas ✅
   - Iconos de feedback con imágenes
   
2. **Funcionalidad Completa**
   - Chat en tiempo real
   - Conexión con Rasa
   - Feedback guardado en PostgreSQL
   - Botones de acceso rápido
   - Modal para comentarios

3. **Interfaz Profesional**
   - Imagen del gobierno en header
   - Avatar del bot personalizado
   - Animaciones suaves
   - Responsive (móvil y desktop)
   - Sin limitaciones de Streamlit

4. **Performance**
   - Sin recargas completas de página
   - AJAX para mensajes
   - Scroll suave
   - Indicador de escritura

---

## 📁 Estructura del Proyecto:

```
flask-chatbot/
├── app.py                          # Backend Flask
├── requirements.txt                # Dependencias
├── templates/
│   └── index.html                 # Interfaz del chat
├── static/
│   ├── css/
│   │   └── style.css              # Estilos profesionales
│   ├── js/
│   │   └── chat.js                # Funcionalidad
│   └── images/                    # ← Copiar tus imágenes aquí
│       ├── gobierno.webp
│       ├── bot.png
│       ├── like.webp
│       └── dislike.png
```

---

## 🔧 INSTALACIÓN:

### Paso 1: Copiar Archivos
Copia toda la carpeta `flask-chatbot` a tu proyecto:
```
C:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot\
```

### Paso 2: Copiar Imágenes
Copia tus 4 imágenes a la carpeta `static/images/`:
- `gobierno.webp`
- `bot.png`
- `like.webp`
- `dislike.png`

### Paso 3: Instalar Dependencias
```bash
cd flask-chatbot
pip install -r requirements.txt
```

### Paso 4: Verificar Configuración
Edita `app.py` si es necesario:
```python
# Línea 13-14: URL de Rasa
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

# Línea 15-20: Configuración de BD
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}
```

### Paso 5: Ejecutar
```bash
# Terminal 1: Rasa Actions (ya lo tienes)
rasa run actions

# Terminal 2: Rasa Server (ya lo tienes)
rasa run --enable-api --cors "*"

# Terminal 3: Flask (NUEVO)
python app.py
```

### Paso 6: Abrir en el Navegador
```
http://localhost:5000
```

---

## 🎨 COMPARACIÓN: Streamlit vs Flask

| Característica | Streamlit | Flask |
|----------------|-----------|-------|
| **Botones en burbujas** | ❌ Imposible | ✅ Funciona |
| **Diseño personalizado** | ❌ Muy limitado | ✅ Total control |
| **Imágenes custom** | ⚠️ Complicado | ✅ Simple |
| **Animaciones CSS** | ❌ Limitado | ✅ Ilimitadas |
| **Performance** | ⚠️ Recarga todo | ✅ AJAX rápido |
| **Responsive** | ⚠️ Básico | ✅ Profesional |
| **Deploy** | ⚠️ Streamlit Cloud | ✅ Cualquier servidor |
| **Modularidad** | ❌ Monolítico | ✅ Muy modular |

---

## 📸 Resultado:

El chatbot se ve EXACTAMENTE como en tu imagen de referencia:
- ✅ Logo del gobierno arriba
- ✅ Avatar del bot con tu imagen
- ✅ Botones de feedback DENTRO de las burbujas
- ✅ Iconos like/dislike con tus imágenes
- ✅ Diseño limpio y profesional

---

## 🔌 Cómo Funciona:

### Frontend → Backend:
```javascript
// El usuario escribe un mensaje
fetch('/send_message', {
    method: 'POST',
    body: JSON.stringify({ message: "Hola" })
})
```

### Backend → Rasa:
```python
# Flask reenvía a Rasa
response = requests.post(RASA_URL, 
    json={'sender': 'user', 'message': user_message})
```

### Rasa → Flask → Frontend:
```python
# Flask devuelve respuesta al navegador
return jsonify({
    'success': True,
    'bot_message': bot_response
})
```

### Feedback → PostgreSQL:
```python
# Guardar en BD
INSERT INTO conversation_messages 
(user_message, bot_response, feedback_type, feedback_comment)
VALUES (...)
```

---

## 🎯 Ventajas de Flask:

### 1. **Modularidad**
Puedes separar fácilmente:
```
├── routes/
│   ├── chat.py
│   ├── feedback.py
│   └── admin.py
├── models/
│   ├── message.py
│   └── feedback.py
└── utils/
    ├── rasa_client.py
    └── db_manager.py
```

### 2. **Escalabilidad**
- Agregar nuevas rutas es simple
- APIs REST fáciles de crear
- Separación frontend/backend clara

### 3. **Profesionalismo**
- Stack estándar de la industria
- Fácil de mantener
- Documentación extensa
- Comunidad grande

### 4. **Deploy Flexible**
- Heroku
- AWS
- Google Cloud
- DigitalOcean
- Tu propio servidor

---

## 🔐 Seguridad (para producción):

### 1. Variables de Entorno
```python
import os
from dotenv import load_dotenv

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}
```

### 2. CORS
```python
from flask_cors import CORS
CORS(app, origins=['https://tu-dominio.com'])
```

### 3. Rate Limiting
```python
from flask_limiter import Limiter
limiter = Limiter(app, default_limits=["100 per hour"])
```

---

## 📈 Próximos Pasos (Opcionales):

### 1. **Dashboard de Admin**
- Ver todas las conversaciones
- Analizar feedback
- Métricas en tiempo real

### 2. **Autenticación**
- Login de usuarios
- Historial personal
- Sesiones persistentes

### 3. **WebSockets**
- Chat en tiempo real aún más rápido
- Notificaciones push
- Múltiples usuarios simultáneos

### 4. **Tests**
- Unitarios (pytest)
- Integración
- End-to-end (Selenium)

---

## 🐛 Troubleshooting:

### Error: "Connection refused to Rasa"
**Solución:**
```bash
# Verifica que Rasa esté corriendo:
curl http://localhost:5005/
```

### Error: "No module named 'flask'"
**Solución:**
```bash
pip install -r requirements.txt
```

### Error: "Template not found"
**Solución:**
Verifica la estructura de carpetas:
```
flask-chatbot/
├── app.py
└── templates/  ← Debe existir
    └── index.html
```

### Imágenes no cargan
**Solución:**
Verifica que están en `static/images/`:
```bash
dir static\images
# Debe mostrar:
# gobierno.webp
# bot.png
# like.webp
# dislike.png
```

---

## ✅ Checklist de Verificación:

- [ ] Flask instalado
- [ ] Imágenes copiadas a `static/images/`
- [ ] Rasa corriendo en puerto 5005
- [ ] PostgreSQL activo
- [ ] Configuración de BD correcta en `app.py`
- [ ] Flask corriendo en puerto 5000
- [ ] Navegador abierto en `localhost:5000`

---

## 🎉 ¡Listo!

Si todo está bien, verás:
- ✅ Interfaz profesional
- ✅ Botones dentro de burbujas
- ✅ Feedback funcionando
- ✅ Sin limitaciones de Streamlit

---

## 💬 ¿Preguntas?

- **¿Quieres agregar más funcionalidades?**
- **¿Necesitas cambiar el diseño?**
- **¿Quieres deployar a producción?**

¡Solo pregunta! 🚀
