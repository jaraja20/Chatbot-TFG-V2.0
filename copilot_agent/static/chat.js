// =====================================================
// COPILOT AGENT - JAVASCRIPT
// Manejo de la interfaz de chat
// =====================================================

class CopilotChat {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.chatMessages = document.getElementById('chatMessages');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.statusText = document.getElementById('statusText');
        
        this.isProcessing = false;
        
        this.init();
    }
    
    init() {
        // Event listeners
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.clearBtn.addEventListener('click', () => this.clearChat());
        
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize del textarea
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
        
        // Cargar historial si existe
        this.loadHistory();
        
        console.log('✅ Copilot Chat inicializado');
    }
    
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isProcessing) {
            return;
        }
        
        // Limpiar input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';
        
        // Agregar mensaje del usuario
        this.addMessage('user', message);
        
        // Mostrar loading
        this.setProcessing(true);
        
        try {
            // Enviar mensaje al servidor
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message
                })
            });
            
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Agregar respuesta de Copilot
            this.addMessage('assistant', data.response);
            
        } catch (error) {
            console.error('Error enviando mensaje:', error);
            this.addMessage('assistant', 
                `⚠️ Lo siento, hubo un error al procesar tu mensaje: ${error.message}\n\n` +
                'Por favor, intenta de nuevo.'
            );
            this.updateStatus('Error', 'error');
        } finally {
            this.setProcessing(false);
        }
    }
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        const avatar = role === 'user' ? this.getUserAvatar() : this.getCopilotAvatar();
        const author = role === 'user' ? 'Tú' : 'GitHub Copilot';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-author">${author}</span>
                    <span class="message-time">${timeString}</span>
                </div>
                <div class="message-text">
                    ${this.formatMessage(content)}
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(content) {
        // Convertir markdown básico a HTML
        let formatted = content
            // Código inline
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Negrita
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Listas
            .replace(/^\- (.+)$/gm, '<li>$1</li>')
            // Saltos de línea
            .replace(/\n/g, '<br>');
        
        // Envolver listas en <ul>
        if (formatted.includes('<li>')) {
            formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        }
        
        // Envolver en párrafos si no hay listas
        if (!formatted.includes('<ul>')) {
            const paragraphs = formatted.split('<br><br>');
            formatted = paragraphs.map(p => p.trim() ? `<p>${p}</p>` : '').join('');
        }
        
        return formatted;
    }
    
    getUserAvatar() {
        return `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" fill="url(#userGradient)"/>
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill="white"/>
                <defs>
                    <linearGradient id="userGradient" x1="0" y1="0" x2="24" y2="24">
                        <stop offset="0%" stop-color="#667EEA"/>
                        <stop offset="100%" stop-color="#764BA2"/>
                    </linearGradient>
                </defs>
            </svg>
        `;
    }
    
    getCopilotAvatar() {
        return `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" fill="#0078D4"/>
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    setProcessing(processing) {
        this.isProcessing = processing;
        this.sendBtn.disabled = processing;
        this.messageInput.disabled = processing;
        
        if (processing) {
            this.loadingIndicator.style.display = 'block';
            this.updateStatus('Escribiendo...', 'processing');
        } else {
            this.loadingIndicator.style.display = 'none';
            this.updateStatus('Conectado', 'online');
            this.messageInput.focus();
        }
    }
    
    updateStatus(text, state) {
        this.statusText.textContent = text;
        const dot = document.querySelector('.status-dot');
        
        if (state === 'error') {
            dot.style.background = '#F85149';
        } else if (state === 'processing') {
            dot.style.background = '#FFA500';
        } else {
            dot.style.background = '#0ACF83';
        }
    }
    
    async clearChat() {
        if (!confirm('¿Estás seguro de que quieres limpiar la conversación?')) {
            return;
        }
        
        try {
            const response = await fetch('/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // Limpiar mensajes (mantener el de bienvenida)
                const messages = this.chatMessages.querySelectorAll('.message');
                messages.forEach((msg, index) => {
                    if (index > 0) { // Mantener el primer mensaje (bienvenida)
                        msg.remove();
                    }
                });
                
                console.log('✅ Conversación limpiada');
            }
        } catch (error) {
            console.error('Error limpiando conversación:', error);
            alert('Error al limpiar la conversación');
        }
    }
    
    async loadHistory() {
        try {
            const response = await fetch('/history');
            
            if (!response.ok) {
                return;
            }
            
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                // Limpiar mensaje de bienvenida si hay historial
                this.chatMessages.innerHTML = '';
                
                // Agregar mensajes del historial
                data.messages.forEach(msg => {
                    this.addMessage(msg.role, msg.content);
                });
            }
        } catch (error) {
            console.error('Error cargando historial:', error);
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.copilotChat = new CopilotChat();
});

// Verificar salud del servidor
async function checkServerHealth() {
    try {
        const response = await fetch('/health');
        if (response.ok) {
            console.log('✅ Servidor OK');
        }
    } catch (error) {
        console.error('❌ Servidor no disponible:', error);
    }
}

// Verificar cada 30 segundos
setInterval(checkServerHealth, 30000);
checkServerHealth();
