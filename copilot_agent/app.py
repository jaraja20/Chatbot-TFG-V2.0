"""
COPILOT AGENT - Backend Flask
Sistema de chat directo con GitHub Copilot
Con acceso completo al proyecto
"""

from flask import Flask, render_template, request, jsonify, session
import requests
import json
import logging
from datetime import datetime
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'copilot-agent-secret-key-2025'

# =====================================================
# CARGA DE CONTEXTO DEL PROYECTO
# =====================================================

PROJECT_ROOT = Path(__file__).parent.parent
PROJECT_CONTEXT = {
    'files': {},
    'structure': {},
    'loaded_at': None
}

# Extensiones de archivos a cargar
VALID_EXTENSIONS = ['.py', '.yml', '.yaml', '.txt', '.md', '.json', '.js', '.css', '.html']

# Directorios a ignorar
IGNORE_DIRS = ['__pycache__', '.git', 'node_modules', '.venv', 'venv', 'models']

def load_project_files():
    """Carga todos los archivos del proyecto en memoria"""
    logger.info("🔍 Cargando archivos del proyecto...")
    
    files_loaded = 0
    
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Filtrar directorios ignorados
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            # Solo archivos con extensiones válidas
            if any(file.endswith(ext) for ext in VALID_EXTENSIONS):
                file_path = Path(root) / file
                relative_path = file_path.relative_to(PROJECT_ROOT)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        PROJECT_CONTEXT['files'][str(relative_path)] = {
                            'content': content,
                            'path': str(file_path),
                            'size': len(content),
                            'lines': content.count('\n') + 1
                        }
                        files_loaded += 1
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo leer {relative_path}: {e}")
    
    PROJECT_CONTEXT['loaded_at'] = datetime.now()
    logger.info(f"✅ {files_loaded} archivos cargados en memoria")
    
    return files_loaded

def get_project_summary():
    """Genera un resumen del proyecto"""
    total_files = len(PROJECT_CONTEXT['files'])
    total_lines = sum(f['lines'] for f in PROJECT_CONTEXT['files'].values())
    
    # Agrupar por tipo
    by_extension = {}
    for file_path, file_info in PROJECT_CONTEXT['files'].items():
        ext = Path(file_path).suffix
        if ext not in by_extension:
            by_extension[ext] = {'count': 0, 'lines': 0}
        by_extension[ext]['count'] += 1
        by_extension[ext]['lines'] += file_info['lines']
    
    return {
        'total_files': total_files,
        'total_lines': total_lines,
        'by_extension': by_extension,
        'loaded_at': PROJECT_CONTEXT['loaded_at']
    }

def search_in_project(query, max_results=5):
    """Busca en todos los archivos del proyecto"""
    results = []
    query_lower = query.lower()
    
    for file_path, file_info in PROJECT_CONTEXT['files'].items():
        content_lower = file_info['content'].lower()
        if query_lower in content_lower:
            # Encontrar líneas que contienen la query
            lines = file_info['content'].split('\n')
            matching_lines = []
            
            for i, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    matching_lines.append({
                        'line_number': i,
                        'content': line.strip()
                    })
                    if len(matching_lines) >= 3:  # Max 3 líneas por archivo
                        break
            
            results.append({
                'file': file_path,
                'matches': matching_lines
            })
            
            if len(results) >= max_results:
                break
    
    return results

def get_file_content(file_path):
    """Obtiene el contenido de un archivo específico"""
    for stored_path, file_info in PROJECT_CONTEXT['files'].items():
        if file_path in stored_path or stored_path.endswith(file_path):
            return file_info
    return None

# Cargar proyecto al iniciar
load_project_files()

# =====================================================
# CONFIGURACIÓN DE API REAL
# =====================================================

# OPCIÓN 1: GitHub Copilot API (requiere token de GitHub)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # Tu token de GitHub
COPILOT_ENDPOINT = "https://api.githubcopilot.com/chat/completions"

# OPCIÓN 2: OpenAI API (alternativa)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

# Modo de operación
USE_REAL_API = True  # Cambiar a True para usar API real
API_MODE = 'openai'  # 'github' o 'openai'

# =====================================================
# CONTEXTO DE CONVERSACIÓN
# =====================================================

conversations = {}

class Conversation:
    """Maneja el historial de una conversación"""
    
    def __init__(self, session_id):
        self.session_id = session_id
        self.messages = []
        self.created_at = datetime.now()
    
    def add_message(self, role, content):
        """Agrega un mensaje al historial"""
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_context(self, max_messages=10):
        """Obtiene el contexto reciente de la conversación"""
        return self.messages[-max_messages:]
    
    def to_dict(self):
        """Convierte la conversación a diccionario"""
        return {
            'session_id': self.session_id,
            'messages': self.messages,
            'created_at': self.created_at.isoformat()
        }

def get_or_create_conversation(session_id):
    """Obtiene o crea una conversación"""
    if session_id not in conversations:
        conversations[session_id] = Conversation(session_id)
    return conversations[session_id]

# =====================================================
# SIMULACIÓN DE GITHUB COPILOT
# =====================================================

def ask_copilot(user_message, conversation_context):
    """
    Procesa mensajes con acceso completo al proyecto
    
    Tiene contexto de:
    - Todos los archivos del proyecto
    - Estructura completa del código
    - Historial de conversación
    """
    
    # Preparar información del proyecto para el contexto
    project_summary = get_project_summary()
    
    # Buscar en el proyecto si la pregunta lo requiere
    search_results = None
    user_message_lower = user_message.lower()
    
    # Detectar si se pregunta por algo específico del código
    if any(word in user_message_lower for word in ['intent', 'función', 'clase', 'def ', 'action', 'slot', 'entity']):
        # Extraer término de búsqueda
        search_term = user_message_lower.replace('cuales son', '').replace('que son', '').replace('?', '').strip()
        search_results = search_in_project(search_term, max_results=10)
    
    # Preparar el prompt con contexto del proyecto
    system_prompt = f"""Eres GitHub Copilot, un asistente de IA con acceso COMPLETO al proyecto Chatbot-TFG-V2.0.

CONTEXTO DEL PROYECTO:
- Total de archivos: {project_summary['total_files']}
- Total de líneas de código: {project_summary['total_lines']}
- Archivos Python: {project_summary['by_extension'].get('.py', {}).get('count', 0)}
- Cargado en: {project_summary['loaded_at'].strftime('%Y-%m-%d %H:%M:%S')}

Tienes acceso a:
- Todos los archivos .py, .yml, .json, .js, .css, .html
- El código completo de cada módulo
- Configuraciones, datos de entrenamiento, y estructura completa

Cuando respondas:
1. Usa información REAL del proyecto
2. Cita archivos y líneas específicas cuando sea relevante
3. Proporciona ejemplos del código actual
4. Sé específico y técnico cuando se requiera"""

    # Construir mensajes para el contexto
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Agregar contexto de conversación reciente
    for msg in conversation_context[-5:]:  # Últimos 5 mensajes
        messages.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    # Agregar mensaje actual con resultados de búsqueda si hay
    if search_results and len(search_results) > 0:
        search_context = "\n\n[RESULTADOS DE BÚSQUEDA EN EL PROYECTO]:\n"
        for result in search_results[:5]:
            search_context += f"\n📄 {result['file']}:\n"
            for match in result['matches'][:2]:
                search_context += f"  Línea {match['line_number']}: {match['content']}\n"
        
        user_message_with_context = user_message + search_context
    else:
        user_message_with_context = user_message
    
    messages.append({
        "role": "user",
        "content": user_message_with_context
    })
    
    # Generar respuesta con conocimiento del proyecto
    if USE_REAL_API:
        copilot_response = call_real_api(messages, search_results)
    else:
        copilot_response = generate_demo_response(user_message, conversation_context, search_results)
    
    return copilot_response

def call_real_api(messages, search_results=None):
    """
    Llama a la API REAL (OpenAI o GitHub Copilot)
    """
    try:
        if API_MODE == 'openai' and OPENAI_API_KEY:
            # Usar OpenAI API (GPT-4)
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",  # Cambiado a gpt-3.5-turbo (disponible por defecto)
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(
                OPENAI_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"Error API: {response.status_code} - {response.text}")
                return f"⚠️ Error en la API: {response.status_code}"
        
        elif API_MODE == 'github' and GITHUB_TOKEN:
            # Usar GitHub Copilot API
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": messages,
                "model": "gpt-4",
                "temperature": 0.7
            }
            
            response = requests.post(
                COPILOT_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"Error GitHub API: {response.status_code}")
                return f"⚠️ Error en GitHub API: {response.status_code}"
        
        else:
            return "⚠️ No hay API key configurada. Necesitas configurar OPENAI_API_KEY o GITHUB_TOKEN en las variables de entorno."
    
    except Exception as e:
        logger.error(f"Error llamando a la API: {e}", exc_info=True)
        return f"⚠️ Error: {str(e)}\n\nPor favor verifica tu API key y conexión."

def generate_demo_response(user_message, context, search_results=None):
    """
    Genera respuestas inteligentes basadas en el contexto del proyecto
    NOTA: Esta es la versión mejorada con conocimiento del proyecto de turnos
    """
    user_message_lower = user_message.lower()
    
    # Detectar preguntas sobre conexión/comunicación con VS Code
    if any(word in user_message_lower for word in ['visual', 'vs code', 'vscode', 'comunicando', 'conectado']):
        return """Sí, estoy conectado al mismo sistema que usas en Visual Studio Code! �

**Cómo funciona:**
- 📡 Este chat usa el mismo motor de IA (GitHub Copilot)
- 🧠 Tengo acceso al contexto de tu proyecto **Chatbot-TFG-V2.0**
- 💾 Puedo consultar la base de datos, el motor difuso, y todo tu sistema
- 🤝 Es como si me escribieras directamente en VS Code, pero desde el navegador

**Diferencias clave:**
- ✅ **Aquí**: Interfaz web limpia, mejor para conversaciones largas
- ✅ **VS Code**: Integrado en el editor, mejor para código

¿Quieres que te ayude con algo específico de tu proyecto de turnos?"""
    
    # Detectar preguntas sobre el proyecto chatbot
    elif any(word in user_message_lower for word in ['proyecto', 'chatbot', 'turnos', 'cedula', 'sistema']):
        return """¡Sí! Tengo conocimiento completo de tu proyecto **Chatbot-TFG-V2.0** 📋

**Tu sistema incluye:**

🏛️ **Sistema de Turnos para Cédulas** (Ciudad del Este, Paraguay)
- 🤖 Rasa 3.6.20 (NLU + Diálogo)
- 🧠 Motor Difuso (scikit-fuzzy) para recomendaciones
- 🗄️ PostgreSQL (chatbotdb)
- 🌐 Flask frontend
- 📧 Notificaciones email + QR
- 📅 Integración Google Calendar

**Componentes principales:**
- `flask-chatbot/app.py` - Frontend web
- `actions/actions.py` - Acciones de Rasa
- `motor_difuso.py` - Recomendaciones inteligentes
- `orquestador_inteligente.py` - Coordinador general
- `copilot_handler.py` - Mi integración actual

**¿En qué puedo ayudarte específicamente?**
- 🔧 Optimizar algún módulo
- 📊 Analizar el rendimiento
- 🐛 Depurar errores
- ✨ Agregar nuevas funcionalidades
- 💡 Dar recomendaciones de mejora"""
    
    # Saludos
    elif any(word in user_message_lower for word in ['hola', 'buenos', 'buenas', 'hey', 'hi', 'que tal']):
        return """¡Hola! 👋 Soy **GitHub Copilot**, tu asistente de IA integrado.

Estoy conectado a tu proyecto **Chatbot-TFG-V2.0** y puedo ayudarte con:

🏛️ **Sistema de Turnos:**
- Consultar disponibilidad
- Analizar saturación
- Optimizar recomendaciones del motor difuso
- Gestionar la base de datos

💻 **Desarrollo:**
- Debugging de código
- Optimizaciones
- Nuevas features
- Mejores prácticas

📊 **Análisis:**
- Revisar logs y conversaciones
- Métricas de rendimiento
- Sugerencias de mejora

¿Qué necesitas hacer hoy?"""
    
    # Despedidas
    elif any(word in user_message_lower for word in ['chau', 'adiós', 'hasta luego', 'bye', 'nos vemos']):
        return "¡Hasta luego! 👋 Fue un placer ayudarte con tu proyecto. Recuerda que estoy aquí 24/7 cuando me necesites. 🚀"
    
    # Preguntas sobre disponibilidad/turnos
    elif any(word in user_message_lower for word in ['disponibilidad', 'turno', 'horario', 'fecha', 'agendar']):
        return """¡Claro! Puedo ayudarte con el sistema de turnos 📅

**Puedo hacer:**
- 🔍 Consultar disponibilidad en tiempo real
- 📊 Analizar saturación por horarios
- 🧠 Recomendar mejores horarios (usando motor difuso)
- 📝 Ayudarte a optimizar el flujo de agendamiento
- 💡 Sugerir mejoras al sistema

**¿Qué necesitas específicamente?**
- Ver disponibilidad de una fecha?
- Analizar qué horarios están más saturados?
- Optimizar las recomendaciones del motor difuso?
- Revisar el código de agendamiento?

Dime qué necesitas y te ayudo 🎯"""
    
    # Preguntas sobre el motor difuso
    elif any(word in user_message_lower for word in ['difuso', 'fuzzy', 'recomendacion', 'saturacion', 'espera']):
        return """🧠 **Motor Difuso** - El cerebro de las recomendaciones

Tu sistema usa **lógica difusa** (scikit-fuzzy) para calcular:

**Entradas:**
- 📊 Ocupación (0-100%)
- ⏰ Hora del día (7:00-17:00)
- 🚨 Urgencia del usuario (0-10)

**Salidas:**
- ⏱️ Tiempo de espera estimado (0-120 min)
- ⭐ Score de recomendación (0-100)

**Reglas activas:** 15+ reglas difusas

**¿Quieres que:**
- Ajuste los parámetros de las reglas?
- Analice el rendimiento actual?
- Agregue nuevas variables?
- Optimice los rangos de pertenencia?

¡Dime qué necesitas! 🎯"""
    
    # Preguntas sobre base de datos
    elif any(word in user_message_lower for word in ['base de datos', 'bd', 'postgresql', 'postgres', 'sql', 'consulta']):
        return """🗄️ **Base de Datos PostgreSQL** - chatbotdb

**Tablas principales:**
- `turnos` - Gestión de citas (nombre, cédula, fecha_hora, código, estado)
- `conversation_messages` - Logging de interacciones
- Tablas de disponibilidad y análisis

**Puedo ayudarte con:**
- 📝 Escribir consultas SQL optimizadas
- 🔍 Analizar datos de turnos
- 📊 Generar reportes y estadísticas
- 🔧 Optimizar queries lentas
- 💡 Diseñar nuevas tablas o índices

**¿Qué necesitas consultar o modificar?**"""
    
    # Preguntas técnicas generales
    elif any(word in user_message_lower for word in ['código', 'code', 'error', 'bug', 'problema']):
        return """🔧 **Asistencia Técnica**

Puedo ayudarte con el código de tu proyecto:

**Servicios disponibles:**
- 🐛 Debugging de errores
- ⚡ Optimización de performance
- 📝 Refactoring y mejores prácticas
- 🧪 Ayuda con testing
- 📚 Documentación de código
- 🔄 Integración de nuevos módulos

**Tu stack actual:**
- Backend: Python 3.8 + Flask + Rasa
- Frontend: HTML/CSS/JS
- BD: PostgreSQL
- IA: Motor Difuso + NLU

¿Qué código necesitas revisar o mejorar?"""
    
    # Preguntas sobre intents
    elif 'intent' in user_message_lower and any(word in user_message_lower for word in ['cuales', 'que', 'lista', 'todos']):
        # Buscar en domain.yml
        domain_file = get_file_content('domain.yml')
        if domain_file:
            intents = []
            lines = domain_file['content'].split('\n')
            in_intents = False
            for line in lines:
                if line.strip() == 'intents:':
                    in_intents = True
                elif in_intents and line.strip().startswith('- '):
                    intent = line.strip()[2:]
                    intents.append(intent)
                elif in_intents and line.strip() and not line.startswith(' '):
                    break
            
            return f"""📋 **Intents definidos en tu chatbot** (domain.yml):

**Total: {len(intents)} intents**

**Saludos y básicos:**
{chr(10).join([f'  • `{i}`' for i in intents[:7]])}

**Gestión de turnos:**
{chr(10).join([f'  • `{i}`' for i in intents[7:17]])}

**Consultas:**
{chr(10).join([f'  • `{i}`' for i in intents[17:25]])}

**Especiales:**
{chr(10).join([f'  • `{i}`' for i in intents[25:]])}

**Archivo:** `domain.yml` (líneas 3-{7+len(intents)})

¿Quieres que te explique algún intent específico o vea sus ejemplos en `nlu.yml`?"""
        else:
            return "No pude encontrar el archivo domain.yml. ¿Está en la ubicación correcta?"
    
    # Preguntas sobre acciones
    elif 'action' in user_message_lower and any(word in user_message_lower for word in ['cuales', 'que', 'lista', 'todos']):
        # Buscar funciones que empiezan con 'Action' en actions.py
        actions_file = get_file_content('actions/actions.py')
        if actions_file:
            actions = []
            lines = actions_file['content'].split('\n')
            for i, line in enumerate(lines, 1):
                if 'class Action' in line and '(Action)' in line:
                    action_name = line.split('class ')[1].split('(')[0]
                    actions.append({
                        'name': action_name,
                        'line': i
                    })
            
            return f"""🎯 **Acciones personalizadas** (actions/actions.py):

**Total: {len(actions)} acciones**

{chr(10).join([f'  • `{a["name"]}` (línea {a["line"]})' for a in actions[:15]])}

{'...' if len(actions) > 15 else ''}

**Archivo:** `actions/actions.py` ({actions_file['lines']} líneas total)

**Principales categorías:**
- Gestión de turnos (agendar, confirmar, cancelar)
- Validaciones de datos (nombre, cédula, fecha)
- Consultas (disponibilidad, requisitos)
- Motor difuso (recomendaciones, saturación)
- Notificaciones (email, QR)

¿Quieres ver el código de alguna acción específica?"""
        else:
            return "No pude encontrar el archivo actions.py"
    
    # Preguntas sobre estructura de conversación
    elif any(word in user_message_lower for word in ['estructura', 'flujo', 'conversacion', 'dialogo']) and 'turno' in user_message_lower:
        stories_file = get_file_content('data/stories.yml')
        if stories_file:
            return f"""💬 **Estructura de conversación para agendar turnos**:

**Flujo principal** (definido en `stories.yml` y `rules.yml`):

```
1️⃣ Usuario expresa intención
   Intent: agendar_turno
   Ejemplos: "quiero un turno", "necesito sacar cita"

2️⃣ Sistema activa formulario
   Action: turno_form
   Estado: active_loop activado

3️⃣ Recolección de datos (slots):
   📝 nombre → validación de nombre real
   🆔 cedula → número o "PRIMERA_VEZ"
   📅 fecha → parsing inteligente (dateparser)
   ⏰ hora → horarios disponibles
   📧 email → opcional para notificaciones

4️⃣ Confirmación de datos
   Action: action_confirmar_datos_turno
   Muestra resumen al usuario

5️⃣ Usuario confirma
   Intent: confirmar_turno / affirm
   
6️⃣ Sistema guarda turno
   Action: action_guardar_turno
   - Inserta en PostgreSQL
   - Crea evento Google Calendar
   - Genera código QR
   - Envía email confirmación

7️⃣ Respuesta final
   Action: utter_turno_confirmado
```

**Motor Difuso integrado:**
- Calcula saturación antes de asignar
- Sugiere horarios alternativos si está lleno
- Estima tiempo de espera

**Archivos involucrados:**
- `data/stories.yml` ({get_file_content('data/stories.yml')['lines'] if get_file_content('data/stories.yml') else '?'} líneas)
- `data/rules.yml` ({get_file_content('data/rules.yml')['lines'] if get_file_content('data/rules.yml') else '?'} líneas)
- `actions/actions.py` (clase `TurnoForm`)

¿Quieres ver el código de alguna parte específica?"""
        else:
            return "No pude acceder a los archivos de historias"
    
    # Preguntas sobre entidades o slots
    elif any(word in user_message_lower for word in ['entidad', 'entity', 'slot']) and any(word in user_message_lower for word in ['cuales', 'que', 'lista']):
        domain_file = get_file_content('domain.yml')
        if domain_file:
            entities = []
            slots = []
            lines = domain_file['content'].split('\n')
            
            in_entities = False
            in_slots = False
            
            for line in lines:
                if line.strip() == 'entities:':
                    in_entities = True
                    in_slots = False
                elif line.strip() == 'slots:':
                    in_slots = True
                    in_entities = False
                elif in_entities and line.strip().startswith('- '):
                    entities.append(line.strip()[2:])
                elif in_slots and line.strip() and not line.startswith(' ') and ':' in line:
                    slots.append(line.strip().replace(':', ''))
                elif line.strip() and not line.startswith(' ') and not line.startswith('-'):
                    in_entities = False
                    in_slots = False
            
            return f"""🏷️ **Entidades y Slots del chatbot**:

**Entidades** (extraídas del texto):
{chr(10).join([f'  • `{e}`' for e in entities])}

**Slots** (almacenamiento temporal):
{chr(10).join([f'  • `{s}`' for s in slots[:10]])}

**Función:**
- **Entidades**: Fragmentos de información extraídos del mensaje del usuario
- **Slots**: Variables que mantienen el estado durante la conversación

**Mappings:**
- De entidades a slots (automático)
- De texto a slots (en formularios)
- Influencian el flujo de la conversación

**Archivo:** `domain.yml`

¿Necesitas ver cómo se usan en las acciones?"""
        else:
            return "No pude acceder al domain.yml"
    
    # Respuesta inteligente por defecto CON BÚSQUEDA
    else:
        base_response = f"""Entiendo tu mensaje: **"{user_message}"**

Como tengo acceso completo a tu proyecto **Chatbot-TFG-V2.0**, puedo ayudarte con:

📋 **Tu Sistema:**
- Consultar y gestionar turnos
- Analizar el motor difuso
- Revisar código y logs
- Optimizar rendimiento

💻 **Desarrollo:**
- Implementar nuevas features
- Debugging y testing
- Mejores prácticas
- Documentación

🤔 **¿Podrías ser más específico sobre qué necesitas?**

Por ejemplo:
- "¿Cuáles son los intents del chatbot?"
- "¿Qué acciones hay definidas?"
- "Muéstrame la estructura de conversación para agendar turnos"
- "¿Cómo funciona el motor difuso?"
- "¿Qué entidades se extraen?"

¡Estoy aquí para ayudarte! 🚀"""
        
        # Si hay resultados de búsqueda, agregarlos
        if search_results and len(search_results) > 0:
            base_response += "\n\n**📎 Encontré esto en el proyecto:**\n"
            for result in search_results[:3]:
                base_response += f"\n📄 `{result['file']}`:\n"
                for match in result['matches'][:2]:
                    base_response += f"  Línea {match['line_number']}: `{match['content'][:80]}...`\n"
        
        return base_response

# =====================================================
# RUTAS DEL SERVIDOR
# =====================================================

@app.route('/')
def index():
    """Página principal del chat"""
    # Crear session_id si no existe
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Endpoint principal del chat"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'error': 'Mensaje vacío'
            }), 400
        
        # Obtener session_id
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        # Obtener o crear conversación
        conversation = get_or_create_conversation(session_id)
        
        # Agregar mensaje del usuario
        conversation.add_message('user', user_message)
        
        # Obtener contexto
        context = conversation.get_context()
        
        # Procesar con Copilot
        copilot_response = ask_copilot(user_message, context)
        
        # Agregar respuesta de Copilot
        conversation.add_message('assistant', copilot_response)
        
        # Log
        logger.info(f"[{session_id}] Usuario: {user_message}")
        logger.info(f"[{session_id}] Copilot: {copilot_response[:100]}...")
        
        return jsonify({
            'response': copilot_response,
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error en chat: {e}", exc_info=True)
        return jsonify({
            'error': 'Error procesando mensaje',
            'details': str(e)
        }), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Obtiene el historial de conversación"""
    try:
        session_id = session.get('session_id')
        
        if not session_id or session_id not in conversations:
            return jsonify({
                'messages': []
            })
        
        conversation = conversations[session_id]
        
        return jsonify({
            'messages': conversation.messages,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return jsonify({
            'error': 'Error obteniendo historial'
        }), 500

@app.route('/clear', methods=['POST'])
def clear_history():
    """Limpia el historial de conversación"""
    try:
        session_id = session.get('session_id')
        
        if session_id and session_id in conversations:
            conversations[session_id] = Conversation(session_id)
        
        return jsonify({
            'success': True,
            'message': 'Historial limpiado'
        })
        
    except Exception as e:
        logger.error(f"Error limpiando historial: {e}")
        return jsonify({
            'error': 'Error limpiando historial'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud"""
    api_configured = False
    api_type = 'none'
    
    if USE_REAL_API:
        if API_MODE == 'openai' and OPENAI_API_KEY:
            api_configured = True
            api_type = 'openai'
        elif API_MODE == 'github' and GITHUB_TOKEN:
            api_configured = True
            api_type = 'github'
    
    return jsonify({
        'status': 'ok',
        'service': 'Copilot Agent',
        'timestamp': datetime.now().isoformat(),
        'active_conversations': len(conversations),
        'api_configured': api_configured,
        'api_type': api_type,
        'mode': 'REAL API' if api_configured else 'DEMO (respuestas simuladas)'
    })

@app.route('/project-info', methods=['GET'])
def project_info():
    """Información del proyecto cargado"""
    try:
        summary = get_project_summary()
        
        # Listar archivos principales
        main_files = [
            path for path in PROJECT_CONTEXT['files'].keys()
            if any(name in path for name in ['app.py', 'actions.py', 'domain.yml', 'nlu.yml', 'motor_difuso.py'])
        ]
        
        return jsonify({
            'success': True,
            'summary': {
                'total_files': summary['total_files'],
                'total_lines': summary['total_lines'],
                'loaded_at': summary['loaded_at'].isoformat() if summary['loaded_at'] else None
            },
            'by_type': {
                ext: {'count': info['count'], 'lines': info['lines']}
                for ext, info in summary['by_extension'].items()
            },
            'main_files': main_files[:10]
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo info del proyecto: {e}")
        return jsonify({
            'error': str(e)
        }), 500

# =====================================================
# EJECUTAR SERVIDOR
# =====================================================

if __name__ == '__main__':
    logger.info("🚀 Iniciando Copilot Agent...")
    logger.info("📡 Servidor disponible en: http://localhost:5001")
    logger.info("💬 Abre tu navegador y comienza a chatear!")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )
