"""
Script para agregar la columna token_confirmacion a la tabla turnos
"""
import psycopg2

print("\n🔧 Agregando columna token_confirmacion a la tabla turnos...")

try:
    conn = psycopg2.connect(
        host="localhost",
        database="chatbotdb",
        user="botuser",
        password="root"
    )
    cur = conn.cursor()
    
    # Verificar si la columna ya existe
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'turnos' 
        AND column_name = 'token_confirmacion';
    """)
    
    if cur.fetchone():
        print("✅ La columna 'token_confirmacion' ya existe")
    else:
        print("➕ Agregando columna 'token_confirmacion'...")
        cur.execute("""
            ALTER TABLE turnos 
            ADD COLUMN token_confirmacion VARCHAR(200);
        """)
        conn.commit()
        print("✅ Columna 'token_confirmacion' agregada exitosamente")
    
    cur.close()
    conn.close()
    print("\n✅ Proceso completado\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}\n")
