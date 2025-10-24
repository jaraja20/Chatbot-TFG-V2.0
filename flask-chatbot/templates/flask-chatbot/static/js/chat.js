// =====================================================
// CHATBOT - FUNCIONALIDAD JAVASCRIPT
// =====================================================

let messageCount = 1;
let currentFeedbackContext = null;

// =====================================================
// ELEMENTOS DEL DOM
// =====================================================

const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const resetBtn = document.getElementById('resetBtn');
const commentModal = document.getElementById('commentModal');
const sendCommentBtn = document.getElementById('sendComment');
const cancelCommentBtn = document.getElementById('cancelComment');
const commentText = document.getElementById('commentText');

// =====================================================
// ENVIAR MENSAJE
// =====================================================

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message) return;
    
    // Agregar mensaje del usuario
    addUserMessage(message);
    userInput.value = '';
    
    // Mostrar indicador de escritura
    const typingId = showTypingIndicator();
    
    try {
        // Enviar a Flask backend
        const response = await fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        // Remover indicador de escritura
        removeTypingIndicator(typingId);
        
        if (data.success) {
            // Agregar respuesta del bot
            addBotMessage(data.bot_message, data.timestamp);
        } else {
            addBotMessage('Lo siento, hubo un error al procesar tu mensaje. Por favor intenta nuevamente.', 'Ahora');
        }
        
    } catch (error) {
        console.error('Error:', error);
        removeTypingIndicator(typingId);
        addBotMessage('Error de conexión. Verifica que el servidor esté activo.', 'Ahora');
    }
});

// =====================================================
// AGREGAR MENSAJE DEL USUARIO
// =====================================================

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

function addBotMessage(text, time = 'Ahora') {
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper bot-message';
    messageWrapper.dataset.messageId = messageCount;
    messageWrapper.dataset.userMessage = userInput.value;
    messageWrapper.dataset.botResponse = text;
    
    messageWrapper.innerHTML = `
        <div class="avatar bot-avatar">
            <img src="/static/images/bot.png" alt="Bot">
        </div>
        <div class="message-content">
            <div class="message-bubble bot-bubble">
                ${escapeHtml(text)}
                
                <!-- Botones de feedback DENTRO de la burbuja -->
                <div class="feedback-buttons">
                    <button class="feedback-btn like-btn" data-message-id="${messageCount}" data-type="positive">
                        <img src="/static/images/like.webp" alt="Me gusta" class="feedback-icon">
                        Útil
                    </button>
                    <button class="feedback-btn dislike-btn" data-message-id="${messageCount}" data-type="negative">
                        <img src="/static/images/dislike.png" alt="No me gusta" class="feedback-icon">
                        Mejorar
                    </button>
                </div>
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

resetBtn.addEventListener('click', () => {
    if (confirm('¿Estás seguro de que quieres reiniciar la conversación?')) {
        // Mantener solo el mensaje inicial
        const firstMessage = chatContainer.querySelector('.message-wrapper');
        chatContainer.innerHTML = '';
        if (firstMessage) {
            chatContainer.appendChild(firstMessage.cloneNode(true));
            setupFeedbackButtons(chatContainer.querySelector('.message-wrapper'));
        }
        messageCount = 1;
        userInput.value = '';
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
