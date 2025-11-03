"""
Flask Chatbot COMPLETO - Sistema de Turnos Cédulas
Incluye: Chat + Dashboard + Logging + ORQUESTADOR INTELIGENTE
Ciudad del Este
"""

from flask import Flask, render_template, request, jsonify, session
import requests
import psycopg2
from datetime import datetime
from orquestador_inteligente import procesar_mensaje_inteligente
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


ORQUESTADOR_DISPONIBLE = True
logger.info("✅ Orquestador HABILITADO - Usando Llama 3.1 con contexto completo del proyecto")


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

# =====================================================
# ✨ RUTA MODIFICADA: /send_message CON ORQUESTADOR
# =====================================================

@app.route('/send_message', methods=['POST'])
def send_message():
    """Enviar mensaje con procesamiento inteligente"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', None)
        
        if not user_message:
            return jsonify({'error': 'Mensaje vacío'}), 400
        
        # Generar session_id si no existe o es None
        if not session_id or session_id == 'user':
            import uuid
            session_id = f"web_{uuid.uuid4().hex[:12]}"
            logger.info(f"🆕 Nuevo session_id generado: {session_id}")
        
        # =====================================================
        # ✨ NUEVO: USAR ORQUESTADOR INTELIGENTE
        # =====================================================
        
        if ORQUESTADOR_DISPONIBLE:
            logger.info(f"🧠 Procesando con Orquestador: '{user_message[:30]}...'")
            
            try:
                # Procesar con sistema inteligente
                resultado = procesar_mensaje_inteligente(user_message, session_id)
                
                bot_message = resultado['text']
                intent_detectado = resultado.get('intent', 'unknown')
                confidence = resultado.get('confidence', 0.0)
                
                logger.info(f"✅ Respuesta generada | Intent: {intent_detectado} | Conf: {confidence:.2f}")
                
                # Log mejorado
                if LOGGER_AVAILABLE:
                    try:
                        log_interaction_improved(
                            session_id=session_id,
                            user_message=user_message,
                            bot_response=bot_message,
                            intent_name=intent_detectado,
                            confidence=confidence
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Error en logger: {e}")
                
                return jsonify({
                    'success': True,
                    'bot_message': bot_message,
                    'session_id': session_id,
                    'timestamp': datetime.now().strftime('%H:%M'),
                    'metadata': {
                        'intent': intent_detectado,
                        'confidence': confidence,
                        'powered_by': 'orquestador_inteligente'
                    }
                })
                
            except Exception as orch_error:
                logger.error(f"❌ Error en orquestador: {orch_error}")
                logger.info("⚠️ Cayendo a sistema Rasa tradicional")
                # Continuar con fallback abajo
        
        # =====================================================
        # FALLBACK: Sistema anterior (Rasa solo)
        # =====================================================
        
        logger.info(f"📨 Usando Rasa tradicional para: '{user_message[:30]}...'")
        
        # Enviar a Rasa
        rasa_response = requests.post(
            RASA_URL,
            json={'sender': session_id, 'message': user_message},
            timeout=10
        )
        
        if rasa_response.status_code == 200:
            bot_responses = rasa_response.json()
            
            responses_text = []
            for response in bot_responses:
                if 'text' in response:
                    responses_text.append(response['text'])
            
            bot_message = ' '.join(responses_text) if responses_text else \
                          "Lo siento, no pude procesar tu mensaje."
            
            # Log
            if LOGGER_AVAILABLE:
                try:
                    log_interaction_improved(
                        session_id=session_id,
                        user_message=user_message,
                        bot_response=bot_message,
                        intent_name="rasa_traditional",
                        confidence=0.8
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Error en logger: {e}")
            
            return jsonify({
                'success': True,
                'bot_message': bot_message,
                'session_id': session_id,
                'timestamp': datetime.now().strftime('%H:%M'),
                'metadata': {
                    'powered_by': 'rasa_traditional'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error al conectar con Rasa'
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Timeout al conectar con el sistema'
        }), 500
        
    except Exception as e:
        logger.error(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================
# RUTA ORIGINAL: /restart_conversation
# =====================================================

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

# =====================================================
# RUTA ORIGINAL: /feedback
# =====================================================

@app.route('/feedback', methods=['POST'])
def feedback():
    """Guardar feedback del usuario"""
    try:
        data = request.json
        
        user_message = data.get('user_message', '')
        bot_response = data.get('bot_response', '')
        feedback_type = data.get('feedback_type', '')
        comment = data.get('comment', None)
        
        if not user_message or not bot_response or not feedback_type:
            return jsonify({
                'success': False,
                'error': 'Faltan datos requeridos'
            }), 400
        
        success = save_feedback(user_message, bot_response, feedback_type, comment)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Feedback guardado correctamente'
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
    """Página del dashboard"""
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Obtener estadísticas generales"""
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

@app.route('/api/dashboard/negative-feedback')
def get_negative_feedback():
    """Obtener feedback negativo - CORREGIDO para campo 'reviewed'"""
    conn = get_db_connection()
    if not conn:
        return jsonify([]), 200
    
    try:
        cursor = conn.cursor()
        
        # Query correcto con campo 'reviewed' en lugar de 'resolved'
        query = """
        SELECT id, user_message, bot_response, feedback_comment, timestamp, reviewed
        FROM conversation_messages
        WHERE feedback_thumbs = -1
        ORDER BY reviewed ASC, timestamp DESC
        LIMIT 50
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        feedback_list = []
        for row in results:
            feedback_list.append({
                'id': row[0],
                'user_message': row[1],
                'bot_response': row[2],
                'feedback_comment': row[3],
                'timestamp': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None,
                'resolved': row[5] if len(row) > 5 and row[5] is not None else False
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(feedback_list)
        
    except Exception as e:
        logger.error(f"Error obteniendo feedback negativo: {e}")
        if conn:
            conn.close()
        return jsonify([]), 200

@app.route('/api/dashboard/conversations')
def get_conversations():
    """Obtener conversaciones recientes - CORREGIDO"""
    conn = get_db_connection()
    if not conn:
        return jsonify([]), 200
    
    try:
        cursor = conn.cursor()
        
        query = """
        SELECT user_message, bot_response, timestamp, feedback_thumbs
        FROM conversation_messages
        ORDER BY timestamp DESC
        LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        conversations = []
        for row in results:
            feedback_type = 'positive' if row[3] == 1 else 'negative' if row[3] == -1 else 'none'
            
            conversations.append({
                'user_message': row[0],
                'bot_response': row[1],
                'timestamp': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else None,
                'feedback_type': feedback_type
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(conversations)
        
    except Exception as e:
        logger.error(f"Error obteniendo conversaciones: {e}")
        if conn:
            conn.close()
        return jsonify([]), 200

# =====================================================
# APIs DASHBOARD - GRÁFICOS
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
# ✨ NUEVAS RUTAS: DEBUG (OPCIONAL)
# =====================================================

@app.route('/api/debug/context/<session_id>', methods=['GET'])
def debug_context(session_id):
    """Ver el contexto actual de una sesión (solo para desarrollo)"""
    if not ORQUESTADOR_DISPONIBLE:
        return jsonify({'error': 'Orquestador no disponible'}), 503
    
    try:
        from orquestador_inteligente import SESSION_CONTEXTS
        
        if session_id in SESSION_CONTEXTS:
            context = SESSION_CONTEXTS[session_id]
            return jsonify({
                'session_id': session_id,
                'context': context.to_dict(),
                'historial_length': len(context.conversacion_historial),
                'ultimo_mensaje': context.ultimo_mensaje
            })
        else:
            return jsonify({'error': 'Sesión no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/fuzzy/<fecha>', methods=['GET'])
def debug_fuzzy(fecha):
    """Ver análisis difuso para una fecha (formato: YYYY-MM-DD)"""
    try:
        from motor_difuso import analizar_disponibilidad_dia
        from datetime import datetime
        
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        analisis = analizar_disponibilidad_dia(fecha_obj)
        
        return jsonify({
            'fecha': fecha,
            'analisis': analisis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/debug/status', methods=['GET'])
def debug_status():
    """Ver estado de todos los componentes"""
    status = {
        'orquestador': ORQUESTADOR_DISPONIBLE,
        'logger': LOGGER_AVAILABLE,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Verificar LLM
    try:
        from llm_classifier import LLMIntentClassifier
        classifier = LLMIntentClassifier()
        status['llm'] = classifier.available
    except:
        status['llm'] = False
    
    # Verificar Rasa
    try:
        response = requests.get(RASA_STATUS_URL, timeout=2)
        status['rasa'] = response.status_code == 200
    except:
        status['rasa'] = False
    
    # Verificar BD
    try:
        conn = get_db_connection()
        status['database'] = conn is not None
        if conn:
            conn.close()
    except:
        status['database'] = False
    
    return jsonify(status)

# =====================================================
# ✨ NUEVA RUTA: Guardar corrección manual del usuario
# =====================================================
@app.route('/save_correction', methods=['POST'])
def save_correction():
    """Guarda una corrección manual del usuario hacia el bot"""
    try:
        from conversation_logger import save_user_correction

        data = request.json
        session_id = data.get('session_id')
        user_message = data.get('user_message')
        bot_response = data.get('bot_response')
        corrected_response = data.get('corrected_response')

        if not all([session_id, user_message, bot_response, corrected_response]):
            return jsonify({
                "success": False,
                "error": "Faltan campos requeridos"
            }), 400

        save_user_correction(session_id, user_message, bot_response, corrected_response)

        return jsonify({
            "success": True,
            "message": "Corrección guardada correctamente"
        })

    except Exception as e:
        logger.error(f"❌ Error guardando corrección: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =====================================================
# NUEVOS ENDPOINTS PARA DASHBOARD MEJORADO
# =====================================================

@app.route('/api/dashboard/performance', methods=['GET'])
def get_performance_metrics():
    """Obtener métricas de rendimiento del bot - CORREGIDO"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    try:
        cursor = conn.cursor()
        
        # 1. Confianza promedio
        cursor.execute("""
            SELECT AVG(confidence), COUNT(*) as total
            FROM conversation_messages
            WHERE confidence IS NOT NULL
        """)
        conf_result = cursor.fetchone()
        avg_confidence = conf_result[0] if conf_result and conf_result[0] else 0.0
        total_interactions = conf_result[1] if conf_result else 0
        
        # 2. Tasa de fallback - CORREGIDO: usa intent_detected
        cursor.execute("""
            SELECT COUNT(*) as fallback_count
            FROM conversation_messages
            WHERE intent_detected IN ('nlu_fallback', 'out_of_scope')
        """)
        fallback_result = cursor.fetchone()
        fallback_count = fallback_result[0] if fallback_result else 0
        fallback_rate = fallback_count / total_interactions if total_interactions > 0 else 0
        
        # 3. Tasa de éxito (confianza > 0.7)
        cursor.execute("""
            SELECT COUNT(*) as success_count
            FROM conversation_messages
            WHERE confidence > 0.7
        """)
        success_result = cursor.fetchone()
        success_count = success_result[0] if success_result else 0
        success_rate = success_count / total_interactions if total_interactions > 0 else 0
        
        # 4. Top 10 intents más usados - CORREGIDO: usa intent_detected
        cursor.execute("""
            SELECT 
                intent_detected as intent_name, 
                COUNT(*) as count,
                AVG(confidence) as avg_confidence
            FROM conversation_messages
            WHERE intent_detected IS NOT NULL AND intent_detected != ''
            GROUP BY intent_detected
            ORDER BY count DESC
            LIMIT 10
        """)
        top_intents = []
        for row in cursor.fetchall():
            top_intents.append({
                'intent_name': row[0],
                'count': row[1],
                'avg_confidence': float(row[2]) if row[2] else 0.0
            })
        
        # 5. Distribución de confianza
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN confidence >= 0.9 THEN 1 END) as high,
                COUNT(CASE WHEN confidence >= 0.75 AND confidence < 0.9 THEN 1 END) as medium_high,
                COUNT(CASE WHEN confidence >= 0.6 AND confidence < 0.75 THEN 1 END) as medium,
                COUNT(CASE WHEN confidence < 0.6 THEN 1 END) as low
            FROM conversation_messages
            WHERE confidence IS NOT NULL
        """)
        dist_result = cursor.fetchone()
        confidence_distribution = {
            'high': dist_result[0] if dist_result else 0,
            'medium_high': dist_result[1] if dist_result else 0,
            'medium': dist_result[2] if dist_result else 0,
            'low': dist_result[3] if dist_result else 0
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'avg_confidence': float(avg_confidence),
            'total_interactions': total_interactions,
            'fallback_rate': float(fallback_rate),
            'success_rate': float(success_rate),
            'top_intents': top_intents,
            'confidence_distribution': confidence_distribution
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/feedback/<int:feedback_id>/resolve', methods=['POST'])
def mark_feedback_resolved(feedback_id):
    """Marcar feedback como resuelto - CORREGIDO para campo 'reviewed'"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Error de conexión a BD'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Actualizar campo 'reviewed' (no 'resolved')
        cursor.execute("""
            UPDATE conversation_messages
            SET reviewed = TRUE
            WHERE id = %s
        """, (feedback_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Feedback marcado como resuelto'
        })
        
    except Exception as e:
        logger.error(f"Error marcando como resuelto: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

# =====================================================
# EJECUTAR APP
# =====================================================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Iniciando Flask Chatbot COMPLETO + ORQUESTADOR")
    logger.info("=" * 60)
    logger.info(f"📍 Chat: http://localhost:5000")
    logger.info(f"📊 Dashboard: http://localhost:5000/dashboard")
    logger.info(f"💬 Rasa URL: {RASA_URL}")
    logger.info(f"🗄️  Database: {DB_CONFIG['database']}")
    
    # Status de componentes
    logger.info("")
    logger.info("🔧 COMPONENTES:")
    logger.info(f"   {'✅' if LOGGER_AVAILABLE else '❌'} Logger mejorado")
    logger.info(f"   {'✅' if ORQUESTADOR_DISPONIBLE else '❌'} Orquestador inteligente")
    
    if ORQUESTADOR_DISPONIBLE:
        logger.info("   🧠 Modo: INTELIGENTE (LLM + Motor Difuso + Rasa)")
    else:
        logger.info("   📨 Modo: TRADICIONAL (Solo Rasa)")
    
    logger.info("")
    logger.info("🐛 DEBUG ENDPOINTS:")
    logger.info("   http://localhost:5000/api/debug/status")
    logger.info("   http://localhost:5000/api/debug/context/<session_id>")
    logger.info("   http://localhost:5000/api/debug/fuzzy/2025-10-24")
    logger.info("=" * 60)
    
    # Inicializar sistema de logging si está disponible
    if LOGGER_AVAILABLE:
        try:
            setup_improved_logging_system("postgresql+psycopg2://botuser:root@localhost/chatbotdb")

            logger.info("✅ Sistema de logging mejorado inicializado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo inicializar logging mejorado: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
    
    
# =====================================================
# 🧠 API - Correcciones de Usuario
# =====================================================

@app.route('/api/dashboard/user-corrections')
def get_user_corrections():
    import psycopg2
    import json

    conn = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="chatbotdb",
            user="botuser",
            password="root"
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT id, session_id, user_message, bot_response, corrected_response, created_at
            FROM feedback_training_data
            ORDER BY created_at DESC
            LIMIT 50;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = []
        for r in rows:
            data.append({
                "id": r[0],
                "session_id": r[1],
                "user_message": r[2],
                "bot_response": r[3],
                "corrected_response": r[4],
                "timestamp": r[5].strftime("%Y-%m-%d %H:%M:%S")
            })

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        if conn:
            conn.close()
        return {
            "success": False,
            "error": str(e)
        }