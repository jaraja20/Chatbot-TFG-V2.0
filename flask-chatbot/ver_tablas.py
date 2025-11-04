"""
Script para ver las tablas disponibles en la base de datos
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
    print("📋 TABLAS DISPONIBLES EN LA BASE DE DATOS")
    print("="*80)
    
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tablas = cursor.fetchall()
    
    print("\nTablas encontradas:")
    for tabla in tablas:
        print(f"  • {tabla[0]}")
        
        # Mostrar cantidad de registros
        cursor.execute(f"SELECT COUNT(*) FROM {tabla[0]}")
        count = cursor.fetchone()[0]
        print(f"    └─ {count} registros")
        
        # Mostrar columnas
        cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{tabla[0]}'
            ORDER BY ordinal_position
        """)
        columnas = cursor.fetchall()
        print(f"    └─ Columnas: {', '.join([c[0] for c in columnas[:5]])}{'...' if len(columnas) > 5 else ''}")
        print()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
