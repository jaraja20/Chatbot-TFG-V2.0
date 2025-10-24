import streamlit as st
import requests
import time
import json
import psycopg2
from datetime import datetime
from typing import List, Dict, Optional

# =====================================================
# ✅ IMPORTAR EL DASHBOARD MEJORADO
# =====================================================
try:
    from learning_dashboard import show_learning_dashboard
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Dashboard no disponible: {e}")
    DASHBOARD_AVAILABLE = False

# =====================================================
# ✅ IMPORTAR EL SISTEMA DE LOGGING MEJORADO
# =====================================================
try:
    from conversation_logger import (
        setup_improved_logging_system, 
        get_improved_conversation_logger,
        set_improved_conversation_logger
    )


    LOGGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Logger mejorado no disponible: {e}")
    LOGGER_AVAILABLE = False

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
    page_title="Sistema de Turnos - Cédulas",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# ✅ INICIALIZAR LOGGER MEJORADO
# =====================================================
if LOGGER_AVAILABLE:
    try:
        database_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
        improved_logger = setup_improved_logging_system(database_url)
        set_improved_conversation_logger(improved_logger)
        print("✅ Logger mejorado inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando logger mejorado: {e}")

# =====================================================
# CSS PERSONALIZADO CON BOTONES COMPACTOS
# =====================================================
def inject_custom_css():
    """Inyecta CSS personalizado para mejorar el scroll del chat y botones compactos"""
    st.markdown("""
    <style>
    /* Estilos para animaciones de mensajes */
    .chat-message {
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Scroll suave */
    html {
        scroll-behavior: smooth;
    }
    
    /* Timestamp styling */
    .timestamp {
        text-align: right;
        font-size: 0.8em;
        opacity: 0.7;
    }
    
    /* ✅ BOTONES DE FEEDBACK COMPACTOS */
    .feedback-buttons {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    
    .feedback-btn {
        display: inline-flex;
        align-items: center;
        padding: 4px 8px;
        border: 1px solid #ddd;
        border-radius: 16px;
        background: white;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;
        text-decoration: none;
        color: #333;
    }
    
    .feedback-btn:hover {
        background: #f0f2f6;
        border-color: #0066cc;
        transform: scale(1.05);
    }
    
    .feedback-btn.selected {
        background: #0066cc;
        color: white;
        border-color: #0066cc;
    }
    
    /* Contenedor de comentarios */
    .comment-container {
        margin-top: 12px;
        padding: 8px;
        background: #f8f9fa;
        border-radius: 8px;
        border-left: 3px solid #ff6b6b;
    }
    
    /* Ocultar botones nativos de Streamlit en feedback */
    .feedback-container button {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

def auto_scroll_to_bottom():
    """Fuerza el scroll hacia abajo usando JavaScript"""
    scroll_script = """
    <script>
    function scrollToBottom() {
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    scrollToBottom();
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 300);
    </script>
    """
    st.markdown(scroll_script, unsafe_allow_html=True)

# =====================================================
# FUNCIONES DE BASE DE DATOS PARA FEEDBACK
# =====================================================

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    try:
        return psycopg2.connect(
            host=DB_CONFIG['host'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
    except Exception as e:
        st.error(f"Error conectando a la BD: {e}")
        return None

def update_feedback_in_db(session_id: str, bot_response: str, feedback_thumbs: int, feedback_comment: str = None):
    """✅ Actualiza feedback usando el sistema mejorado"""
    
    # Intentar con el logger mejorado primero
    if LOGGER_AVAILABLE:
        try:
            logger_instance = get_improved_conversation_logger()
            if logger_instance:
                success = logger_instance.update_feedback(
                    session_id=session_id,
                    bot_response=bot_response,
                    feedback_thumbs=feedback_thumbs,
                    feedback_comment=feedback_comment
                )
                if success:
                    print(f"✅ Feedback actualizado: {'👍' if feedback_thumbs == 1 else '👎'}")
                    if feedback_comment:
                        print(f"   Comentario: {feedback_comment}")
                    return True
        except Exception as e:
            print(f"⚠️ Error con logger mejorado: {e}")
    
    # Fallback: usar psycopg2 directamente con la tabla nueva
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Buscar en conversation_messages (tabla nueva)
        cursor.execute("""
            SELECT id FROM conversation_messages 
            WHERE session_id = %s AND bot_response = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (session_id, bot_response))
        
        result = cursor.fetchone()
        if not result:
            print(f"⚠️ No se encontró mensaje para actualizar feedback")
            cursor.close()
            conn.close()
            return False
        
        log_id = result[0]
        
        # Actualizar feedback
        cursor.execute("""
            UPDATE conversation_messages 
            SET feedback_thumbs = %s, 
                feedback_comment = %s,
                needs_review = CASE WHEN %s = -1 THEN TRUE ELSE needs_review END
            WHERE id = %s
        """, (feedback_thumbs, feedback_comment, feedback_thumbs, log_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Feedback actualizado (fallback): {'👍' if feedback_thumbs == 1 else '👎'}")
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando feedback: {e}")
        st.error(f"Error actualizando feedback: {e}")
        if conn:
            conn.close()
        return False

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

@st.cache_data(ttl=30)
def check_rasa_status() -> Dict[str, bool]:
    """Verifica el estado de Rasa"""
    try:
        response = requests.get(RASA_STATUS_URL, timeout=5)
        return {
            'online': response.status_code == 200,
            'model_loaded': response.json().get('model_file') is not None
        }
    except:
        return {'online': False, 'model_loaded': False}

def send_message_to_rasa(message: str, sender: str = None) -> List[Dict]:
    """Envía mensaje a Rasa y retorna respuestas"""
    try:
        # ✅ Usar el session_id de Streamlit como sender para que coincida
        if sender is None:
            sender = st.session_state.get("session_id", "default")
        
        payload = {
            "sender": sender,  # ✅ Ahora usa el mismo session_id
            "message": message,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "session_id": sender  # ✅ Consistente
            }
        }
        
        response = requests.post(
            RASA_URL,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error del servidor: {response.status_code}")
            return []
    
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout: El servidor tardó demasiado en responder")
        return []
    except requests.exceptions.ConnectionError:
        st.error("🔌 Error de conexión: No se pudo conectar con el servidor Rasa")
        return []
    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return []

def initialize_session():
    """Inicializa variables de sesión"""
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "¡Hola! 👋 Soy tu asistente virtual para la gestión de turnos de cédulas. ¿En qué puedo ayudarte hoy?",
            "timestamp": datetime.now().isoformat(),
            "feedback_given": False
        }]
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"
    
    if "should_scroll" not in st.session_state:
        st.session_state.should_scroll = True

def add_message(role: str, content: str, feedback_enabled: bool = True):
    """Agrega un mensaje al historial de chat"""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "feedback_given": False if role == "assistant" and feedback_enabled else None
    }
    st.session_state.messages.append(message)
    st.session_state.should_scroll = True

def handle_feedback(message_index: int, feedback_type: str, comment: str = None):
    """Maneja el feedback del usuario"""
    message = st.session_state.messages[message_index]
    
    # Marcar como feedback dado
    message["feedback_given"] = True
    message["feedback_type"] = feedback_type
    
    # Guardar en BD
    feedback_thumbs = 1 if feedback_type == "positive" else -1
    session_id = st.session_state.session_id
    bot_response = message["content"]
    
    success = update_feedback_in_db(session_id, bot_response, feedback_thumbs, comment)
    
    if success:
        if feedback_type == "positive":
            st.success("¡Gracias por tu feedback positivo! 👍")
        else:
            st.info("Gracias por tu feedback. Lo usaremos para mejorar. 👎")
    else:
        st.warning("No se pudo guardar el feedback, pero lo hemos registrado localmente.")

def show_feedback_buttons(message_index: int):
    """Muestra botones de feedback compactos"""
    message = st.session_state.messages[message_index]
    
    # Si ya se dio feedback, mostrar estado
    if message.get("feedback_given", False):
        feedback_type = message.get("feedback_type", "")
        if feedback_type == "positive":
            st.success("✅ Marcado como útil")
        elif feedback_type == "negative":
            st.error("❌ Marcado como no útil")
        return
    
    # Mostrar botones de feedback
    col1, col2 = st.columns([1, 5])
    
    with col1:
        if st.button("👍", key=f"thumbs_up_{message_index}", help="Útil"):
            handle_feedback(message_index, "positive")
            st.rerun()
    
    with col2:
        if st.button("👎", key=f"thumbs_down_{message_index}", help="No útil"):
            # Activar modo comentario
            st.session_state[f"comment_mode_{message_index}"] = True
            st.rerun()
    
    # Si está en modo comentario
    if st.session_state.get(f"comment_mode_{message_index}", False):
        st.markdown('<div class="comment-container">', unsafe_allow_html=True)
        st.write("**¿Qué salió mal?**")
        
        comment = st.text_area(
            "¿Qué podríamos mejorar?",
            key=f"comment_{message_index}",
            placeholder="Describe brevemente qué esperabas o qué no funcionó...",
            height=60
        )
        
        col_send, col_cancel = st.columns(2)
        with col_send:
            if st.button("Enviar", key=f"send_{message_index}"):
                handle_feedback(message_index, "negative", comment)
                st.session_state[f"comment_mode_{message_index}"] = False
                st.rerun()
        
        with col_cancel:
            if st.button("Cancelar", key=f"cancel_{message_index}"):
                st.session_state[f"comment_mode_{message_index}"] = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def process_quick_button(user_msg: str):
    """Procesa los botones rápidos de la sidebar"""
    add_message("user", user_msg, feedback_enabled=False)
    
    bot_responses = send_message_to_rasa(user_msg)
    
    if bot_responses:
        for response in bot_responses:
            if "text" in response:
                add_message("assistant", response["text"])
    else:
        add_message("assistant", "No recibí respuesta del servidor.")

def render_sidebar():
    """Renderiza la barra lateral con información útil"""
    with st.sidebar:
        st.title("📋 Panel de Control")
        
        # Estado de Rasa
        status = check_rasa_status()
        if status['online']:
            st.success("🟢 Rasa Conectado")
        else:
            st.error("🔴 Rasa Desconectado")
        
        st.markdown("---")
        
        # Información del sistema
        st.markdown("""
        ### ℹ️ Información
        
        **Horario:** Lunes a Viernes  
        07:00 - 17:00
        
        **Lugar:** Av. Pioneros del Este  
        Ciudad del Este
        
        **Costo:** 25.000 Gs
        """)
        
        st.markdown("---")
        
        # Acciones rápidas con botones más compactos
        st.subheader("🚀 Acciones Rápidas")
        
        # Usar columnas para botones más compactos
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📅 Agendar", help="Agendar turno", use_container_width=True):
                process_quick_button("Quiero agendar un turno")
                st.rerun()
            
            if st.button("📋 Requisitos", help="Ver requisitos", use_container_width=True):
                process_quick_button("Qué requisitos necesito")
                st.rerun()
            
            if st.button("📍 Ubicación", help="Ver ubicación", use_container_width=True):
                process_quick_button("Dónde queda la oficina")
                st.rerun()
        
        with col2:
            if st.button("⏰ Horarios", help="Ver horarios", use_container_width=True):
                process_quick_button("Cuáles son los horarios")
                st.rerun()
            
            if st.button("📊 Saturación", help="Ver ocupación", use_container_width=True):
                process_quick_button("Cuánto es la saturación actualmente")
                st.rerun()
            
            if st.button("⏱️ Espera", help="Tiempo de espera", use_container_width=True):
                process_quick_button("Cuánto voy a esperar")
                st.rerun()
        
        st.markdown("---")
        
        # Estadísticas de la sesión
        st.subheader("📊 Estadísticas")
        total_messages = len(st.session_state.messages)
        user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total_messages)
        with col2:
            st.metric("Tuyos", user_messages)
        
        # Control de sesión
        st.subheader("🔧 Controles")
        
        if st.button("🔄 Reiniciar Chat", help="Borrar historial"):
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Chat reiniciado. ¿En qué puedo ayudarte?",
                "timestamp": datetime.now().isoformat(),
                "feedback_given": False
            }]
            st.session_state.should_scroll = True
            st.rerun()
        
        if st.button("💾 Guardar Chat", help="Descargar historial"):
            chat_history = {
                "session_id": st.session_state.session_id,
                "messages": st.session_state.messages,
                "timestamp": datetime.now().isoformat()
            }
            st.download_button(
                label="📄 Descargar JSON",
                data=json.dumps(chat_history, indent=2, ensure_ascii=False),
                file_name=f"chat_turnos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

def show_chat_interface():
    """Muestra la interfaz principal del chat con sistema de feedback"""
    
    # Inyectar CSS personalizado
    inject_custom_css()
    
    # Header principal
    st.title("🏛️ Sistema de Gestión de Turnos")
    st.subheader("Cédulas de Identidad - Ciudad del Este")
    
    # Contenedor principal del chat
    chat_container = st.container()
    
    with chat_container:
        # Mostrar historial de chat con botones de feedback
        for i, message in enumerate(st.session_state.messages):
            role = message["role"]
            with st.chat_message(role):
                # Contenido del mensaje
                st.markdown(f'<div class="chat-message">{message["content"]}</div>', 
                           unsafe_allow_html=True)
                
                # ✅ MOSTRAR BOTONES DE FEEDBACK PARA RESPUESTAS DEL BOT
                if role == "assistant" and not message.get("feedback_given", False):
                    show_feedback_buttons(i)
                
                # Timestamp
                if "timestamp" in message:
                    timestamp = datetime.fromisoformat(message["timestamp"]).strftime("%H:%M")
                    st.markdown(f'<div class="timestamp">⏰ {timestamp}</div>', 
                               unsafe_allow_html=True)
    
    # Input del usuario (fijo en la parte inferior)
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        # Agregar mensaje del usuario al historial
        add_message("user", prompt, feedback_enabled=False)
        
        # Obtener respuesta del bot
        with st.spinner("El bot está escribiendo..."):
            bot_responses = send_message_to_rasa(prompt)
            
            response_content = ""
            if bot_responses:
                for response in bot_responses:
                    if "text" in response:
                        response_content += response["text"] + "\n\n"
                    elif "image" in response:
                        response_content += f"[Imagen: {response['image']}]\n\n"
                    elif "custom" in response:
                        response_content += f"Respuesta personalizada: {response['custom']}\n\n"
            else:
                response_content = "No recibí respuesta del servidor. Por favor, intenta de nuevo."
            
            # Limpiar contenido y agregarlo al historial
            response_content = response_content.strip()
            add_message("assistant", response_content)
        
        # Rerun para mostrar los nuevos mensajes
        st.rerun()
    
    # Auto-scroll si es necesario
    if st.session_state.get("should_scroll", False):
        auto_scroll_to_bottom()
        st.session_state.should_scroll = False

# =====================================================
# APLICACIÓN PRINCIPAL CON PESTAÑAS
# =====================================================
def main():
    """Función principal de la aplicación con pestañas"""
    initialize_session()
    render_sidebar()

    if DASHBOARD_AVAILABLE:
        page = st.sidebar.radio(
            "Seleccionar página:",
            ["💬 Chat", "📊 Dashboard de Aprendizaje"],
            help="Cambia entre el chat y el panel de análisis"
        )

        if page == "💬 Chat":
            show_chat_interface()
        else:
            show_learning_dashboard()  # viene desde learning_dashboard.py
    else:
        show_chat_interface()
        st.warning("⚠️ Dashboard no disponible. Instala dependencias: `pip install plotly pandas`")

if __name__ == "__main__":
    main()

