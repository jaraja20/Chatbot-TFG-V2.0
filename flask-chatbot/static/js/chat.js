// =====================================================
// CHATBOT - FUNCIONALIDAD JAVASCRIPT
// =====================================================

let messageCount = 1;
let currentFeedbackContext = null;
let sessionId = null;

// =====================================================
// ELEMENTOS DEL DOM
// =====================================================

const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const resetBtn = document.getElementById('restart-btn');
const commentModal = document.getElementById('commentModal');
const sendCommentBtn = document.getElementById('sendComment');
const cancelCommentBtn = document.getElementById('cancelComment');
const commentText = document.getElementById('commentText');

// =====================================================
// DETECTOR DE CORRECCIONES MANUALES
// =====================================================

function esCorreccionDeUsuario(texto) {
    const patrones = [
        "debes responder",
        "tienes que responder",
        "deberías responder",
        "la respuesta correcta es",
        "debería ser",
        "corrige esto",
        "deberías decir"
    ];
    const textoLower = texto.toLowerCase();
    return patrones.some(p => textoLower.includes(p));
}


// =====================================================
// ENVIAR MENSAJE
// =====================================================

let isProcessing = false; // 🔒 Evitar doble envío

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const message = userInput.value.trim();
    if (!message || isProcessing) return;
    
    isProcessing = true; // 🔒 Bloquear nuevos envíos
    
    // DESHABILITADO: Copilot (puerto 5001)
    // Solo usar si necesitas el copilot agent separado
    /*
    try {
        console.log("🤖 Intentando usar Copilot...");
        const copilotResponse = await fetch('http://localhost:5001/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        if (copilotResponse.ok) {
            const copilotData = await copilotResponse.json();
            addUserMessage(message);
            userInput.value = '';
            addBotMessage(copilotData.response, "Ahora");
            return;
        }
    } catch (error) {
        console.log("❌ Copilot no disponible, usando sistema normal:", error);
    }
    */

    // Agregar mensaje del usuario
    addUserMessage(message);
    userInput.value = '';

    // ✅ Verificar si es una corrección
    if (esCorreccionDeUsuario(message)) {
        console.log('🧠 Corrección detectada, enviando al servidor...');

        // Buscar el último mensaje del bot en el contenedor del chat
        const allBotMessages = chatContainer.querySelectorAll('.bot-message .bot-bubble');
        const lastBotMessage = allBotMessages.length > 0 ? allBotMessages[allBotMessages.length - 1] : null;

        if (lastBotMessage) {
            const botResponse = lastBotMessage.textContent.trim();
            await guardarCorreccion(sessionId, message, botResponse);
            addBotMessage("✅ Gracias, he registrado tu corrección para aprendizaje.", "Ahora");
        } else {
            addBotMessage("⚠️ No hay respuesta anterior para corregir.", "Ahora");
        }

        return; // 🚫 Salir para no enviar a Flask
    }


    // Mostrar indicador de escritura
    const typingId = showTypingIndicator();

    try {
        // Enviar a Flask backend con session_id
        const response = await fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId  // ✅ AGREGAR session_id
            })
        });

        const data = await response.json();

        if (data.session_id) {
            sessionId = data.session_id;
        }

        // Remover indicador de escritura
        removeTypingIndicator(typingId);

        if (data.success) {
            console.log('🔍 Respuesta del servidor:', data);
            
            // Preparar opciones para el mensaje del bot
            const botMessageOptions = {};
            
            // Si incluye botón del dashboard, agregarlo a las opciones
            if (data.show_dashboard_button) {
                console.log('✅ Backend dice mostrar dashboard button!');
                botMessageOptions.showDashboardButton = true;
                botMessageOptions.dashboardUrl = data.dashboard_url || '/dashboard';
            }
            
            console.log('🔍 botMessageOptions:', botMessageOptions);
            
            // Agregar respuesta del bot
            addBotMessage(data.bot_message, data.timestamp, botMessageOptions);
        } else {
            addBotMessage('Lo siento, hubo un error al procesar tu mensaje. Por favor intenta nuevamente.', 'Ahora');
        }

    } catch (error) {
        console.error('Error:', error);
        removeTypingIndicator(typingId);
        addBotMessage('Error de conexión. Verifica que el servidor esté activo.', 'Ahora');
    } finally {
        isProcessing = false; // 🔓 Desbloquear para siguiente mensaje
    }
});


// =====================================================
// AGREGAR MENSAJE DEL USUARIO
// =====================================================

function generateSessionId() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    const id = `web_${timestamp}_${random}`;
    console.log('🆔 Session ID generado:', id);
    return id;
}
if (!sessionId) {
    sessionId = generateSessionId();
}
function addUserMessage(text) {
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper user-message';
    messageWrapper.dataset.messageId = messageCount;
    
    const now = new Date();
    const time = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    messageWrapper.innerHTML = `
        <div class="avatar user-avatar">👤</div>
        <div class="message-content">
            <div class="message-bubble user-bubble">
                ${escapeHtml(text)}
            </div>
            <div class="message-time">${time}</div>
        </div>
    `;
    
    chatContainer.appendChild(messageWrapper);
    scrollToBottom();
    messageCount++;
}

// =====================================================
// AGREGAR MENSAJE DEL BOT
// =====================================================

function addBotMessage(text, time = 'Ahora', options = {}) {
    console.log('🔍 addBotMessage llamado con options:', options);
    
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper bot-message';
    messageWrapper.dataset.messageId = messageCount;
    messageWrapper.dataset.userMessage = userInput.value;
    messageWrapper.dataset.botResponse = text;
    
    // Configurar marked para permitir emojis y otros caracteres especiales
    marked.setOptions({
        breaks: true,
        gfm: true,
        mangle: false,
        headerIds: false
    });
    
    // Renderizar el markdown a HTML
    const renderedText = marked.parse(text);
    
    // Botón del dashboard si se especifica
    console.log('🔍 showDashboardButton:', options.showDashboardButton);
    const dashboardButton = options.showDashboardButton ? `
        <a href="${options.dashboardUrl || '/dashboard'}" 
           class="dashboard-button" 
           target="_blank"
           style="display: inline-block; margin-top: 15px; padding: 12px 24px; 
                  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; text-decoration: none; border-radius: 8px; 
                  font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                  transition: all 0.3s ease; text-align: center;"
           onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.4)';"
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(102, 126, 234, 0.3)';">
            📊 Abrir Dashboard
        </a>
    ` : '';
    
    console.log('🔍 Dashboard button HTML:', dashboardButton);
    
    messageWrapper.innerHTML = `
        <div class="avatar bot-avatar">
            <img src="/static/images/bot.png" alt="Bot">
        </div>
        <div class="message-content">
            <div class="message-bubble bot-bubble markdown-content">
                ${renderedText}
            </div>
            ${dashboardButton}
            <!-- Botones de feedback -->
            <div class="feedback-buttons" style="margin-top: 10px;">
                <button class="feedback-btn like-btn" data-message-id="${messageCount}" data-type="positive">
                    <img src="/static/images/like.webp" alt="Me gusta" class="feedback-icon">
                    Útil
                </button>
                <button class="feedback-btn dislike-btn" data-message-id="${messageCount}" data-type="negative">
                    <img src="/static/images/dislike.png" alt="No me gusta" class="feedback-icon">
                    Mejorar
                </button>
            </div>
            <div class="message-time">${time}</div>
        </div>
    `;
    
    chatContainer.appendChild(messageWrapper);
    
    // Agregar listeners a los botones de feedback
    setupFeedbackButtons(messageWrapper);
    
    scrollToBottom();
    messageCount++;
}

// =====================================================
// INDICADOR DE ESCRITURA
// =====================================================

function showTypingIndicator() {
    const typingId = `typing-${Date.now()}`;
    const typingWrapper = document.createElement('div');
    typingWrapper.className = 'message-wrapper bot-message';
    typingWrapper.id = typingId;
    
    typingWrapper.innerHTML = `
        <div class="avatar bot-avatar">
            <img src="/static/images/bot.png" alt="Bot">
        </div>
        <div class="message-content">
            <div class="message-bubble bot-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    
    chatContainer.appendChild(typingWrapper);
    scrollToBottom();
    
    return typingId;
}

function removeTypingIndicator(typingId) {
    const element = document.getElementById(typingId);
    if (element) {
        element.remove();
    }
}

// =====================================================
// FEEDBACK
// =====================================================

function setupFeedbackButtons(messageWrapper) {
    const likeBtn = messageWrapper.querySelector('.like-btn');
    const dislikeBtn = messageWrapper.querySelector('.dislike-btn');
    
    likeBtn.addEventListener('click', function() {
        handleFeedback(messageWrapper, 'positive');
    });
    
    dislikeBtn.addEventListener('click', function() {
        handleFeedback(messageWrapper, 'negative');
    });
}

async function handleFeedback(messageWrapper, feedbackType) {
    const messageId = messageWrapper.dataset.messageId;
    
    // Obtener mensajes del contexto
    const allMessages = chatContainer.querySelectorAll('.message-wrapper');
    let userMessage = '';
    let botResponse = messageWrapper.querySelector('.bot-bubble').textContent.trim();
    
    // Buscar el mensaje del usuario anterior
    for (let i = allMessages.length - 1; i >= 0; i--) {
        if (allMessages[i] === messageWrapper) {
            // Encontrado el mensaje del bot, buscar el del usuario anterior
            for (let j = i - 1; j >= 0; j--) {
                if (allMessages[j].classList.contains('user-message')) {
                    userMessage = allMessages[j].querySelector('.user-bubble').textContent.trim();
                    break;
                }
            }
            break;
        }
    }
    
    if (feedbackType === 'positive') {
        // Feedback positivo - guardar directo
        await sendFeedback(userMessage, botResponse, feedbackType, null);
        
        // Marcar botón como activo
        const likeBtn = messageWrapper.querySelector('.like-btn');
        likeBtn.classList.add('active');
        likeBtn.disabled = true;
        
        // Desactivar el otro botón
        const dislikeBtn = messageWrapper.querySelector('.dislike-btn');
        dislikeBtn.disabled = true;
        
        showToast('¡Gracias por tu feedback! 👍');
        
    } else {
        // Feedback negativo - mostrar modal para comentario
        currentFeedbackContext = {
            messageWrapper,
            userMessage,
            botResponse
        };
        
        commentModal.classList.add('show');
        commentText.value = '';
        commentText.focus();
    }
}

// =====================================================
// ENVIAR FEEDBACK AL SERVIDOR
// =====================================================

async function sendFeedback(userMessage, botResponse, feedbackType, comment) {
    try {
        const response = await fetch('/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_message: userMessage,
                bot_response: botResponse,
                feedback_type: feedbackType,
                comment: comment
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Feedback guardado correctamente');
        } else {
            console.error('Error al guardar feedback:', data.error);
        }
        
    } catch (error) {
        console.error('Error al enviar feedback:', error);
    }
}

// =====================================================
// GUARDAR CORRECCIONES MANUALES
// =====================================================

async function guardarCorreccion(sessionId, userMessage, botResponse) {
    try {
        // Extraer el texto corregido por el usuario (parte después de “debes responder con...”)
        let correctedText = userMessage.toLowerCase()
            .replace("debes responder con", "")
            .replace("deberías responder con", "")
            .replace("tienes que responder con", "")
            .trim();

        const response = await fetch('/save_correction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                user_message: userMessage,
                bot_response: botResponse,
                corrected_response: correctedText
            })
        });

        const data = await response.json();

        if (data.success) {
            console.log("✅ Corrección guardada:", correctedText);
            showToast("✅ Corrección registrada");
        } else {
            console.error("Error al guardar corrección:", data.error);
            showToast("⚠️ No se pudo guardar la corrección");
        }
    } catch (error) {
        console.error("Error guardando corrección:", error);
        showToast("❌ Error de conexión al guardar corrección");
    }
}


// =====================================================
// MODAL DE COMENTARIOS
// =====================================================

sendCommentBtn.addEventListener('click', async () => {
    const comment = commentText.value.trim();
    
    if (!comment) {
        alert('Por favor escribe un comentario');
        return;
    }
    
    if (currentFeedbackContext) {
        await sendFeedback(
            currentFeedbackContext.userMessage,
            currentFeedbackContext.botResponse,
            'negative',
            comment
        );
        
        // Marcar botón como activo
        const dislikeBtn = currentFeedbackContext.messageWrapper.querySelector('.dislike-btn');
        dislikeBtn.classList.add('active');
        dislikeBtn.disabled = true;
        
        // Desactivar el otro botón
        const likeBtn = currentFeedbackContext.messageWrapper.querySelector('.like-btn');
        likeBtn.disabled = true;
        
        showToast('¡Gracias por tu comentario! 💬');
    }
    
    commentModal.classList.remove('show');
    currentFeedbackContext = null;
});

cancelCommentBtn.addEventListener('click', () => {
    commentModal.classList.remove('show');
    currentFeedbackContext = null;
});

// Cerrar modal al hacer click fuera
commentModal.addEventListener('click', (e) => {
    if (e.target === commentModal) {
        commentModal.classList.remove('show');
        currentFeedbackContext = null;
    }
});

// =====================================================
// BOTONES DE ACCESO RÁPIDO
// =====================================================

document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const message = btn.dataset.message;
        userInput.value = message;
        chatForm.dispatchEvent(new Event('submit'));
    });
});

// =====================================================
// REINICIAR CHAT
// =====================================================

resetBtn.addEventListener('click', async () => {
    if (confirm('¿Estás seguro de que quieres reiniciar la conversación?')) {
        try {
            // ✅ NUEVO: Llamar al backend para reiniciar
            const response = await fetch('/restart_conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ session_id: sessionId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Actualizar session_id
                sessionId = data.session_id;
                console.log('✅ Nueva sesión:', sessionId);
            }
        } catch (error) {
            console.error('Error reiniciando:', error);
            // Fallback: generar localmente
            sessionId = generateSessionId();
        }
        
        // Limpiar interfaz
        const firstMessage = chatContainer.querySelector('.message-wrapper');
        chatContainer.innerHTML = '';
        if (firstMessage) {
            chatContainer.appendChild(firstMessage.cloneNode(true));
            setupFeedbackButtons(chatContainer.querySelector('.message-wrapper'));
        }
        messageCount = 1;
        userInput.value = '';
        
        showToast('✅ Conversación reiniciada');
    }
});

// =====================================================
// UTILIDADES
// =====================================================

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message) {
    // Toast simple (puedes mejorarlo)
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 2000;
        animation: slideIn 0.3s;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// =====================================================
// INICIALIZACIÓN
// =====================================================

console.log('💬 Chatbot Flask inicializado');
console.log('🚀 Listo para recibir mensajes');
