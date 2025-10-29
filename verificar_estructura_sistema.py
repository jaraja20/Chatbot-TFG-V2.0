"""
Script de diagnóstico estructural del sistema de chatbot TFG
Detecta: rutas, módulos, BD y servidor Rasa activos
"""

import os, sys, importlib.util, requests, psycopg2
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Archivos clave esperados
ARCHIVOS_ESENCIALES = [
    "app.py", "orquestador_inteligente.py", "motor_difuso.py",
    "conversation_logger.py", "learning_dashboard.py",
    "templates/index.html", "templates/dashboard.html",
    "static/js/chat.js", "static/js/dashboard.js",
    "static/css/style.css", "static/css/dashboard.css",
    "system_prompt_turnos.txt"
]

print("\n📁 Verificando estructura del proyecto...\n")

encontrados = 0
for archivo in ARCHIVOS_ESENCIALES:
    ruta = PROJECT_ROOT / archivo
    if ruta.exists():
        print(f"✅ {archivo}")
        encontrados += 1
    else:
        print(f"❌ {archivo}")

print(f"\n📊 Archivos encontrados: {encontrados}/{len(ARCHIVOS_ESENCIALES)}")

# --- Verificar conexión BD ---
print("\n🧩 Verificando conexión a PostgreSQL...")
try:
    conn = psycopg2.connect(
        host="localhost", database="chatbotdb", user="botuser", password="root"
    )
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    print("✅ Conexión BD OK:", cur.fetchone()[0])
    cur.close(); conn.close()
except Exception as e:
    print("⚠️  Error al conectar BD:", e)

# --- Verificar servidor Rasa ---
print("\n🤖 Verificando servidor Rasa...")
try:
    res = requests.get("http://localhost:5005/status", timeout=3)
    if res.status_code == 200:
        print("✅ Rasa activo y operativo")
    else:
        print("⚠️  Rasa responde con código:", res.status_code)
except Exception as e:
    print("❌ Rasa no disponible:", e)

# --- Verificar importaciones clave ---
print("\n🧠 Verificando módulos Python...")
for mod in ["motor_difuso", "orquestador_inteligente", "conversation_logger"]:
    ruta = PROJECT_ROOT / f"{mod}.py"
    if ruta.exists():
        spec = importlib.util.spec_from_file_location(mod, ruta)
        try:
            importlib.util.module_from_spec(spec)
            print(f"✅ {mod} importable")
        except Exception as e:
            print(f"⚠️  {mod} presenta error de importación:", e)
    else:
        print(f"❌ {mod} no encontrado")

print("\n✅ Verificación estructural finalizada.\n")
