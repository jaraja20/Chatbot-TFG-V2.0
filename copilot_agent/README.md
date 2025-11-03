# 🤖 Copilot Agent - Chat Interface

Interfaz de chat directa con GitHub Copilot para comunicarte como si fuera este mismo chat de VS Code.

## 🚀 Instalación y Uso

### 1. Instalar dependencias

```bash
cd copilot_agent
pip install -r requirements.txt
```

### 2. Configurar API Key (IMPORTANTE)

Para que **YO (GitHub Copilot real)** responda, necesitas una API key:

**Opción A: OpenAI API (Recomendado - más fácil)**
1. Ir a https://platform.openai.com/api-keys
2. Crear una cuenta y generar API key
3. Agregar $5-10 de créditos
4. Crear archivo `.env` en esta carpeta:
```bash
OPENAI_API_KEY=sk-proj-tu_clave_aqui
```

**Opción B: GitHub Token (si tienes Copilot)**
1. Ir a https://github.com/settings/tokens
2. Generar token con scope `copilot`
3. Crear archivo `.env`:
```bash
GITHUB_TOKEN=ghp_tu_token_aqui
```

### 3. Ejecutar el servidor

```bash
python app.py
```

### 4. Abrir en el navegador

Abre tu navegador en:
```
http://localhost:5001
```

**NOTA:** Sin API key, solo verás respuestas simuladas. Con API key, será el GitHub Copilot REAL respondiendo.

## 📋 Características

- ✅ **Interfaz moderna** estilo VS Code
- ✅ **Conversación fluida** como este chat
- ✅ **Historial de conversación** mantenido en sesión
- ✅ **Respuestas contextuales** basadas en el historial
- ✅ **Diseño responsive** (móvil y escritorio)
- ✅ **Formato markdown** en mensajes
- ✅ **Indicadores de estado** (conectado, escribiendo, etc.)
- ✅ **Limpiar conversación** con un clic

## 🎨 Interfaz

La interfaz está diseñada para simular la experiencia de chat de GitHub Copilot:

- **Header**: Logo, título y controles
- **Área de mensajes**: Conversación con scroll automático
- **Input área**: Campo de texto con botón de envío
- **Indicadores**: Estado de conexión y carga

## 🔧 Arquitectura

```
Usuario → Frontend (HTML/CSS/JS) → Flask Backend → Copilot Simulation
                                                    ↓
                                            Respuestas inteligentes
```

### Endpoints disponibles:

- `GET /` - Página principal del chat
- `POST /chat` - Enviar mensaje y recibir respuesta
- `GET /history` - Obtener historial de conversación
- `POST /clear` - Limpiar conversación
- `GET /health` - Estado del servidor

## 📝 Notas

**IMPORTANTE**: Esta es una versión de **demostración/prueba**. Las respuestas son simuladas con lógica básica.

Para integración real con GitHub Copilot API:
1. Necesitarás un token de acceso de GitHub
2. Descomentar las líneas de código API en `app.py`
3. Configurar las credenciales apropiadas

## 🎯 Próximos pasos

Una vez que confirmes que esta interfaz funciona, podemos:

1. Integrar con el sistema de turnos real
2. Conectar con la base de datos de tu proyecto
3. Añadir funcionalidades específicas del chatbot de cédulas
4. Integrar con el motor difuso y las recomendaciones

## 💡 Uso

### Atajos de teclado:
- `Enter`: Enviar mensaje
- `Shift + Enter`: Nueva línea en el mensaje

### Funciones:
- Click en el ícono de papelera (🗑️): Limpiar conversación
- Estado verde (●): Servidor conectado
- Puntos animados: Copilot está escribiendo...

---

**¡Prueba el chat y avísame cómo funciona!** 🚀
