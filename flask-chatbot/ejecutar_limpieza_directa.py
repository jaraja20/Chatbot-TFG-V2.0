"""
Script directo para limpiar mensajes - SIN confirmación interactiva
"""

import psycopg2

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
    print("🧹 EJECUTANDO LIMPIEZA DE DATOS")
    print("="*80)
    
    # Antes
    cursor.execute("SELECT COUNT(*) FROM conversation_messages")
    total_antes = cursor.fetchone()[0]
    print(f"\n📊 Mensajes ANTES: {total_antes}")
    
    # Eliminar "Inicio de sesión"
    cursor.execute("DELETE FROM conversation_messages WHERE user_message = 'Inicio de sesión'")
    del1 = cursor.rowcount
    print(f"✅ Eliminados 'Inicio de sesión': {del1}")
    
    # Eliminar intent 'error'
    cursor.execute("DELETE FROM conversation_messages WHERE intent_detected = 'error'")
    del2 = cursor.rowcount
    print(f"✅ Eliminados intent 'error': {del2}")
    
    # Eliminar NULL con confidence 0
    cursor.execute("""
        DELETE FROM conversation_messages 
        WHERE (intent_detected IS NULL OR intent_detected = '')
        AND confidence = 0
    """)
    del3 = cursor.rowcount
    print(f"✅ Eliminados NULL/vacíos: {del3}")
    
    # COMMIT
    conn.commit()
    print("\n✅ CAMBIOS CONFIRMADOS EN LA BASE DE DATOS")
    
    # Después
    cursor.execute("SELECT COUNT(*) FROM conversation_messages")
    total_despues = cursor.fetchone()[0]
    print(f"\n📊 Mensajes DESPUÉS: {total_despues}")
    print(f"📊 Eliminados: {total_antes - total_despues}")
    
    # Nueva distribución
    print("\n" + "="*80)
    print("📈 NUEVA DISTRIBUCIÓN DE CONFIANZA")
    print("="*80)
    
    cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE confidence >= 0.90")
    muy_alta = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE confidence >= 0.75 AND confidence < 0.90")
    alta = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE confidence >= 0.60 AND confidence < 0.75")
    media = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE confidence < 0.60")
    baja = cursor.fetchone()[0]
    
    if total_despues > 0:
        print(f"\nMuy Alta (90-100%): {muy_alta} ({muy_alta/total_despues*100:.1f}%)")
        print(f"Alta (75-89%):      {alta} ({alta/total_despues*100:.1f}%)")
        print(f"Media (60-74%):     {media} ({media/total_despues*100:.1f}%)")
        print(f"Baja (<60%):        {baja} ({baja/total_despues*100:.1f}%)")
    
    print("\n✅ ¡Limpieza completada! Refresca el dashboard para ver las nuevas estadísticas.")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
