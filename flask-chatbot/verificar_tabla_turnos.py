"""
Script para verificar y agregar la columna token_confirmacion a la tabla turnos
"""
import psycopg2
from psycopg2 import sql

print("\n" + "="*80)
print("🔍 VERIFICANDO ESTRUCTURA DE LA BASE DE DATOS")
print("="*80 + "\n")

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(
        host="localhost",
        database="chatbotdb",
        user="botuser",
        password="root"
    )
    cur = conn.cursor()
    
    # 1. Verificar si la tabla turnos existe
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'turnos'
        );
    """)
    tabla_existe = cur.fetchone()[0]
    
    if not tabla_existe:
        print("❌ La tabla 'turnos' no existe. Creándola...")
        cur.execute("""
            CREATE TABLE turnos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255),
                cedula VARCHAR(50),
                fecha DATE,
                hora TIME,
                numero_turno VARCHAR(50),
                codigo_turno VARCHAR(10),
                email VARCHAR(255),
                confirmado BOOLEAN DEFAULT FALSE,
                fecha_confirmacion TIMESTAMP,
                token_confirmacion VARCHAR(100) UNIQUE,
                estado VARCHAR(50) DEFAULT 'pendiente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("✅ Tabla 'turnos' creada exitosamente")
    else:
        print("✅ La tabla 'turnos' existe")
    
    # 2. Verificar si la columna token_confirmacion existe
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'turnos' 
        AND column_name = 'token_confirmacion';
    """)
    columna_token = cur.fetchone()
    
    if not columna_token:
        print("⚠️ Columna 'token_confirmacion' no existe. Agregándola...")
        cur.execute("""
            ALTER TABLE turnos 
            ADD COLUMN token_confirmacion VARCHAR(100) UNIQUE;
        """)
        conn.commit()
        print("✅ Columna 'token_confirmacion' agregada exitosamente")
    else:
        print("✅ La columna 'token_confirmacion' existe")
    
    # 3. Verificar si la columna estado existe
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'turnos' 
        AND column_name = 'estado';
    """)
    columna_estado = cur.fetchone()
    
    if not columna_estado:
        print("⚠️ Columna 'estado' no existe. Agregándola...")
        cur.execute("""
            ALTER TABLE turnos 
            ADD COLUMN estado VARCHAR(50) DEFAULT 'pendiente';
        """)
        conn.commit()
        print("✅ Columna 'estado' agregada exitosamente")
    else:
        print("✅ La columna 'estado' existe")
    
    # 4. Mostrar estructura actual de la tabla
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'turnos'
        ORDER BY ordinal_position;
    """)
    columnas = cur.fetchall()
    
    print("\n📋 Estructura actual de la tabla 'turnos':")
    print("-" * 80)
    for col in columnas:
        nombre = col[0]
        tipo = col[1]
        longitud = col[2] if col[2] else ""
        nullable = "NULL" if col[3] == "YES" else "NOT NULL"
        default = f"DEFAULT {col[4]}" if col[4] else ""
        print(f"  • {nombre:25} {tipo:15} {str(longitud):10} {nullable:10} {default}")
    print("-" * 80)
    
    # 5. Contar turnos existentes
    cur.execute("SELECT COUNT(*) FROM turnos;")
    total_turnos = cur.fetchone()[0]
    print(f"\n📊 Total de turnos en la base de datos: {total_turnos}")
    
    cur.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ VERIFICACIÓN COMPLETADA EXITOSAMENTE")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    print(traceback.format_exc())
