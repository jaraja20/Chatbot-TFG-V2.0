"""
Adaptador para el frontend para usar GitHub Copilot
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from copilot_handler import procesar_mensaje_copilot
import logging

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        logger.info("📩 Recibida petición de chat")
        data = request.json
        mensaje = data.get('message')
        session_id = data.get('session_id', 'default')
        
        logger.info(f"💬 Mensaje: {mensaje}")
        logger.info(f"🆔 Session ID: {session_id}")
        
        # Procesar mensaje con Copilot
        respuesta = procesar_mensaje_copilot(mensaje, session_id)
        
        logger.info(f"✅ Respuesta generada: {respuesta}")
        
        return jsonify({
            'response': respuesta.get('response'),
            'data': respuesta
        })
        
    except Exception as e:
        logger.error(f"Error en el endpoint de chat: {e}")
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(port=5001)  # Puerto diferente para no conflictuar con el existente