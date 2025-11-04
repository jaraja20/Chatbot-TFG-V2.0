"""
Script para verificar que los filtros de mensajes funcionan correctamente
"""

import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("="*80)
    print("🔍 VERIFICACIÓN DE FILTROS DE MENSAJES")
    print("="*80)
    
    # Contar mensajes totales
    cursor.execute("SELECT COUNT(*) FROM conversation_messages")
    total_antes = cursor.fetchone()[0]
    print(f"\n📊 Total de mensajes actuales: {total_antes}")
    
    # Últimos 10 mensajes
    print("\n📋 ÚLTIMOS 10 MENSAJES REGISTRADOS:")
    print("-"*80)
    
    cursor.execute("""
        SELECT 
            user_message,
            intent_detected,
            confidence,
            timestamp
        FROM conversation_messages
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    mensajes = cursor.fetchall()
    
    for idx, (msg, intent, conf, ts) in enumerate(mensajes, 1):
        intent_display = intent if intent else "(sin intent)"
        conf_display = f"{conf:.2%}" if conf else "0.00%"
        print(f"{idx}. [{conf_display}] [{intent_display}] {msg[:60]}")
    
    # Verificar si hay mensajes "Inicio de sesión" nuevos
    print("\n" + "="*80)
    print("🔍 VERIFICANDO MENSAJES FILTRADOS")
    print("="*80)
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM conversation_messages 
        WHERE user_message = 'Inicio de sesión'
    """)
    inicio_sesion = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM conversation_messages 
        WHERE (intent_detected IS NULL OR intent_detected = '')
        AND confidence = 0
    """)
    sin_intent = cursor.fetchone()[0]
    
    print(f"\n✅ Mensajes 'Inicio de sesión': {inicio_sesion}")
    print(f"✅ Mensajes sin intent y conf=0: {sin_intent}")
    
    if inicio_sesion == 0 and sin_intent == 0:
        print("\n🎉 ¡PERFECTO! Los filtros están funcionando correctamente.")
        print("   No se están guardando mensajes automáticos.")
    else:
        print(f"\n⚠️  Hay {inicio_sesion + sin_intent} mensajes que deberían haberse filtrado.")
        print("   Pueden ser mensajes antiguos de antes de aplicar los filtros.")
    
    # Instrucciones de prueba
    print("\n" + "="*80)
    print("🧪 CÓMO PROBAR:")
    print("="*80)
    print("1. Abre el chat en tu navegador (http://localhost:5000)")
    print("2. Escribe varios mensajes normales (ej: 'hola', 'quiero un turno')")
    print("3. Cierra y vuelve a abrir el chat")
    print("4. Ejecuta este script de nuevo")
    print("5. Verifica que:")
    print("   - Solo se guardaron tus mensajes reales")
    print("   - NO hay mensajes 'Inicio de sesión'")
    print("   - NO hay mensajes con confidence=0 e intent vacío")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
