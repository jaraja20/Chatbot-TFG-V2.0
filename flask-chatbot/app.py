"""
Flask Chatbot COMPLETO - Sistema de Turnos Cédulas
Incluye: Chat + Dashboard + Logging
Ciudad del Este
"""

from flask import Flask, render_template, request, jsonify, session
import requests
import psycopg2
from datetime import datetime
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambiar-en-produccion'

# =====================================================
# CONFIGURACIÓN
# =====================================================
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
RASA_STATUS_URL = "http://localhost:5005/status"

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# =====================================================
# IMPORTAR SISTEMA DE LOGGING MEJORADO
# =====================================================
try:
    from conversation_logger import (
        setup_improved_logging_system,
        get_improved_conversation_logger,
        log_interaction_improved
    )
    LOGGER_AVAILABLE = True
    logger.info("✅ Sistema de logging mejorado cargado")
except ImportError as e:
    LOGGER_AVAILABLE = False
    logger.warning(f"⚠️ Logger mejorado no disponible: {e}")

# =====================================================
# FUNCIONES DE BASE DE DATOS
# =====================================================

def get_db_connection():
    """Conexión a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        return None

def save_feedback(user_message, bot_response, feedback_type, comment=None):
    """Guardar feedback en la BD - COMPATIBLE con Streamlit"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Convertir feedback_type a feedback_thumbs (compatibilidad con Streamlit)
        feedback_thumbs = 1 if feedback_type == 'positive' else -1
        
        # BUSCAR mensaje existente primero
        cursor.execute("""
            SELECT id FROM conversation_messages 
            WHERE user_message = %s AND bot_response = %s 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (user_message, bot_response))
        
        existing = cursor.fetchone()
        
        if existing:
            # ACTUALIZAR mensaje existente
            cursor.execute("""
                UPDATE conversation_messages 
                SET feedback_thumbs = %s, 
                    feedback_comment = %s,
                    needs_review = CASE WHEN %s = -1 THEN TRUE ELSE needs_review END
                WHERE id = %s
            """, (feedback_thumbs, comment, feedback_thumbs, existing[0]))
            
            logger.info(f"✅ Feedback actualizado: {feedback_type}")
        else:
            # INSERTAR nuevo mensaje con feedback
            cursor.execute("""
                INSERT INTO conversation_messages 
                (session_id, user_message, bot_response, feedback_thumbs, feedback_comment, timestamp, needs_review)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                'web_chat',
                user_message,
                bot_response,
                feedback_thumbs,
                comment,
                datetime.now(),
                feedback_thumbs == -1
            ))
            
            logger.info(f"✅ Feedback guardado: {feedback_type}")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error guardando feedback: {e}")
        if conn:
            conn.close()
        return False

def get_negative_feedback():
    """Obtener feedback negativo - COMPATIBLE con Streamlit"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        # Buscar feedback_thumbs = -1 (negativo)
        query = """
        SELECT user_message, bot_response, feedback_comment, timestamp
        FROM conversation_messages
        WHERE feedback_thumbs = -1 AND feedback_comment IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 50
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        feedback_list = []
        for row in results:
            feedback_list.append({
                'user_message': row[0],
                'bot_response': row[1],
                'comment': row[2],
                'timestamp': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            })
        
        cursor.close()
        conn.close()
        
        return feedback_list
        
    except Exception as e:
        logger.error(f"Error obteniendo feedback: {e}")
        if conn:
            conn.close()
        return []

def get_feedback_stats():
    """Obtener estadísticas - COMPATIBLE con Streamlit"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # feedback_thumbs: 1 = positivo, -1 = negativo
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN feedback_thumbs = 1 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN feedback_thumbs = -1 THEN 1 ELSE 0 END) as negative
            FROM conversation_messages
            WHERE feedback_thumbs IN (1, -1)
        """)
        
        result = cursor.fetchone()
        
        stats = {
            'total': result[0] or 0,
            'positive': result[1] or 0,
            'negative': result[2] or 0,
            'satisfaction_rate': round((result[1] / result[0] * 100) if result[0] > 0 else 0, 1)
        }
        
        cursor.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        if conn:
            conn.close()
        return None


def get_recent_conversations(limit=20):
    """Obtener conversaciones - COMPATIBLE con Streamlit"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        
        query = """
        SELECT user_message, bot_response, feedback_thumbs, timestamp
        FROM conversation_messages
        ORDER BY timestamp DESC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        conversations = []
        for row in results:
            # Convertir feedback_thumbs a feedback_type
            feedback_type = None
            if row[2] == 1:
                feedback_type = 'positive'
            elif row[2] == -1:
                feedback_type = 'negative'
            
            conversations.append({
                'user_message': row[0],
                'bot_response': row[1],
                'feedback_type': feedback_type,
                'timestamp': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None
            })
        
        cursor.close()
        conn.close()
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error obteniendo conversaciones: {e}")
        if conn:
            conn.close()
        return []

# =====================================================
# RUTAS - CHAT
# =====================================================

@app.route('/')
def index():
    """Página principal del chat"""
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    """Enviar mensaje a Rasa y obtener respuesta"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', 'user')  # ✅ NUEVO: recibir session_id
        
        if not user_message:
            return jsonify({'error': 'Mensaje vacío'}), 400
        
        # ✅ NUEVO: Generar session_id si no existe
        if session_id == 'user':
            import uuid
            session_id = f"web_{uuid.uuid4().hex[:12]}"
        
        # Enviar a Rasa con session_id único
        rasa_response = requests.post(
            RASA_URL,
            json={'sender': session_id, 'message': user_message},  # ✅ CAMBIO: usar session_id
            timeout=10
        )
        
        if rasa_response.status_code == 200:
            bot_responses = rasa_response.json()
            
            # Extraer texto de respuestas
            responses_text = []
            for response in bot_responses:
                if 'text' in response:
                    responses_text.append(response['text'])
            
            bot_message = ' '.join(responses_text) if responses_text else "Lo siento, no pude procesar tu mensaje."
            
            # Log usando conversation_logger si está disponible
            if LOGGER_AVAILABLE:
                try:
                    log_interaction_improved(
                        user_message=user_message,
                        bot_response=bot_message,
                        intent="web_chat",
                        confidence=1.0
                    )
                except Exception as e:
                    logger.warning(f"No se pudo registrar en logger mejorado: {e}")
            
            return jsonify({
                'success': True,
                'bot_message': bot_message,
                'session_id': session_id,
                'timestamp': datetime.now().strftime('%H:%M')
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error al conectar con Rasa'
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Timeout al conectar con Rasa'
        }), 500
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/restart_conversation', methods=['POST'])
def restart_conversation():
    """Reiniciar conversación - generar nueva sesión"""
    try:
        import uuid
        
        # Generar nuevo session_id
        new_session_id = f"web_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"✅ Nueva sesión creada: {new_session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Conversación reiniciada',
            'session_id': new_session_id
        })
            
    except Exception as e:
        logger.error(f"Error en restart: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/feedback', methods=['POST'])
def feedback():
    """Guardar feedback del usuario"""
    try:
        data = request.json
        user_message = data.get('user_message', '')
        bot_response = data.get('bot_response', '')
        feedback_type = data.get('feedback_type', '')
        comment = data.get('comment', None)
        
        success = save_feedback(user_message, bot_response, feedback_type, comment)
        
        if success:
            return jsonify({
                'success': True,
                'message': '¡Gracias por tu feedback!'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error al guardar feedback'
            }), 500
            
    except Exception as e:
        logger.error(f"Error en feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# RUTAS - DASHBOARD
# =====================================================

@app.route('/dashboard')
def dashboard():
    """Página del dashboard de análisis"""
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """API para obtener estadísticas del dashboard"""
    try:
        stats = get_feedback_stats()
        
        if stats:
            return jsonify({
                'success': True,
                'stats': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudieron obtener estadísticas'
            }), 500
            
    except Exception as e:
        logger.error(f"Error en dashboard stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dashboard/negative-feedback', methods=['GET'])
def get_dashboard_negative_feedback():
    """API para obtener feedback negativo"""
    try:
        feedback_list = get_negative_feedback()
        
        return jsonify({
            'success': True,
            'feedback': feedback_list
        })
            
    except Exception as e:
        logger.error(f"Error en negative feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/dashboard/conversations', methods=['GET'])
def get_dashboard_conversations():
    """API para obtener conversaciones recientes"""
    try:
        limit = request.args.get('limit', 20, type=int)
        conversations = get_recent_conversations(limit)
        
        return jsonify({
            'success': True,
            'conversations': conversations
        })
            
    except Exception as e:
        logger.error(f"Error en conversations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# RUTAS - UTILIDADES
# =====================================================

@app.route('/health')
def health():
    """Verificar estado del servidor"""
    # Verificar conexión a Rasa
    rasa_status = False
    try:
        response = requests.get(RASA_STATUS_URL, timeout=2)
        rasa_status = response.status_code == 200
    except:
        pass
    
    # Verificar conexión a BD
    db_status = get_db_connection() is not None
    
    return jsonify({
        'status': 'ok' if (rasa_status and db_status) else 'degraded',
        'rasa': 'up' if rasa_status else 'down',
        'database': 'up' if db_status else 'down',
        'timestamp': datetime.now().isoformat()
    })


# =====================================================
# RUTAS - DASHBOARD AVANZADO CON GRÁFICOS
# =====================================================

@app.route('/api/dashboard/feedback-over-time', methods=['GET'])
def get_feedback_over_time():
    """Feedback a lo largo del tiempo (últimos 7 días)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Últimos 7 días con feedback_thumbs
        cursor.execute("""
            SELECT 
                DATE(timestamp) as fecha,
                SUM(CASE WHEN feedback_thumbs = 1 THEN 1 ELSE 0 END) as positivos,
                SUM(CASE WHEN feedback_thumbs = -1 THEN 1 ELSE 0 END) as negativos
            FROM conversation_messages
            WHERE feedback_thumbs IN (1, -1)
                AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(timestamp)
            ORDER BY fecha
        """)
        
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                'fecha': row[0].strftime('%Y-%m-%d') if row[0] else None,
                'positivos': row[1] or 0,
                'negativos': row[2] or 0
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Feedback over time: {len(data)} días")
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error en feedback over time: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/intents-distribution', methods=['GET'])
def get_intents_distribution():
    """Distribución de intents detectados (top 10)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Top 10 intents del último mes
        cursor.execute("""
            SELECT 
                COALESCE(intent_detected, 'Sin clasificar') as intent,
                COUNT(*) as count
            FROM conversation_messages
            WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY intent_detected
            ORDER BY count DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                'intent': row[0] or 'Sin clasificar',
                'count': row[1] or 0
            })
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Intents distribution: {len(data)} intents")
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error en intents distribution: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/confidence-stats', methods=['GET'])
def get_confidence_stats():
    """Estadísticas de confianza del modelo"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Estadísticas del último mes
        cursor.execute("""
            SELECT 
                AVG(COALESCE(confidence, 0)) as avg_confidence,
                MIN(COALESCE(confidence, 0)) as min_confidence,
                MAX(COALESCE(confidence, 0)) as max_confidence,
                COUNT(CASE WHEN confidence < 0.5 THEN 1 END) as low_confidence_count,
                COUNT(*) as total_messages
            FROM conversation_messages
            WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
        """)
        
        result = cursor.fetchone()
        
        stats = {
            'avg_confidence': round(result[0], 2) if result[0] else 0,
            'min_confidence': round(result[1], 2) if result[1] else 0,
            'max_confidence': round(result[2], 2) if result[2] else 0,
            'low_confidence_count': result[3] or 0,
            'total_messages': result[4] or 0
        }
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Confidence stats calculadas")
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error en confidence stats: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/messages-per-hour', methods=['GET'])
def get_messages_per_hour():
    """Mensajes por hora del día"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                EXTRACT(HOUR FROM timestamp) as hora,
                COUNT(*) as cantidad
            FROM conversation_messages
            WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY EXTRACT(HOUR FROM timestamp)
            ORDER BY hora
        """)
        
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                'hora': int(row[0]) if row[0] else 0,
                'cantidad': row[1] or 0
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error en messages per hour: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/needs-review', methods=['GET'])
def get_needs_review():
    """Mensajes que necesitan revisión"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_message,
                bot_response,
                intent_detected,
                confidence,
                timestamp
            FROM conversation_messages
            WHERE needs_review = TRUE
                AND reviewed = FALSE
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                'user_message': row[0],
                'bot_response': row[1],
                'intent': row[2],
                'confidence': round(row[3], 2) if row[3] else 0,
                'timestamp': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error en needs review: {e}")
        if conn:
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
    
# =====================================================
# EJECUTAR APP
# =====================================================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Iniciando Flask Chatbot COMPLETO")
    logger.info("=" * 60)
    logger.info(f"📍 Chat: http://localhost:5000")
    logger.info(f"📊 Dashboard: http://localhost:5000/dashboard")
    logger.info(f"💬 Rasa URL: {RASA_URL}")
    logger.info(f"🗄️  Database: {DB_CONFIG['database']}")
    logger.info("=" * 60)
    
    # Inicializar sistema de logging si está disponible
    if LOGGER_AVAILABLE:
        try:
            setup_improved_logging_system()
            logger.info("✅ Sistema de logging mejorado inicializado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo inicializar logging mejorado: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
