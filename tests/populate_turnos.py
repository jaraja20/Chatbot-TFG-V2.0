"""
Script para poblar la base de datos con turnos simulados con integración Google Calendar
Genera turnos de octubre 2025 con horarios cada 15 minutos
Horario: 7:00 - 15:00 (excepto 11:00 por almuerzo)
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import random
import string
from calendar_utils import crear_evento_turno
import time

DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Turno(Base):
    __tablename__ = 'turnos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    cedula = Column(String(20))
    fecha_hora = Column(DateTime, nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    estado = Column(String(20), default='activo')
    event_id = Column(String(255))  # <- NUEVA COLUMNA
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

NOMBRES = [
    "Juan Pérez", "María González", "Carlos López", "Ana Martínez",
    "Luis Rodríguez", "Laura Fernández", "Pedro Sánchez", "Carmen Díaz",
    "Miguel Torres", "Isabel Ramírez", "José García", "Rosa Flores",
    "Antonio Ruiz", "Lucía Castro", "Francisco Silva", "Patricia Ortiz",
    "Javier Morales", "Elena Núñez", "Roberto Medina", "Teresa Vega",
    "Ricardo Romero", "Sofía Herrera", "Diego Vargas", "Mónica Reyes",
    "Andrés Gutiérrez", "Beatriz Navarro", "Raúl Mendoza", "Claudia Ramos",
    "Sergio Jiménez", "Natalia Cabrera", "Fernando Cruz", "Gabriela Soto",
    "Marcos Peña", "Daniela Ríos", "Pablo Domínguez", "Valentina Guerrero",
    "Gustavo Aguilar", "Carolina Bravo", "Héctor Campos", "Andrea León"
]

def generar_codigo_unico():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generar_cedula():
    return str(random.randint(1000000, 9999999))

def obtener_dias_laborables_octubre_2025():
    dias_laborables = []
    for dia in range(1, 32):
        fecha = datetime.date(2025, 10, dia)
        if fecha.weekday() <= 4:
            dias_laborables.append(fecha)
    return dias_laborables

def generar_horarios_disponibles():
    horarios = []
    for hora in range(7, 15):
        if hora == 11:
            continue
        for minuto in [0, 15, 30, 45]:
            horarios.append(datetime.time(hora, minuto))
    return horarios

def poblar_base_datos(limpiar_existentes=False, sincronizar_calendar=True):
    session = Session()
    
    try:
        if limpiar_existentes:
            print("Eliminando turnos existentes...")
            session.query(Turno).delete()
            session.commit()
            print("Turnos existentes eliminados")
        
        print("\nGenerando turnos para octubre 2025...")
        print("Horario: 7:00 - 15:00 (pausa 11:00)")
        
        if sincronizar_calendar:
            print("ADVERTENCIA: Esto creara eventos en Google Calendar")
            print("Tiempo estimado: 15-20 minutos\n")
        
        dias_laborables = obtener_dias_laborables_octubre_2025()
        horarios = generar_horarios_disponibles()
        
        turnos_creados = 0
        eventos_creados = 0
        eventos_fallidos = 0
        
        for fecha in dias_laborables:
            print(f"Procesando {fecha.strftime('%A %d/%m/%Y')}...")
            
            for horario in horarios:
                fecha_hora = datetime.datetime.combine(fecha, horario)
                slots_a_ocupar = random.sample([0, 1, 2, 3], 3)
                
                for slot in slots_a_ocupar:
                    nombre = random.choice(NOMBRES)
                    cedula = generar_cedula()
                    codigo = generar_codigo_unico()
                    
                    while session.query(Turno).filter_by(codigo=codigo).first():
                        codigo = generar_codigo_unico()
                    
                    event_id = None
                    
                    # Crear evento en Google Calendar si está habilitado
                    if sincronizar_calendar:
                        try:
                            exito, resultado = crear_evento_turno(
                                nombre=nombre,
                                cedula=cedula,
                                fecha_hora=fecha_hora,
                                codigo_turno=codigo
                            )
                            
                            if exito and 'eid=' in resultado:
                                event_id = resultado.split('eid=')[1].split('&')[0]
                                eventos_creados += 1
                            else:
                                eventos_fallidos += 1
                            
                            time.sleep(0.3)  # Pausa para no saturar API
                            
                        except Exception as e:
                            print(f"  Error creando evento para {codigo}: {e}")
                            eventos_fallidos += 1
                    
                    turno = Turno(
                        nombre=nombre,
                        cedula=cedula,
                        fecha_hora=fecha_hora,
                        codigo=codigo,
                        estado='activo',
                        event_id=event_id,
                        created_at=datetime.datetime.utcnow()
                    )
                    
                    session.add(turno)
                    turnos_creados += 1
                    
                    if turnos_creados % 50 == 0:
                        session.commit()
                        if sincronizar_calendar:
                            print(f"  {turnos_creados} turnos creados ({eventos_creados} en Calendar)...")
                        else:
                            print(f"  {turnos_creados} turnos creados...")
        
        session.commit()
        
        print(f"\nProceso completado exitosamente")
        print(f"Total de turnos creados: {turnos_creados}")
        
        if sincronizar_calendar:
            print(f"Eventos en Google Calendar: {eventos_creados}")
            print(f"Eventos fallidos: {eventos_fallidos}")
        
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario")
        session.rollback()
    except Exception as e:
        session.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        session.close()

def limpiar_base_datos():
    session = Session()
    try:
        count = session.query(Turno).delete()
        session.commit()
        print(f"{count} turnos eliminados de la base de datos")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 60)
    print("SCRIPT DE POBLACION DE TURNOS - OCTUBRE 2025")
    print("=" * 60)
    
    print("\nOpciones:")
    print("1. Poblar BD + Google Calendar (LENTO, 15-20 min)")
    print("2. Poblar solo BD (RAPIDO, sin Calendar)")
    print("3. Limpiar base de datos")
    print("4. Salir")
    
    opcion = input("\nSelecciona una opcion (1-4): ").strip()
    
    if opcion == "1":
        confirmacion = input("\nEsto creara ~1932 eventos en Calendar. Continuar? (si/no): ").lower()
        if confirmacion == 'si':
            poblar_base_datos(limpiar_existentes=True, sincronizar_calendar=True)
    
    elif opcion == "2":
        confirmacion = input("\nEsto eliminara turnos existentes. Continuar? (si/no): ").lower()
        if confirmacion == 'si':
            poblar_base_datos(limpiar_existentes=True, sincronizar_calendar=False)
    
    elif opcion == "3":
        confirmacion = input("\nEliminar TODOS los turnos? (si/no): ").lower()
        if confirmacion == 'si':
            limpiar_base_datos()
    
    elif opcion == "4":
        print("Saliendo...")
    
    else:
        print("Opcion invalida")
    
    print("\n" + "=" * 60)