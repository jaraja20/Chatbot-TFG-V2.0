"""
Simple assistant backend for the demo frontend.
This backend is independent from the main project and provides simple, friendly responses.
Run with: python simple_backend.py
Listens on http://127.0.0.1:5020
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app)


def simple_reply(message: str) -> str:
    m = (message or "").strip().lower()
    if not m:
        return "No recibí ningún mensaje. Escribí algo y te respondo."
    if any(g in m for g in ["hola", "buenas", "buen", "hi"]):
        return "¡Hola! 👋 Soy tu asistente de prueba. Escribime lo que quieras."
    if "cómo estás" in m or "como estas" in m:
        return "Estoy bien, gracias. ¿Y vos?"
    if "gracias" in m or "thank" in m:
        return "De nada — para eso estoy. ¿Querés probar otra cosa?"
    # Simple echo with timestamp to show it's the demo assistant
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    return f"Asistente (demo) — {now}: Recibí tu mensaje: \"{message}\""


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    message = data.get('message') if data else None
    session_id = data.get('session_id') if data else None
    # Generate a simple response
    response_text = simple_reply(message)
    return jsonify({'response': response_text, 'session_id': session_id})


if __name__ == '__main__':
    app.run(port=5020, debug=True)
