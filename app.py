import streamlit as st
import requests
import time
import json
from datetime import datetime
from typing import List, Dict, Optional

# Importar el dashboard de aprendizaje
try:
    from learning_dashboard import show_learning_dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False

# =====================================================
# CONFIGURACIÓN
# =====================================================
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
RASA_STATUS_URL = "http://localhost:5005/status"

st.set_page_config(
    page_title="Sistema de Turnos - Cédulas",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CSS PERSONALIZADO PARA AUTO-SCROLL
# =====================================================
def inject_custom_css():
    """Inyecta CSS personalizado para mejorar el scroll del chat - versión simplificada"""
    st.markdown("""
    <style>
    /* Solo estilos para animaciones de mensajes */
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
    </style>
    """, unsafe_allow_html=True)

def auto_scroll_to_bottom():
    """Fuerza el scroll hacia abajo usando JavaScript"""
    scroll_script = """
    <script>
    // Función para hacer scroll al final
    function scrollToBottom() {
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    // Ejecutar inmediatamente
    scrollToBottom();
    
    // También después de un pequeño delay para asegurar renderizado
    setTimeout(scrollToBottom, 100);
    setTimeout(scrollToBottom, 300);
    </script>
    """
    st.markdown(scroll_script, unsafe_allow_html=True)

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

@st.cache_data(ttl=30)  # Cache por 30 segundos
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
            timeout=15,  # Aumentar timeout
            headers={
                "Content-Type": "application/json; charset=utf-8"  # Especificar charset
            }
        )
        
        if response.status_code == 200:
            # Verificar que hay respuesta
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
    """Inicializa el estado de la sesión"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "¡Hola! Soy tu asistente virtual para gestión de cédulas en Ciudad del Este. ¿En qué puedo ayudarte hoy?",
                "timestamp": datetime.now().isoformat()
            }
        ]
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"
    
    # Inicializar flag para scroll
    if "should_scroll" not in st.session_state:
        st.session_state.should_scroll = False

def add_message(role: str, content: str):
    """Agrega mensaje al historial y marca para scroll"""
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    # Marcar que necesitamos hacer scroll
    st.session_state.should_scroll = True

def process_quick_button(user_msg: str):
    """Procesa los botones rápidos de la sidebar"""
    # Agregar mensaje del usuario
    add_message("user", user_msg)
    
    # Obtener respuesta de Rasa
    bot_responses = send_message_to_rasa(user_msg)
    
    # Procesar respuestas
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
        
        # Acciones rápidas
        st.subheader("🚀 Acciones Rápidas")
        
        if st.button("📅 Agendar Turno", help="Iniciar proceso de agendamiento"):
            process_quick_button("Quiero agendar un turno")
            st.rerun()
        
        if st.button("📋 Ver Requisitos", help="Consultar documentos necesarios"):
            process_quick_button("Qué requisitos necesito")
            st.rerun()
        
        if st.button("📍 Ver Ubicación", help="Consultar ubicación de la oficina"):
            process_quick_button("Dónde queda la oficina")
            st.rerun()
        
        if st.button("⏰ Consultar Horarios", help="Ver horarios de atención"):
            process_quick_button("Cuáles son los horarios")
            st.rerun()
        
        if st.button("📊 Ver Saturación", help="Consultar ocupación actual"):
            process_quick_button("Cuánto es la saturación actualmente")
            st.rerun()
        
        if st.button("⏱️ Tiempo Espera", help="Consultar tiempo de espera"):
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
        
        if st.button("🔄 Reiniciar Chat", help="Borrar historial y empezar de nuevo"):
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Chat reiniciado. ¿En qué puedo ayudarte?",
                "timestamp": datetime.now().isoformat()
            }]
            st.session_state.should_scroll = True
            st.rerun()
        
        if st.button("💾 Guardar Chat", help="Descargar historial de conversación"):
            chat_history = {
                "session_id": st.session_state.session_id,
                "messages": st.session_state.messages,
                "timestamp": datetime.now().isoformat()
            }
            st.download_button(
                label="Descargar JSON",
                data=json.dumps(chat_history, indent=2, ensure_ascii=False),
                file_name=f"chat_turnos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

def show_chat_interface():
    """Muestra la interfaz principal del chat con scroll mejorado"""
    
    # Inyectar CSS personalizado
    inject_custom_css()
    
    # Header principal
    st.title("🏛️ Sistema de Gestión de Turnos")
    st.subheader("Cédulas de Identidad - Ciudad del Este")
    
    # Contenedor principal del chat
    chat_container = st.container()
    
    with chat_container:
        # Mostrar historial de chat
        for i, message in enumerate(st.session_state.messages):
            role = message["role"]
            with st.chat_message(role):
                # Contenido del mensaje con clase CSS
                st.markdown(f'<div class="chat-message">{message["content"]}</div>', 
                           unsafe_allow_html=True)
                
                # Timestamp
                if "timestamp" in message:
                    timestamp = datetime.fromisoformat(message["timestamp"]).strftime("%H:%M")
                    st.markdown(f'<div class="timestamp">⏰ {timestamp}</div>', 
                               unsafe_allow_html=True)
    
    # Input del usuario (fijo en la parte inferior)
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        # Agregar mensaje del usuario al historial
        add_message("user", prompt)
        
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
        
        # También usar el método nativo de Streamlit para scroll
        st.markdown("""
        <script>
        // Scroll nativo de Streamlit
        const chatElements = parent.document.querySelectorAll('[data-testid="stChatMessage"]');
        if (chatElements.length > 0) {
            const lastMessage = chatElements[chatElements.length - 1];
            lastMessage.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
        </script>
        """, unsafe_allow_html=True)

# =====================================================
# APLICACIÓN PRINCIPAL CON PESTAÑAS
# =====================================================
def main():
    """Función principal de la aplicación con pestañas"""
    initialize_session()
    
    # Renderizar sidebar
    render_sidebar()
    
    # Crear pestañas principales
    if DASHBOARD_AVAILABLE:
        # Selector de página en lugar de pestañas
        page = st.sidebar.radio(
            "Seleccionar página:",
            ["💬 Chat", "📊 Dashboard de Aprendizaje"]
        )
        
        if page == "💬 Chat":
            show_chat_interface()
        else:
            show_learning_dashboard()
    else:
        # Solo mostrar chat si el dashboard no está disponible
        show_chat_interface()
        
        # Mostrar advertencia si el dashboard no está disponible
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