"""
Script para agregar la columna 'email' a la tabla turnos si no existe
"""
import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'postgres',
    'password': 'admin',
    'port': 5432
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Verificar si la columna 'email' existe
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='turnos' AND column_name='email';
    """)
    
    if cursor.fetchone() is None:
        print("⚠️  Columna 'email' no existe. Agregándola...")
        
        # Agregar columna email
        cursor.execute("""
            ALTER TABLE turnos 
            ADD COLUMN email VARCHAR(255);
        """)
        
        conn.commit()
        print("✅ Columna 'email' agregada exitosamente!")
    else:
        print("✅ La columna 'email' ya existe en la tabla 'turnos'")
    
    # Verificar estructura actual de la tabla
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name='turnos'
        ORDER BY ordinal_position;
    """)
    
    print("\n📋 Estructura actual de la tabla 'turnos':")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
