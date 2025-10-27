// =====================================================
// DASHBOARD JAVASCRIPT
// =====================================================

// Elementos del DOM
const refreshBtn = document.getElementById('refreshBtn');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');

// =====================================================
// INICIALIZACIÓN
// =====================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('📊 Dashboard cargado');
    loadDashboardData();
    
    // Event listeners
    refreshBtn.addEventListener('click', () => {
        refreshBtn.textContent = '⏳ Actualizando...';
        refreshBtn.disabled = true;
        loadDashboardData();
    });
    
    // Tabs
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            switchTab(btn.dataset.tab);
        });
    });
});

// =====================================================
// CARGAR DATOS DEL DASHBOARD
// =====================================================

async function loadDashboardData() {
    try {
        // Cargar estadísticas
        await loadStats();
        
        // Cargar feedback negativo
        await loadNegativeFeedback();
        
        // Cargar conversaciones
        await loadConversations();

        // 🧠 Cargar correcciones de usuario
        await loadUserCorrections();
        
        // Resetear botón
        refreshBtn.textContent = '🔄 Actualizar';
        refreshBtn.disabled = false;
        
    } catch (error) {
        console.error('Error cargando dashboard:', error);
        refreshBtn.textContent = '❌ Error';
        setTimeout(() => {
            refreshBtn.textContent = '🔄 Actualizar';
            refreshBtn.disabled = false;
        }, 2000);
    }
}


// =====================================================
// CARGAR ESTADÍSTICAS
// =====================================================

async function loadStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            // Actualizar DOM
            document.getElementById('totalFeedback').textContent = stats.total;
            document.getElementById('positiveFeedback').textContent = stats.positive;
            document.getElementById('negativeFeedback').textContent = stats.negative;
            document.getElementById('satisfactionRate').textContent = stats.satisfaction_rate + '%';
            
            console.log('✅ Estadísticas cargadas');
        } else {
            console.error('Error en stats:', data.error);
        }
        
    } catch (error) {
        console.error('Error cargando stats:', error);
    }
}

// =====================================================
// CARGAR FEEDBACK NEGATIVO
// =====================================================

async function loadNegativeFeedback() {
    try {
        const response = await fetch('/api/dashboard/negative-feedback');
        const data = await response.json();
        
        if (data.success) {
            const feedbackList = document.getElementById('negativeFeedbackList');
            
            if (data.feedback.length === 0) {
                feedbackList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🎉</div>
                        <div class="empty-state-text">¡No hay feedback negativo!</div>
                        <div class="empty-state-hint">El bot está funcionando bien</div>
                    </div>
                `;
            } else {
                feedbackList.innerHTML = data.feedback.map(item => `
                    <div class="feedback-item">
                        <div class="feedback-header">
                            <span class="feedback-date">📅 ${item.timestamp}</span>
                        </div>
                        
                        <div class="feedback-content">
                            <div class="feedback-message">
                                <div class="message-label">👤 Usuario:</div>
                                <div class="message-text">${escapeHtml(item.user_message)}</div>
                            </div>
                            
                            <div class="feedback-message">
                                <div class="message-label">🤖 Bot:</div>
                                <div class="message-text">${escapeHtml(item.bot_response)}</div>
                            </div>
                            
                            <div class="feedback-comment-box">
                                <div class="comment-label">💬 Comentario:</div>
                                <div class="comment-text">"${escapeHtml(item.comment)}"</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
            
            console.log(`✅ Feedback negativo cargado (${data.feedback.length} items)`);
        } else {
            console.error('Error en feedback:', data.error);
        }
        
    } catch (error) {
        console.error('Error cargando feedback negativo:', error);
        document.getElementById('negativeFeedbackList').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <div class="empty-state-text">Error cargando feedback</div>
            </div>
        `;
    }
}

// =====================================================
// CARGAR CONVERSACIONES
// =====================================================

async function loadConversations() {
    try {
        const response = await fetch('/api/dashboard/conversations?limit=20');
        const data = await response.json();
        
        if (data.success) {
            const conversationsList = document.getElementById('conversationsList');
            
            if (data.conversations.length === 0) {
                conversationsList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">💬</div>
                        <div class="empty-state-text">No hay conversaciones aún</div>
                        <div class="empty-state-hint">Las conversaciones aparecerán aquí</div>
                    </div>
                `;
            } else {
                conversationsList.innerHTML = data.conversations.map(conv => {
                    let feedbackClass = 'none';
                    let feedbackText = 'Sin feedback';
                    
                    if (conv.feedback_type === 'positive') {
                        feedbackClass = 'positive';
                        feedbackText = '👍 Positivo';
                    } else if (conv.feedback_type === 'negative') {
                        feedbackClass = 'negative';
                        feedbackText = '👎 Negativo';
                    }
                    
                    return `
                        <div class="conversation-item">
                            <div class="conversation-header">
                                <span class="conversation-date">📅 ${conv.timestamp}</span>
                                <span class="feedback-badge ${feedbackClass}">${feedbackText}</span>
                            </div>
                            
                            <div class="conversation-exchange">
                                <div class="exchange-message user">
                                    <div class="exchange-label">👤 Usuario</div>
                                    <div class="exchange-text">${escapeHtml(conv.user_message)}</div>
                                </div>
                                
                                <div class="exchange-message bot">
                                    <div class="exchange-label">🤖 Bot</div>
                                    <div class="exchange-text">${escapeHtml(conv.bot_response)}</div>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
            
            console.log(`✅ Conversaciones cargadas (${data.conversations.length} items)`);
        } else {
            console.error('Error en conversations:', data.error);
        }
        
    } catch (error) {
        console.error('Error cargando conversaciones:', error);
        document.getElementById('conversationsList').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <div class="empty-state-text">Error cargando conversaciones</div>
            </div>
        `;
    }
}

// =====================================================
// CARGAR CORRECCIONES DE USUARIO
// =====================================================

async function loadUserCorrections() {
    try {
        const response = await fetch('/api/dashboard/user-corrections');
        const data = await response.json();

        const correctionsList = document.getElementById('correctionsList');

        if (!data.success || data.data.length === 0) {
            correctionsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🧘</div>
                    <div class="empty-state-text">Sin correcciones registradas</div>
                    <div class="empty-state-hint">Los usuarios aún no corrigieron respuestas del bot</div>
                </div>
            `;
            return;
        }

        correctionsList.innerHTML = data.data.map(item => `
            <div class="feedback-item" style="border-left-color:#6366f1">
                <div class="feedback-header">
                    <span class="feedback-date">📅 ${item.timestamp}</span>
                    <span class="feedback-badge none">Session: ${item.session_id}</span>
                </div>

                <div class="feedback-content">
                    <div class="feedback-message">
                        <div class="message-label">👤 Usuario (Mensaje original)</div>
                        <div class="message-text">${escapeHtml(item.user_message)}</div>
                    </div>

                    <div class="feedback-message">
                        <div class="message-label">🤖 Respuesta del bot</div>
                        <div class="message-text">${escapeHtml(item.bot_response)}</div>
                    </div>

                    <div class="feedback-message" style="background:#ecfdf5;border-left:4px solid #10b981">
                        <div class="message-label">✅ Corrección sugerida</div>
                        <div class="message-text">${escapeHtml(item.corrected_response)}</div>
                    </div>
                </div>
            </div>
        `).join('');

        console.log(`✅ Correcciones cargadas (${data.data.length})`);
    } catch (error) {
        console.error('Error cargando correcciones:', error);
        document.getElementById('correctionsList').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <div class="empty-state-text">Error cargando correcciones</div>
            </div>
        `;
    }
}


// =====================================================
// CAMBIAR TABS
// =====================================================

function switchTab(tabName) {
    // Desactivar todos los tabs
    tabBtns.forEach(btn => btn.classList.remove('active'));
    tabPanels.forEach(panel => panel.classList.remove('active'));
    
    // Activar el tab seleccionado
    const activeBtn = document.querySelector(`[data-tab="${tabName}"]`);
    const activePanel = document.getElementById(`${tabName}-panel`);
    
    if (activeBtn && activePanel) {
        activeBtn.classList.add('active');
        activePanel.classList.add('active');
    }
}

// =====================================================
// UTILIDADES
// =====================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =====================================================
// AUTO-REFRESH (cada 30 segundos)
// =====================================================

setInterval(() => {
    console.log('🔄 Auto-refresh...');
    loadStats(); // Solo stats, no todo
}, 30000);

console.log('📊 Dashboard JS inicializado');
