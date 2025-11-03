let messageCount = 1;
let sessionId = null;

function generateSessionId() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `web_${timestamp}_${random}`;
}
if (!sessionId) {
    sessionId = generateSessionId();
}

const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const backendSelect = document.getElementById('backendSelect');
const sessionIdDisplay = document.getElementById('sessionIdDisplay');

// initialize backend selection from localStorage
const BACKENDS = {
    demo: 'http://localhost:5020/chat',
    real: 'http://localhost:5001/chat'
};
let selectedBackend = localStorage.getItem('copilot_backend') || 'demo';
if (backendSelect) {
    backendSelect.value = selectedBackend;
    backendSelect.addEventListener('change', function() {
        selectedBackend = backendSelect.value;
        localStorage.setItem('copilot_backend', selectedBackend);
    });
}

if (sessionIdDisplay) {
    sessionIdDisplay.textContent = `session: ${sessionId}`;
}

function addUserMessage(text) {
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper user-message';
    messageWrapper.dataset.messageId = messageCount;
    messageWrapper.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    chatContainer.appendChild(messageWrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    messageCount++;
}

function addBotMessage(text) {
    marked.setOptions({ breaks: true, gfm: true });
    const renderedText = marked.parse(text);
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper bot-message';
    messageWrapper.dataset.messageId = messageCount;
    messageWrapper.innerHTML = `<div class="message-bubble">${renderedText}</div>`;
    chatContainer.appendChild(messageWrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    messageCount++;
}

function escapeHtml(text) {
    return text.replace(/[&<>'"]/g, function (c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','\'':'&#39;','"':'&quot;'}[c];
    });
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;
    addUserMessage(message);
    userInput.value = '';
    // Llamada al backend Copilot
    try {
        const target = BACKENDS[selectedBackend] || BACKENDS.demo;
        console.log('Enviando a backend:', selectedBackend, target);
        const res = await fetch(target, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId }),
            mode: 'cors'
        });
        // Mostrar detalles en consola para depuración
        console.log('Copilot response (raw):', res);
        if (!res.ok) {
            const text = await res.text();
            console.error('Error response from backend:', res.status, text);
            addBotMessage('Error del servidor: ' + res.status + ' - ' + text);
        } else {
            const data = await res.json();
            console.log('Copilot data:', data);
            // update session id if backend returns one
            if (data.session_id) {
                sessionId = data.session_id;
                if (sessionIdDisplay) sessionIdDisplay.textContent = `session: ${sessionId}`;
            }
            addBotMessage(data.response || 'Error en la respuesta del servidor');
        }
    } catch (err) {
        console.error('Fetch error:', err);
        addBotMessage('No se pudo conectar con el backend Copilot. Detalle en consola.');
    }
});
