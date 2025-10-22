"""
🧪 TEST COMPLETO DEL SISTEMA DE FEEDBACK
Script para verificar que todo el flujo funcione correctamente

EJECUTAR: python test_feedback_system.py
"""

import requests
import psycopg2
import time
import json
from datetime import datetime

# =====================================================
# CONFIGURACIÓN
# =====================================================
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# Crear un session_id único para este test
TEST_SESSION_ID = f"test_session_{int(time.time())}"

print("="*70)
print("🧪 TEST DEL SISTEMA DE FEEDBACK")
print("="*70)
print(f"\n📋 Session ID de prueba: {TEST_SESSION_ID}\n")

# =====================================================
# PASO 1: ENVIAR MENSAJE A RASA
# =====================================================
print("📤 PASO 1: Enviando mensaje a Rasa...")
print("-"*70)

payload = {
    "sender": TEST_SESSION_ID,
    "message": "Hola, quiero un turno de prueba"
}

try:
    response = requests.post(RASA_URL, json=payload, timeout=10)
    if response.status_code == 200:
        bot_responses = response.json()
        if bot_responses:
            bot_message = bot_responses[0].get('text', '')
            print(f"✅ Respuesta de Rasa recibida:")
            print(f"   {bot_message[:100]}...")
        else:
            print("⚠️ Rasa respondió pero sin texto")
            bot_message = "Respuesta vacía"
    else:
        print(f"❌ Error: Rasa respondió con código {response.status_code}")
        bot_message = None
except Exception as e:
    print(f"❌ Error conectando con Rasa: {e}")
    bot_message = None

if not bot_message:
    print("\n❌ No se pudo obtener respuesta de Rasa. Asegúrate de que esté corriendo.")
    exit(1)

# Esperar a que se guarde en BD
print("\n⏳ Esperando 2 segundos para que se guarde en BD...")
time.sleep(2)

# =====================================================
# PASO 2: VERIFICAR EN BASE DE DATOS
# =====================================================
print("\n📊 PASO 2: Verificando en base de datos...")
print("-"*70)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Buscar el mensaje guardado
    cursor.execute("""
        SELECT 
            id, session_id, user_message, bot_response,
            intent_detected, confidence, feedback_thumbs, feedback_comment
        FROM conversation_messages
        WHERE session_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
    """, (TEST_SESSION_ID,))
    
    result = cursor.fetchone()
    
    if result:
        msg_id, session_id, user_msg, bot_resp, intent, confidence, feedback_thumbs, feedback_comment = result
        print(f"✅ Mensaje encontrado en BD:")
        print(f"   ID: {msg_id}")
        print(f"   Session ID: {session_id}")
        print(f"   Usuario: {user_msg}")
        print(f"   Bot: {bot_resp[:60]}...")
        print(f"   Intent: {intent}")
        print(f"   Confianza: {confidence}")
        print(f"   Feedback: {feedback_thumbs}")
    else:
        print(f"❌ No se encontró mensaje con session_id: {TEST_SESSION_ID}")
        print("\n🔍 Verificando otros mensajes recientes...")
        cursor.execute("""
            SELECT id, session_id, user_message, timestamp
            FROM conversation_messages
            ORDER BY timestamp DESC
            LIMIT 3
        """)
        recent = cursor.fetchall()
        for row in recent:
            print(f"   - ID {row[0]}: session_id='{row[1]}', msg='{row[2][:30]}...', time={row[3]}")
        
        cursor.close()
        conn.close()
        print("\n❌ El mensaje no se guardó correctamente. Verifica el logger en actions.py")
        exit(1)
    
    # =====================================================
    # PASO 3: SIMULAR FEEDBACK NEGATIVO
    # =====================================================
    print("\n👎 PASO 3: Simulando feedback negativo...")
    print("-"*70)
    
    test_comment = "Esta es una prueba de feedback negativo desde el script de testing"
    
    # Actualizar feedback
    cursor.execute("""
        UPDATE conversation_messages
        SET feedback_thumbs = -1,
            feedback_comment = %s,
            needs_review = TRUE
        WHERE id = %s
    """, (test_comment, msg_id))
    
    conn.commit()
    
    # Verificar que se actualizó
    cursor.execute("""
        SELECT feedback_thumbs, feedback_comment, needs_review
        FROM conversation_messages
        WHERE id = %s
    """, (msg_id,))
    
    updated = cursor.fetchone()
    if updated and updated[0] == -1:
        print(f"✅ Feedback actualizado correctamente:")
        print(f"   Thumbs: {updated[0]} (👎)")
        print(f"   Comentario: {updated[1]}")
        print(f"   Needs Review: {updated[2]}")
    else:
        print("❌ El feedback no se actualizó")
        cursor.close()
        conn.close()
        exit(1)
    
    # =====================================================
    # PASO 4: VERIFICAR EN DASHBOARD
    # =====================================================
    print("\n📊 PASO 4: Verificando datos para el dashboard...")
    print("-"*70)
    
    # 4.1: Mensajes con feedback negativo
    cursor.execute("""
        SELECT COUNT(*) 
        FROM conversation_messages
        WHERE feedback_thumbs = -1
    """)
    negative_count = cursor.fetchone()[0]
    print(f"📋 Total mensajes con feedback negativo: {negative_count}")
    
    # 4.2: Contextos capturados
    cursor.execute("""
        SELECT COUNT(*)
        FROM conversation_context_enhanced
    """)
    context_count = cursor.fetchone()[0]
    print(f"🔍 Total contextos problemáticos capturados: {context_count}")
    
    # 4.3: Estadísticas del sistema
    cursor.execute("""
        SELECT 
            date, 
            total_messages, 
            needs_review_count,
            positive_feedback,
            negative_feedback
        FROM system_stats
        ORDER BY date DESC
        LIMIT 1
    """)
    stats = cursor.fetchone()
    if stats:
        print(f"📈 Estadísticas de hoy:")
        print(f"   Fecha: {stats[0]}")
        print(f"   Total mensajes: {stats[1]}")
        print(f"   Necesitan revisión: {stats[2]}")
        print(f"   Feedback positivo: {stats[3]}")
        print(f"   Feedback negativo: {stats[4]}")
    
    # =====================================================
    # PASO 5: SIMULAR CONSULTA DEL DASHBOARD
    # =====================================================
    print("\n📊 PASO 5: Simulando consultas del dashboard...")
    print("-"*70)
    
    # Consulta de mensajes con feedback negativo (como lo hace el dashboard)
    cursor.execute("""
        SELECT 
            cm.id,
            cm.session_id,
            cm.user_message,
            cm.bot_response,
            cm.feedback_comment,
            cm.intent_detected,
            cm.confidence,
            cm.timestamp
        FROM conversation_messages cm
        WHERE cm.feedback_thumbs = -1
        ORDER BY cm.timestamp DESC
        LIMIT 5
    """)
    
    negative_feedback_messages = cursor.fetchall()
    
    print(f"\n🎯 Dashboard - Pestaña 'Feedback Negativo':")
    print(f"   Encontrados: {len(negative_feedback_messages)} mensajes")
    
    if negative_feedback_messages:
        for i, msg in enumerate(negative_feedback_messages, 1):
            print(f"\n   Mensaje {i}:")
            print(f"      ID: {msg[0]}")
            print(f"      Usuario: {msg[2]}")
            print(f"      Bot: {msg[3][:50]}...")
            print(f"      Comentario: {msg[4]}")
            print(f"      Intent: {msg[5]} (confianza: {msg[6]:.2f})")
        
        print("\n✅ ÉXITO: El dashboard debería mostrar estos mensajes")
    else:
        print("\n⚠️ No hay mensajes con feedback negativo para mostrar")
    
    cursor.close()
    conn.close()
    
    # =====================================================
    # RESUMEN FINAL
    # =====================================================
    print("\n" + "="*70)
    print("📋 RESUMEN DEL TEST")
    print("="*70)
    print(f"✅ Mensaje enviado a Rasa con session_id: {TEST_SESSION_ID}")
    print(f"✅ Mensaje guardado en BD (ID: {msg_id})")
    print(f"✅ Feedback negativo aplicado correctamente")
    print(f"✅ Datos disponibles para el dashboard")
    print("\n🎯 PRÓXIMOS PASOS:")
    print("   1. Abre el dashboard de Streamlit")
    print("   2. Ve a la pestaña 'Feedback Negativo'")
    print("   3. Deberías ver el mensaje de prueba con el comentario")
    print(f"\n💡 Para ver este mensaje específico en pgAdmin:")
    print(f"   SELECT * FROM conversation_messages WHERE id = {msg_id};")
    print("\n" + "="*70)

except psycopg2.Error as e:
    print(f"❌ Error de base de datos: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    exit(1)