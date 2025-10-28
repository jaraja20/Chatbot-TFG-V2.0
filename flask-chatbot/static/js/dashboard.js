// Dashboard JavaScript - Versión Mejorada con Rendimiento

let currentTab = 'performance';

document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    setupEventListeners();
    
    // Auto-refresh cada 2 minutos (era 30 segundos - OPTIMIZADO)
    setInterval(loadDashboardData, 120000);
});

function setupEventListeners() {
    // Botón de actualizar
    document.getElementById('refreshBtn').addEventListener('click', loadDashboardData);
    
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            switchTab(this.dataset.tab);
        });
    });
}

function switchTab(tabName) {
    currentTab = tabName;
    
    // Actualizar botones
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Actualizar paneles
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`${tabName}-panel`).classList.add('active');
    
    // Cargar datos específicos del tab si es necesario
    if (tabName === 'performance') {
        loadPerformanceMetrics();
    }
}

async function loadDashboardData() {
    try {
        // Cargar estadísticas generales
        await loadStats();
        
        // Cargar datos según el tab activo
        if (currentTab === 'performance') {
            await loadPerformanceMetrics();
        } else if (currentTab === 'negative') {
            await loadNegativeFeedback();
        } else if (currentTab === 'conversations') {
            await loadConversations();
        }
        
        console.log('✅ Dashboard actualizado');
    } catch (error) {
        console.error('❌ Error cargando dashboard:', error);
    }
}

// =====================================================
// ESTADÍSTICAS GENERALES - ✅ CORREGIDO
// =====================================================
async function loadStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        const data = await response.json();
        
        // ✅ CORREGIDO: Los datos están dentro de data.stats
        const stats = data.stats || data;
        
        document.getElementById('totalFeedback').textContent = stats.total || 0;
        document.getElementById('positiveFeedback').textContent = stats.positive || 0;
        document.getElementById('negativeFeedback').textContent = stats.negative || 0;
        document.getElementById('satisfactionRate').textContent = `${stats.satisfaction_rate || 0}%`;
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

// =====================================================
// NUEVA: MÉTRICAS DE RENDIMIENTO
// =====================================================
async function loadPerformanceMetrics() {
    try {
        const response = await fetch('/api/dashboard/performance');
        const data = await response.json();
        
        // Métricas principales
        const avgConf = (data.avg_confidence * 100).toFixed(1);
        document.getElementById('avgConfidence').textContent = `${avgConf}%`;
        document.getElementById('confidenceProgress').style.width = `${avgConf}%`;
        
        document.getElementById('totalInteractions').textContent = data.total_interactions;
        
        const fallback = (data.fallback_rate * 100).toFixed(1);
        document.getElementById('fallbackRate').textContent = `${fallback}%`;
        document.getElementById('fallbackProgress').style.width = `${fallback}%`;
        
        const success = (data.success_rate * 100).toFixed(1);
        document.getElementById('successRate').textContent = `${success}%`;
        document.getElementById('successProgress').style.width = `${success}%`;
        
        // Top Intents
        renderTopIntents(data.top_intents);
        
        // Distribución de confianza
        renderConfidenceDistribution(data.confidence_distribution);
        
    } catch (error) {
        console.error('Error cargando métricas:', error);
        document.getElementById('topIntentsChart').innerHTML = '<p class="error-message">Error cargando métricas de rendimiento</p>';
    }
}

function renderTopIntents(intents) {
    const container = document.getElementById('topIntentsChart');
    
    if (!intents || intents.length === 0) {
        container.innerHTML = '<p class="empty-message">No hay datos de intents disponibles</p>';
        return;
    }
    
    let html = '';
    intents.forEach((intent, index) => {
        const confidence = (intent.avg_confidence * 100).toFixed(1);
        const confidenceClass = confidence >= 80 ? 'success' : confidence >= 60 ? 'warning' : 'danger';
        
        html += `
            <div class="intent-row">
                <span class="intent-name">${index + 1}. ${intent.intent_name || 'unknown'}</span>
                <div class="intent-stats">
                    <div class="stat-item">
                        <span class="label">Usos:</span>
                        <span class="value">${intent.count}</span>
                    </div>
                    <div class="stat-item">
                        <span class="label">Confianza:</span>
                        <span class="value ${confidenceClass}">${confidence}%</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function renderConfidenceDistribution(distribution) {
    const container = document.getElementById('confidenceDistribution');
    
    if (!distribution) {
        container.innerHTML = '<p class="empty-message">No hay datos de distribución disponibles</p>';
        return;
    }
    
    const ranges = [
        { label: 'Muy Alta (90-100%)', value: distribution.high || 0, color: '#10b981' },
        { label: 'Alta (75-89%)', value: distribution.medium_high || 0, color: '#3b82f6' },
        { label: 'Media (60-74%)', value: distribution.medium || 0, color: '#f59e0b' },
        { label: 'Baja (<60%)', value: distribution.low || 0, color: '#ef4444' }
    ];
    
    const total = ranges.reduce((sum, r) => sum + r.value, 0);
    
    let html = '<div style="margin-top: 16px;">';
    ranges.forEach(range => {
        const percentage = total > 0 ? ((range.value / total) * 100).toFixed(1) : 0;
        html += `
            <div style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="font-size: 14px; color: #374151;">${range.label}</span>
                    <span style="font-size: 14px; font-weight: 600; color: #1f2937;">${range.value} (${percentage}%)</span>
                </div>
                <div style="width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
                    <div style="width: ${percentage}%; height: 100%; background: ${range.color}; transition: width 0.5s ease;"></div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// =====================================================
// FEEDBACK NEGATIVO (MEJORADO con botón Resuelto)
// =====================================================
async function loadNegativeFeedback() {
    try {
        const response = await fetch('/api/dashboard/negative-feedback');
        const data = await response.json();
        
        const container = document.getElementById('negativeFeedbackList');
        
        if (!data || data.length === 0) {
            container.innerHTML = '<p class="empty-message">¡Excelente! No hay feedback negativo reciente</p>';
            return;
        }
        
        let html = '';
        data.forEach(item => {
            const isResolved = item.resolved || false;
            const resolvedBadge = isResolved ? '<span class="resolved-badge">✓ Resuelto</span>' : '';
            const resolveButton = !isResolved ? 
                `<button class="btn-resolve" onclick="markAsResolved(${item.id})">✓ Marcar como Resuelto</button>` : 
                '<button class="btn-resolve" disabled>✓ Ya Resuelto</button>';
            
            html += `
                <div class="feedback-item ${isResolved ? 'resolved' : ''}" id="feedback-${item.id}">
                    <div class="feedback-header">
                        <span class="feedback-time">${item.timestamp || 'Sin fecha'}</span>
                        ${resolvedBadge}
                    </div>
                    
                    <div class="feedback-messages">
                        <div class="message user">
                            <strong>👤 Usuario:</strong> ${item.user_message}
                        </div>
                        <div class="message bot">
                            <strong>🤖 Bot:</strong> ${item.bot_response}
                        </div>
                    </div>
                    
                    ${item.feedback_comment ? `
                        <div class="feedback-comment">
                            <strong>💬 Comentario:</strong>
                            <p>${item.feedback_comment}</p>
                        </div>
                    ` : ''}
                    
                    <div class="feedback-actions">
                        ${resolveButton}
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Error cargando feedback negativo:', error);
        document.getElementById('negativeFeedbackList').innerHTML = 
            '<p class="error-message">Error cargando feedback negativo</p>';
    }
}

// NUEVA: Marcar feedback como resuelto
async function markAsResolved(feedbackId) {
    try {
        const response = await fetch(`/api/dashboard/feedback/${feedbackId}/resolve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            // Actualizar UI
            const feedbackItem = document.getElementById(`feedback-${feedbackId}`);
            if (feedbackItem) {
                feedbackItem.classList.add('resolved');
                
                // Agregar badge
                const header = feedbackItem.querySelector('.feedback-header');
                if (!header.querySelector('.resolved-badge')) {
                    header.innerHTML += '<span class="resolved-badge">✓ Resuelto</span>';
                }
                
                // Cambiar botón
                const button = feedbackItem.querySelector('.btn-resolve');
                button.textContent = '✓ Ya Resuelto';
                button.disabled = true;
            }
            
            console.log('✅ Feedback marcado como resuelto');
        } else {
            console.error('❌ Error marcando como resuelto');
            alert('Error al marcar como resuelto');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al conectar con el servidor');
    }
}

// =====================================================
// CONVERSACIONES
// =====================================================
async function loadConversations() {
    try {
        const response = await fetch('/api/dashboard/conversations');
        const data = await response.json();
        
        const container = document.getElementById('conversationsList');
        
        if (!data || data.length === 0) {
            container.innerHTML = '<p class="empty-message">No hay conversaciones recientes</p>';
            return;
        }
        
        let html = '';
        data.forEach(item => {
            const feedbackIcon = item.feedback_type === 'positive' ? '👍' : 
                                 item.feedback_type === 'negative' ? '👎' : '➖';
            
            html += `
                <div class="conversation-item">
                    <div class="conversation-header">
                        <span class="conversation-time">${item.timestamp || 'Sin fecha'}</span>
                        <span class="feedback-icon">${feedbackIcon}</span>
                    </div>
                    
                    <div class="conversation-messages">
                        <div class="message user">
                            <strong>👤 Usuario:</strong> ${item.user_message}
                        </div>
                        <div class="message bot">
                            <strong>🤖 Bot:</strong> ${item.bot_response}
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Error cargando conversaciones:', error);
        document.getElementById('conversationsList').innerHTML = 
            '<p class="error-message">Error cargando conversaciones</p>';
    }
}

// Estilos adicionales para items resueltos
const style = document.createElement('style');
style.textContent = `
    .feedback-item.resolved {
        opacity: 0.6;
        border-left: 4px solid #10b981 !important;
    }
    
    .feedback-actions {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
    }
    
    .empty-message {
        text-align: center;
        padding: 40px;
        color: #6b7280;
        font-size: 16px;
    }
    
    .error-message {
        text-align: center;
        padding: 40px;
        color: #ef4444;
        font-size: 16px;
    }
    
    .success {
        color: #10b981 !important;
    }
    
    .warning {
        color: #f59e0b !important;
    }
    
    .danger {
        color: #ef4444 !important;
    }
`;
document.head.appendChild(style);