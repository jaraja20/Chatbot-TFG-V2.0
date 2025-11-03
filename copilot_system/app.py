from flask import Flask, send_from_directory, render_template_string
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def index():
    with open(os.path.join(BASE_DIR, 'index.html'), encoding='utf-8') as f:
        return render_template_string(f.read())

@app.route('/style.css')
def style():
    return send_from_directory(BASE_DIR, 'style.css')

@app.route('/chat.js')
def chat_js():
    return send_from_directory(BASE_DIR, 'chat.js')

if __name__ == '__main__':
    app.run(port=5010, debug=True)
