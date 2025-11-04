"""
Script simple para confirmar la limpieza pendiente en la BD
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
    conn.commit()  # Confirmar cualquier transacción pendiente
    cursor = conn.cursor()
    
    print("✅ Transacción confirmada")
    
    # Ver estado actual
    cursor.execute("SELECT COUNT(*) FROM conversation_messages")
    total = cursor.fetchone()[0]
    print(f"📊 Total actual de mensajes: {total}")
    
    # Nueva distribución
    cursor.execute("""
        SELECT 
            CASE 
                WHEN confidence >= 0.90 THEN 'Muy Alta (90-100%)'
                WHEN confidence >= 0.75 THEN 'Alta (75-89%)'
                WHEN confidence >= 0.60 THEN 'Media (60-74%)'
                ELSE 'Baja (<60%)'
            END as rango,
            COUNT(*) as cantidad
        FROM conversation_messages
        GROUP BY rango
        ORDER BY 
            CASE 
                WHEN confidence >= 0.90 THEN 1
                WHEN confidence >= 0.75 THEN 2
                WHEN confidence >= 0.60 THEN 3
                ELSE 4
            END
    """)
    
    print("\n📈 Distribución de Confianza:")
    print(f"{'Rango':<20} {'Cantidad':<12} {'Porcentaje'}")
    print("-"*50)
    
    for rango, cant in cursor.fetchall():
        pct = (cant / total * 100) if total > 0 else 0
        print(f"{rango:<20} {cant:<12} {pct:>10.1f}%")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
