import streamlit as st
import requests
import time
import json
import logging
import psycopg2
from datetime import datetime
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ IMPORTAR EL CLASIFICADOR LLM Y FALLBACK
try:
    from llm_classifier import LLMIntentClassifier
    from llm_fallback_handler import manejar_fallback_inteligente
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️ llm_classifier no disponible, usando solo Rasa")
    def manejar_fallback_inteligente(msg):
        return "No entendí bien tu consulta. ¿Podrías reformularla?"

# =====================================================
# CONFIGURACIÓN
# =====================================================
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
RASA_STATUS_URL = "http://localhost:5005/status"

# Configuración de base de datos
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

st.set_page_config(
    page_title="Turnos Cédulas - Ciudad del Este",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ✅ INICIALIZAR CLASIFICADOR LLM
if LLM_AVAILABLE:
    try:
        llm_classifier = LLMIntentClassifier()
        if llm_classifier.available:
            st.success("🤖 Clasificador LLM activo", icon="✅")
        else:
            llm_classifier = None
    except:
        llm_classifier = None
else:
    llm_classifier = None

# =====================================================
# CSS MODERNO CON BURBUJAS Y CENTRADO
# =====================================================
def inject_modern_css():
    st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit */
    .stDeployButton {display: none;}
    .stDecoration {display: none;}
    header[data-testid="stHeader"] {display: none;}
    
    /* Fondo general */
    .stApp {
        background: #f5f7fa;
    }
    
    /* Contenedor principal */
    .main .block-container {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 30px;
        background: white;
        margin: 20px auto;
        max-width: 1100px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Contenedor del chat con altura fija y scroll */
    .chat-messages-container {
        max-height: 500px;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 10px;
        margin-bottom: 20px;
        background: transparent;
    }
    
    /* Scroll personalizado */
    .chat-messages-container::-webkit-scrollbar {
        width: 8px;
    }
    
    .chat-messages-container::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 10px;
    }
    
    .chat-messages-container::-webkit-scrollbar-thumb {
        background: #cbd5e0;
        border-radius: 10px;
    }
    
    .chat-messages-container::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* Animaciones */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Estilos de burbujas de chat */
    .message-wrapper {
        display: flex;
        margin-bottom: 20px;
        animation: slideIn 0.3s ease-out;
        align-items: flex-start;
    }
    
    /* Burbuja del BOT (izquierda, azul claro) */
    .message-wrapper.bot {
        justify-content: flex-start;
    }
    
    .message-bubble.bot {
        background: #e0e7ff;
        color: #1e293b;
        border-radius: 18px 18px 18px 4px;
        padding: 14px 18px;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.12);
        word-wrap: break-word;
    }
    
    /* Burbuja del USUARIO (derecha, rosa claro) */
    .message-wrapper.user {
        justify-content: flex-end;
    }
    
    .message-bubble.user {
        background: #fce7f3;
        color: #1e293b;
        border-radius: 18px 18px 4px 18px;
        padding: 14px 18px;
        max-width: 70%;
        box-shadow: 0 2px 8px rgba(236, 72, 153, 0.12);
        word-wrap: break-word;
    }
    
    /* Avatar */
    .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        margin: 0 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    
    .message-avatar.bot {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        order: -1;
    }
    
    .message-avatar.user {
        background: linear-gradient(135deg, #ec4899 0%, #f472b6 100%);
        order: 1;
    }
    
    /* Contenido del mensaje */
    .message-content {
        flex: 1;
        max-width: 75%;
    }
    
    /* Timestamp */
    .message-time {
        font-size: 0.7rem;
        color: #94a3b8;
        margin-top: 4px;
    }
    
    .message-wrapper.user .message-time {
        text-align: right;
    }
    
    /* Título principal */
    .main-title {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 2rem;
        font-weight: 600;
        color: #1a365d;
        text-align: center;
        margin: 0 0 8px 0;
    }
    
    .main-subtitle {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.95rem;
        color: #4a5568;
        text-align: center;
        margin: 0 0 20px 0;
        font-weight: 300;
    }
    
    /* Botones de acción rápida */
    .quick-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 15px 0 20px 0;
    }
    
    /* Botones compactos */
    .stButton > button {
        padding: 8px 16px !important;
        font-size: 0.85rem !important;
        border-radius: 18px !important;
        transition: all 0.2s !important;
        background: white !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e0 !important;
        font-weight: 500 !important;
        height: 36px !important;
        min-width: auto !important;
    }
    
    .stButton > button:hover {
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06) !important;
    }
    
    /* Input del chat */
    .stTextInput > div > div > input {
        border-radius: 24px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 12px 20px !important;
        font-size: 0.95rem !important;
        transition: all 0.2s !important;
        background: white !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }
    
    /* Campo de comentario con fondo claro */
    .comment-container {
        background: #f8f9fa !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 12px !important;
        margin-top: 10px !important;
    }
    
    .comment-container textarea {
        background: white !important;
        border: 1px solid #cbd5e0 !important;
        border-radius: 8px !important;
    }
    
    /* Badges */
    .llm-badge {
        font-size: 0.65rem;
        background: #10b981;
        color: white;
        padding: 2px 6px;
        border-radius: 8px;
        margin-left: 6px;
        font-weight: 600;
    }
    
    /* Responsivo */
    @media (max-width: 768px) {
        .message-bubble {
            max-width: 85%;
        }
        
        .main .block-container {
            padding: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)# =====================================================
# FUNCIONES DE BASE DE DATOS
# =====================================================
def get_db_connection():
    try:
        return psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
    except Exception as e:
        return None

def save_feedback_simple(session_id: str, user_message: str, bot_response: str, 
                         feedback_thumbs: int, feedback_comment: str = None):
    """✅ Guarda feedback DIRECTAMENTE en la BD sin buscar"""
    conn = get_db_connection()
    if not conn:
        print("❌ No se pudo conectar a la BD")
        return False
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversation_messages 
            (session_id, user_message, bot_response, 
             feedback_thumbs, feedback_comment, needs_review, 
             timestamp, intent_detected, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s)
            RETURNING id
        """, (
            session_id,
            user_message,
            bot_response,
            feedback_thumbs,
            feedback_comment,
            True if feedback_thumbs == -1 else False,
            'feedback_manual',
            1.0
        ))
        
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Feedback guardado con ID: {new_id}")
        print(f"   Feedback: {'👍' if feedback_thumbs == 1 else '👎'}")
        if feedback_comment:
            print(f"   Comentario: {feedback_comment}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error guardando feedback: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False

# =====================================================
# FUNCIONES DE RASA CON LLM
# =====================================================
def send_message_to_rasa(message: str, sender: str = "user") -> List[Dict]:
    """Envía mensaje a Rasa, opcionalmente pre-procesado con LLM"""
    try:
        # ✅ PRE-PROCESAR CON LLM SI ESTÁ DISPONIBLE
        intent_detected = None
        confidence = 0.0
        
        if llm_classifier:
            intent_detected, confidence = llm_classifier.classify_intent(message)
            
            # Si el LLM tiene alta confianza, agregar metadata
            if confidence > 0.80:
                st.session_state[f"llm_intent_{len(st.session_state.messages)}"] = {
                    "intent": intent_detected,
                    "confidence": confidence
                }
        
        payload = {
            "sender": sender,
            "message": message,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "session_id": st.session_state.get("session_id", "default"),
                "llm_intent": intent_detected if confidence > 0.80 else None,
                "llm_confidence": float(confidence) if confidence > 0.80 else None
            }
        }
        
        response = requests.post(
            RASA_URL,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if not response_data:
                return [{"text": "El sistema está procesando tu solicitud. Intenta de nuevo."}]
            return response_data
        else:
            return [{"text": "Servicio temporalmente no disponible. Intenta en unos minutos."}]
            
    except requests.exceptions.Timeout:
        return [{"text": "El sistema está ocupado. Intenta de nuevo en unos segundos."}]
    except requests.exceptions.ConnectionError:
        return [{"text": "Servicio no disponible. Contacta al soporte técnico."}]
    except Exception as e:
        return [{"text": "Error temporal del sistema. Intenta nuevamente."}]

# =====================================================
# INICIALIZACIÓN
# =====================================================
def initialize_session():
    """Inicializa la sesión SIEMPRE limpia"""
    
    # ✅ Verificar si es la primera ejecución de esta carga de página
    if "initialized" not in st.session_state:
        # Limpiar TODO el session_state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Marcar como inicializado
        st.session_state.initialized = True
        
        logger.info("🔄 Nueva sesión iniciada - Estado limpio")
    
    # Inicializar mensajes si no existen
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "¡Hola! Soy tu asistente virtual para gestión de cédulas de identidad en Ciudad del Este. ¿En qué puedo ayudarte hoy?",
                "timestamp": datetime.now().isoformat(),
                "feedback_given": True,
                "show_quick_actions": True
            }
        ]
    
    # Inicializar session_id si no existe
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"public_session_{int(time.time())}"
    
    # Inicializar waiting_response
    if "waiting_response" not in st.session_state:
        st.session_state.waiting_response = False

def add_message(role: str, content: str, feedback_enabled: bool = True):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "feedback_given": False if role == "assistant" and feedback_enabled else True,
        "show_quick_actions": False
    })

# =====================================================
# COMPONENTES DE UI
# =====================================================
def render_message_bubble(message: Dict, index: int):
    """Renderiza un mensaje con burbuja estilo moderno"""
    role = message["role"]
    content = message["content"]
    timestamp = datetime.fromisoformat(message["timestamp"]).strftime("%H:%M")
    
    bubble_class = "bot" if role == "assistant" else "user"
    avatar_emoji = "🤖" if role == "assistant" else "👤"
    
    # ✅ Verificar si fue mejorado por LLM
    llm_info = st.session_state.get(f"llm_intent_{index}", None)
    llm_badge = ""
    if llm_info and role == "user":
        llm_badge = f'<span class="llm-badge">🧠 LLM: {llm_info["intent"][:15]}</span>'
    
    # HTML de la burbuja
    st.markdown(f"""
    <div class="message-wrapper {bubble_class}">
        <div class="message-avatar {bubble_class}">{avatar_emoji}</div>
        <div class="message-content">
            <div class="message-bubble {bubble_class}">
                {content} {llm_badge}
            </div>
            <div class="message-time">{timestamp}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botones de acción rápida solo en primer mensaje
    if message.get("show_quick_actions", False):
        render_quick_actions()
    
    # Feedback para mensajes del bot
    if role == "assistant" and not message.get("feedback_given", False):
        show_feedback_buttons(index)

def render_quick_actions():
    """Renderiza botones de acción rápida"""
    st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
    
    cols = st.columns(6)
    
    quick_actions = [
        ("📅 Agendar", "Quiero agendar un turno"),
        ("📋 Requisitos", "Qué requisitos necesito"),
        ("⏰ Horarios", "Cuáles son los horarios"),
        ("📍 Ubicación", "Dónde queda la oficina"),
        ("💰 Costo", "Cuánto cuesta"),
        ("⏱️ Espera", "Cuánto voy a esperar")
    ]
    
    for i, (label, message) in enumerate(quick_actions):
        with cols[i]:
            if st.button(label, key=f"qa_{i}", use_container_width=True):
                process_quick_message(message)
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_feedback_buttons(message_index: int):
    """Muestra botones de feedback compactos"""
    message = st.session_state.messages[message_index]
    
    if message["role"] != "assistant" or message.get("feedback_given", False):
        return
    
    col1, col2, col3 = st.columns([1, 1, 8])
    
    with col1:
        if st.button("👍", key=f"pos_{message_index}", help="Útil"):
            handle_feedback(message_index, "positive")
            st.rerun()
    
    with col2:
        if st.button("👎", key=f"neg_{message_index}", help="No útil"):
            st.session_state[f"comment_mode_{message_index}"] = True
            st.rerun()
    
    # Cuadro de comentario con fondo claro
    if st.session_state.get(f"comment_mode_{message_index}", False):
        st.markdown('<div class="comment-container">', unsafe_allow_html=True)
        
        comment = st.text_area(
            "💭 ¿Qué podríamos mejorar?",
            key=f"comment_{message_index}",
            placeholder="Escribe tu comentario aquí...",
            height=60
        )
        
        col_send, col_cancel = st.columns(2)
        
        with col_send:
            if st.button("📤 Enviar", key=f"send_{message_index}", type="primary"):
                if comment and comment.strip():
                    handle_feedback(message_index, "negative", comment)
                    st.session_state[f"comment_mode_{message_index}"] = False
                    st.rerun()
        
        with col_cancel:
            if st.button("✖️ Cancelar", key=f"cancel_{message_index}"):
                st.session_state[f"comment_mode_{message_index}"] = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def handle_feedback(message_index: int, feedback_type: str, comment: str = None):
    """✅ Captura mensaje del usuario también"""
    if message_index >= len(st.session_state.messages):
        return
    
    message = st.session_state.messages[message_index]
    if message["role"] != "assistant":
        return
    
    st.session_state.messages[message_index]["feedback_given"] = True
    
    # Buscar el mensaje del usuario que provocó esta respuesta
    user_message = "Mensaje no disponible"
    if message_index > 0:
        prev_message = st.session_state.messages[message_index - 1]
        if prev_message["role"] == "user":
            user_message = prev_message["content"]
    
    feedback_value = 1 if feedback_type == "positive" else -1
    
    # Usar la nueva función simple
    success = save_feedback_simple(
        session_id=st.session_state.session_id,
        user_message=user_message,
        bot_response=message["content"],
        feedback_thumbs=feedback_value,
        feedback_comment=comment
    )
    
    if success:
        if feedback_type == "positive":
            st.toast("¡Gracias por tu valoración!", icon="👍")
        else:
            st.toast("Gracias por tu comentario. Seguimos mejorando.", icon="📝")
    else:
        st.warning("No se pudo guardar el feedback.")

def process_quick_message(message: str):
    """Procesa mensaje de acción rápida"""
    add_message("user", message, feedback_enabled=False)
    
    with st.spinner("Procesando..."):
        bot_responses = send_message_to_rasa(message)
        
        response_content = ""
        if bot_responses:
            for response in bot_responses:
                if "text" in response:
                    response_content += response["text"] + "\n\n"
        else:
            response_content = "No pude procesar tu solicitud. Intenta de nuevo."
        
        response_content = response_content.strip()
        add_message("assistant", response_content)
    
    st.rerun()

# =====================================================
# INTERFAZ PRINCIPAL
# =====================================================
def show_chat_interface():
    """Muestra la interfaz principal del chat"""
    
    inject_modern_css()
    
    # ✅ Header con botón de reinicio
    col_title, col_reset = st.columns([4, 1])
    
    with col_title:
        llm_status = "🧠 LLM Activo" if llm_classifier else ""
        st.markdown(f"""
        <div class="main-title">🏛️ Turnos Cédulas {llm_status}</div>
        <div class="main-subtitle">Ciudad del Este - Sistema Oficial</div>
        """, unsafe_allow_html=True)
    
    with col_reset:
        if st.button("🔄 Reiniciar", help="Iniciar nueva conversación", use_container_width=True):
            # Limpiar todo el estado
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Contenedor del chat con altura fija y scroll
    st.markdown('<div class="chat-messages-container">', unsafe_allow_html=True)
    
    # Mostrar historial con burbujas
    for i, message in enumerate(st.session_state.messages):
        render_message_bubble(message, i)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input del usuario
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([9, 1])
        with col1:
            prompt = st.text_input(
                "chat_input",
                placeholder="Escribe tu consulta aquí...",
                label_visibility="collapsed",
                key="user_input"
            )
        with col2:
            submit = st.form_submit_button("➤", use_container_width=True)
    
    if submit and prompt:
        add_message("user", prompt, feedback_enabled=False)
        st.rerun()
    
    # Procesar respuesta del bot
    if len(st.session_state.messages) > 0:
        last_message = st.session_state.messages[-1]
        
        if last_message["role"] == "user" and not st.session_state.get("waiting_response", False):
            st.session_state.waiting_response = True
            
            with st.spinner("Procesando..."):
                bot_responses = send_message_to_rasa(last_message["content"])
                
                response_content = ""
                if bot_responses:
                    for response in bot_responses:
                        if "text" in response:
                            response_content += response["text"] + "\n\n"
                else:
                    response_content = "No pude procesar tu solicitud. Intenta de nuevo."
                
                response_content = response_content.strip()
                add_message("assistant", response_content)
                
                st.session_state.waiting_response = False
            
            st.rerun()

# =====================================================
# APLICACIÓN PRINCIPAL
# =====================================================
def main():
    """Aplicación principal"""
    initialize_session()
    show_chat_interface()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("Error del sistema. Intenta recargar la página.")
        st.info("Si el problema persiste, contacta al soporte técnico.")