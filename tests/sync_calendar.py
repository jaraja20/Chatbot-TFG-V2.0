import psycopg2
from calendar_utils import crear_evento_turno
from datetime import datetime
import time

DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'

def sincronizar_turnos():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Obtener turnos sin event_id
        cursor.execute("""
            SELECT id, nombre, cedula, fecha_hora, codigo 
            FROM turnos 
            WHERE event_id IS NULL 
            ORDER BY fecha_hora
        """)
        
        turnos = cursor.fetchall()
        total = len(turnos)
        
        print(f"Turnos a sincronizar: {total}\n")
        
        sincronizados = 0
        errores = 0
        
        for turno in turnos:
            turno_id, nombre, cedula, fecha_hora, codigo = turno
            
            # Crear evento en Google Calendar
            exito, resultado = crear_evento_turno(
                nombre=nombre,
                cedula=cedula,
                fecha_hora=fecha_hora,
                codigo_turno=codigo
            )
            
            if exito:
                # Extraer event_id del link
                event_id = resultado.split('eid=')[1].split('&')[0] if 'eid=' in resultado else None
                
                if event_id:
                    # Actualizar BD con event_id
                    cursor.execute("""
                        UPDATE turnos 
                        SET event_id = %s 
                        WHERE id = %s
                    """, (event_id, turno_id))
                    conn.commit()
                    
                    sincronizados += 1
                    if sincronizados % 10 == 0:
                        print(f"Sincronizados: {sincronizados}/{total}")
                    
                    # Pausa para no saturar la API
                    time.sleep(0.5)
            else:
                errores += 1
                print(f"Error en turno {codigo}: {resultado}")
        
        print(f"\nProceso completado:")
        print(f"✓ Sincronizados: {sincronizados}")
        print(f"✗ Errores: {errores}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("=== SINCRONIZACIÓN CON GOOGLE CALENDAR ===\n")
    confirmacion = input("¿Deseas sincronizar todos los turnos con Google Calendar? (si/no): ")
    
    if confirmacion.lower() == 'si':
        sincronizar_turnos()
    else:
        print("Operación cancelada")