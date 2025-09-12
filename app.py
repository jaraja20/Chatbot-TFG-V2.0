import streamlit as st
import requests

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

st.set_page_config(page_title="Chatbot", page_icon="🤖")

# ===== CSS =====
st.markdown(
    """
    <style>
    body {
        background-color: white;
    }
    .chat-container {
        height: 500px;
        overflow-y: auto;
        border: 2px solid #333;
        padding: 10px;
        border-radius: 10px;
        background-color: #000; /* Fondo negro del chat */
    }
    .chat-bubble {
        max-width: 70%;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px;
        line-height: 1.4;
        font-size: 15px;
        display: inline-block;
        word-wrap: break-word;
        color: white;
    }
    .user-msg {
        background-color: #0084ff;
        text-align: right;
        float: right;
        clear: both;
    }
    .bot-msg {
        background-color: #444;
        text-align: left;
        float: left;
        clear: both;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💬 Chat con el Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "bot", "content": "👋 ¡Hola! Soy Jarabot y te ayudaré en el proceso de gestionar tu cédula. ¿En qué puedo ayudarte hoy?"}
    ]

if "pending_message" not in st.session_state:
    st.session_state.pending_message = None

# ===== Mostrar historial =====
chat_html = "<div class='chat-container'>"
for i, msg in enumerate(st.session_state.messages):
    role_class = "user-msg" if msg["role"] == "user" else "bot-msg"
    icon = "🧑" if msg["role"] == "user" else "🤖"
    chat_html += f"<div class='chat-bubble {role_class}' id='msg-{i}'>{icon} {msg['content']}</div>"
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# ===== Scroll automático =====
if st.session_state.messages:
    last_id = f"msg-{len(st.session_state.messages)-1}"
    scroll_script = f"""
    <script>
    var last_msg = document.getElementById("{last_id}");
    if (last_msg) {{
        last_msg.scrollIntoView({{behavior: "smooth"}});
    }}
    </script>
    """
    st.markdown(scroll_script, unsafe_allow_html=True)

# ===== Input =====
user_input = st.chat_input("Escribe tu mensaje...")

if user_input:
    # Mostrar inmediatamente el mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": user_input})
    # Guardar pendiente para enviar al bot en el próximo ciclo
    st.session_state.pending_message = user_input
    st.rerun()

# ===== Procesar mensaje pendiente (respuesta del bot) =====
if st.session_state.pending_message:
    try:
        response = requests.post(RASA_URL, json={"sender": "user", "message": st.session_state.pending_message})
        bot_responses = response.json()

        for resp in bot_responses:
            if "text" in resp:
                st.session_state.messages.append({"role": "bot", "content": resp["text"]})

    except Exception:
        st.session_state.messages.append({"role": "bot", "content": "⚠️ Error al conectar con Rasa."})

    # Limpiar mensaje pendiente
    st.session_state.pending_message = None
    st.rerun()
