"""
Script de prueba para verificar la configuración de la API
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Verificando configuración de API...")
print()

openai_key = os.getenv('OPENAI_API_KEY', '')
github_token = os.getenv('GITHUB_TOKEN', '')

if openai_key:
    print(f"✅ OPENAI_API_KEY configurada")
    print(f"   Primeros caracteres: {openai_key[:20]}...")
    print(f"   Longitud: {len(openai_key)} caracteres")
else:
    print("❌ OPENAI_API_KEY NO configurada")

print()

if github_token:
    print(f"✅ GITHUB_TOKEN configurado")
    print(f"   Primeros caracteres: {github_token[:20]}...")
else:
    print("ℹ️  GITHUB_TOKEN no configurado (opcional)")

print()
print("📊 Estado del sistema:")
print(f"   Archivo .env existe: {os.path.exists('.env')}")
print()

if openai_key or github_token:
    print("🎉 ¡Configuración correcta! El sistema usará API REAL")
else:
    print("⚠️  Sin API configurada - usará respuestas simuladas")
