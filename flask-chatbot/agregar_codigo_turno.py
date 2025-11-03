"""
Script para agregar columna codigo_turno a la tabla turnos
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

try:
    print("🔄 Conectando a la base de datos...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Verificar si la columna ya existe
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='turnos' AND column_name='codigo_turno';
    """)
    
    existe = cursor.fetchone()
    
    if existe:
        print("✅ La columna 'codigo_turno' ya existe en la tabla 'turnos'")
    else:
        print("➕ Agregando columna 'codigo_turno' a la tabla 'turnos'...")
        cursor.execute("""
            ALTER TABLE turnos 
            ADD COLUMN codigo_turno VARCHAR(5);
        """)
        conn.commit()
        print("✅ Columna 'codigo_turno' agregada exitosamente")
    
    # Mostrar estructura actualizada de la tabla
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'turnos'
        ORDER BY ordinal_position;
    """)
    
    print("\n📋 Estructura actual de la tabla 'turnos':")
    print("-" * 60)
    for row in cursor.fetchall():
        col_name, data_type, max_length = row
        length_str = f"({max_length})" if max_length else ""
        print(f"  • {col_name:20} {data_type}{length_str}")
    print("-" * 60)
    
    cursor.close()
    conn.close()
    print("\n✅ Script completado exitosamente")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
