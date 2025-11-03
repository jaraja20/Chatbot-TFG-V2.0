import psycopg2
from datetime import datetime

try:
    conn = psycopg2.connect(
        dbname='chatbotdb',
        user='botuser',
        password='root',
        host='localhost'
    )
    cur = conn.cursor()
    
    # Contar turnos activos
    cur.execute("SELECT COUNT(*) FROM turnos WHERE estado='activo';")
    count = cur.fetchone()[0]
    print(f"\n✅ Total turnos activos: {count}")
    
    if count > 0:
        # Ver algunos turnos
        cur.execute("SELECT nombre, cedula, fecha_hora, estado FROM turnos WHERE estado='activo' LIMIT 5;")
        print("\n📋 Ejemplos de turnos:")
        for row in cur.fetchall():
            print(f"  - {row[0]} ({row[1]}) - {row[2]} - {row[3]}")
        
        # Ver fechas disponibles
        cur.execute("SELECT DATE(fecha_hora), COUNT(*) FROM turnos WHERE estado='activo' GROUP BY DATE(fecha_hora) ORDER BY DATE(fecha_hora);")
        print("\n📅 Turnos por fecha:")
        for row in cur.fetchall():
            print(f"  - {row[0]}: {row[1]} turnos")
    else:
        print("\n⚠️ NO HAY TURNOS EN LA BASE DE DATOS")
        print("   Esto explica por qué el sistema dice '0 horas disponibles'")
    
    conn.close()
    print("\n✅ Consulta completada\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}\n")
