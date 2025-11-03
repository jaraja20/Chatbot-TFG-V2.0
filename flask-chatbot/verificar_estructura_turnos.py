"""
Script para verificar la estructura real de la tabla turnos
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

try:
    print("🔍 VERIFICANDO ESTRUCTURA DE LA TABLA TURNOS")
    print("=" * 70)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Obtener todas las columnas de la tabla turnos
    cursor.execute("""
        SELECT 
            column_name, 
            data_type, 
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = 'turnos'
        ORDER BY ordinal_position;
    """)
    
    columnas = cursor.fetchall()
    
    print("\n📋 COLUMNAS DE LA TABLA 'turnos':")
    print("-" * 70)
    print(f"{'COLUMNA':<25} {'TIPO':<20} {'NULL':<8} {'DEFAULT':<15}")
    print("-" * 70)
    
    for col in columnas:
        col_name, data_type, max_length, nullable, default = col
        tipo_completo = f"{data_type}"
        if max_length:
            tipo_completo += f"({max_length})"
        
        null_str = "SÍ" if nullable == "YES" else "NO"
        default_str = str(default)[:15] if default else "-"
        
        print(f"{col_name:<25} {tipo_completo:<20} {null_str:<8} {default_str:<15}")
    
    print("-" * 70)
    print(f"\n✅ Total de columnas: {len(columnas)}")
    
    # Verificar si hay registros
    cursor.execute("SELECT COUNT(*) FROM turnos;")
    count = cursor.fetchone()[0]
    print(f"📊 Registros en la tabla: {count}")
    
    # Mostrar un registro de ejemplo si existe
    if count > 0:
        cursor.execute("SELECT * FROM turnos LIMIT 1;")
        ejemplo = cursor.fetchone()
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'turnos' ORDER BY ordinal_position;")
        nombres_cols = [row[0] for row in cursor.fetchall()]
        
        print("\n📄 EJEMPLO DE REGISTRO:")
        print("-" * 70)
        for nombre, valor in zip(nombres_cols, ejemplo):
            print(f"  {nombre:<25} = {valor}")
        print("-" * 70)
    
    cursor.close()
    conn.close()
    
    print("\n✅ Consulta completada")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
