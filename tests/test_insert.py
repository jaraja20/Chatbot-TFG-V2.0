import psycopg2

DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Insertar en tabla de prueba
cursor.execute("""
    INSERT INTO turnos_test (nombre, fecha_hora, codigo)
    VALUES ('Desde Python', '2025-10-01 14:00:00', 'PY001')
""")
conn.commit()

# Verificar
cursor.execute("SELECT COUNT(*) FROM turnos_test")
print(f"Total en turnos_test: {cursor.fetchone()[0]}")

cursor.close()
conn.close()