"""
Flask Chatbot - Sistema de Turnos Cédulas
Ciudad del Este
"""

from flask import Flask, render_template, request, jsonify
import requests
import psycopg2
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui'

# Configuración
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# =====================================================
# FUNCIONES DE BASE DE DATOS
# =====================================================

def get_db_connection():
    """Conexión a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error conectando a BD: {e}")
        return None

def save_feedback(user_message, bot_response, feedback_type, comment=None):
    """Guardar feedback en la BD"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        query = """
        INSERT INTO conversation_messages 
        (user_message, bot_response, feedback_type, feedback_comment, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            user_message,
            bot_response,
            feedback_type,
            comment,
            datetime.now()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error guardando feedback: {e}")
        if conn:
            conn.close()
        return False

# =====================================================
# RUTAS
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
        
        if not user_message:
            return jsonify({'error': 'Mensaje vacío'}), 400
        
        # Enviar a Rasa
        rasa_response = requests.post(
            RASA_URL,
            json={'sender': 'user', 'message': user_message},
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
            
            return jsonify({
                'success': True,
                'bot_message': bot_message,
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
        print(f"Error: {e}")
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
        feedback_type = data.get('feedback_type', '')  # 'positive' o 'negative'
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
        print(f"Error en feedback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Verificar estado del servidor"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

# =====================================================
# EJECUTAR APP
# =====================================================

if __name__ == '__main__':
    print("🚀 Iniciando Flask Chatbot...")
    print("📍 URL: http://localhost:5000")
    print("💬 Rasa URL:", RASA_URL)
    app.run(debug=True, host='0.0.0.0', port=5000)
