import streamlit as st
import requests
import time
import json
import psycopg2
from datetime import datetime
from typing import List, Dict, Optional

# Importar el dashboard de aprendizaje
try:
    from learning_dashboard import show_learning_dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False

# Importar el sistema de logging
try:
    from conversation_logger import setup_learning_system, get_conversation_logger, set_conversation_logger
    LOGGER_AVAILABLE = True
except ImportError:
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
    """Actualiza feedback en la base de datos usando psycopg2"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Buscar el registro más reciente que coincida
        cursor.execute("""
            SELECT id FROM conversation_logs 
            WHERE session_id = %s AND bot_response = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (session_id, bot_response))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        log_id = result[0]
        
        # Actualizar feedback
        update_query = """
            UPDATE conversation_logs 
            SET feedback_thumbs = %s, 
                feedback_comment = %s,
                needs_review = CASE WHEN %s = -1 THEN TRUE ELSE needs_review END
            WHERE id = %s
        """
        
        cursor.execute(update_query, (feedback_thumbs, feedback_comment, feedback_thumbs, log_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
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

def send_message_to_rasa(message: str, sender: str = "user") -> List[Dict]:
    """Envía mensaje a Rasa y retorna respuestas"""
    try:
        payload = {
            "sender": sender,
            "message": message,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "session_id": st.session_state.get("session_id", "default")
            }
        }
        
        response = requests.post(
            RASA_URL,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if not response_data:
                return [{"text": "El bot no respondió. Intenta de nuevo."}]
            return response_data
        else:
            return [{"text": f"Error del servidor: {response.status_code}. Verifica que Rasa esté funcionando."}]
            
    except requests.exceptions.Timeout:
        return [{"text": "El bot tardó demasiado en responder. Verifica la conexión con Rasa."}]
    except requests.exceptions.ConnectionError:
        return [{"text": "No se puede conectar con Rasa. Asegúrate de que esté ejecutándose en el puerto 5005."}]
    except Exception as e:
        return [{"text": f"Error de conexión: {str(e)}"}]

def initialize_session():
    """Inicializa el estado de la sesión con sistema de logging mejorado"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "¡Hola! Soy tu asistente virtual para gestión de cédulas en Ciudad del Este. ¿En qué puedo ayudarte hoy?",
                "timestamp": datetime.now().isoformat(),
                "feedback_given": False
            }
        ]
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"
    
    if "should_scroll" not in st.session_state:
        st.session_state.should_scroll = False
    
    # ✅ SISTEMA DE LOGGING MEJORADO
    try:
        from improved_conversation_logger import (
            setup_improved_logging_system, 
            get_improved_conversation_logger,
            set_improved_conversation_logger
        )
        
        if not get_improved_conversation_logger():
            database_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
            logger_instance = setup_improved_logging_system(database_url)
            set_improved_conversation_logger(logger_instance)
            st.success("✅ Sistema de logging mejorado inicializado", icon="🤖")
            
    except ImportError:
        st.warning("⚠️ Sistema de logging mejorado no disponible")
    except Exception as e:
        st.warning(f"⚠️ Error inicializando sistema mejorado: {e}")
    
    # Fallback al sistema anterior si está disponible
    if LOGGER_AVAILABLE and not get_conversation_logger():
        try:
            database_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
            logger_instance = setup_learning_system(database_url)
            set_conversation_logger(logger_instance)
        except Exception as e:
            st.warning(f"⚠️ Sistema de aprendizaje fallback no disponible: {e}")

def add_message(role: str, content: str, feedback_enabled: bool = True):
    """Agrega mensaje al historial y marca para scroll"""
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "feedback_given": False if role == "assistant" and feedback_enabled else True
    })
    st.session_state.should_scroll = True

def handle_feedback(message_index: int, feedback_type: str, comment: str = None):
    """Maneja el feedback del usuario para un mensaje específico"""
    if message_index >= len(st.session_state.messages):
        return
    
    message = st.session_state.messages[message_index]
    if message["role"] != "assistant":
        return
    
    # Marcar feedback como dado
    st.session_state.messages[message_index]["feedback_given"] = True
    
    # Determinar valor de feedback
    feedback_value = 1 if feedback_type == "positive" else -1
    
    # Actualizar en base de datos
    success = update_feedback_in_db(
        session_id=st.session_state.session_id,
        bot_response=message["content"],
        feedback_thumbs=feedback_value,
        feedback_comment=comment
    )
    
    if success:
        if feedback_type == "positive":
            st.toast("¡Gracias por el 👍!", icon="😊")
        else:
            st.toast("Comentario guardado, seguimos.", icon="📝")
    else:
        st.toast("Error guardando feedback", icon="❌")

def show_feedback_buttons(message_index: int):
    """Muestra botones de feedback compactos para un mensaje"""
    message = st.session_state.messages[message_index]
    
    if message["role"] != "assistant" or message.get("feedback_given", False):
        return
    
    col1, col2, col3 = st.columns([1, 1, 8])
    
    with col1:
        if st.button("👍", key=f"pos_{message_index}", help="Respuesta útil"):
            handle_feedback(message_index, "positive")
            st.rerun()
    
    with col2:
        if st.button("👎", key=f"neg_{message_index}", help="Respuesta no útil"):
            # Activar modo de comentario
            st.session_state[f"comment_mode_{message_index}"] = True
            st.rerun()
    
    # Mostrar cuadro de comentario si está en modo comentario
    if st.session_state.get(f"comment_mode_{message_index}", False):
        with st.container():
            st.markdown('<div class="comment-container">', unsafe_allow_html=True)
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
    
    # Renderizar sidebar
    render_sidebar()
    
    # Crear selector de página
    if DASHBOARD_AVAILABLE:
        page = st.sidebar.radio(
            "Seleccionar página:",
            ["💬 Chat", "📊 Dashboard de Aprendizaje"],
            help="Cambia entre el chat y el panel de análisis"
        )
        
        if page == "💬 Chat":
            show_chat_interface()
        else:
            show_learning_dashboard()
    else:
        # Solo mostrar chat si el dashboard no está disponible
        show_chat_interface()
        
        if not DASHBOARD_AVAILABLE:
            st.warning("⚠️ Dashboard de aprendizaje no disponible. Instala las dependencias: `pip install plotly pandas`")

# =====================================================
# PUNTO DE ENTRADA
# =====================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Error crítico en la aplicación: {str(e)}")
        st.info("Por favor, recarga la página o contacta al administrador.")