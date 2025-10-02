"""
Script para poblar la base de datos con turnos simulados
Genera turnos de octubre 2025 con horarios cada 15 minutos
Horario: 7:00 - 15:00 (excepto 11:00 por almuerzo)
Cada hora tiene 4 slots: :00, :15, :30, :45
Deja 1 slot libre por horario (3 de 4 ocupados)
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import random
import string

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

def poblar_base_datos(limpiar_existentes=False):
    session = Session()
    
    try:
        if limpiar_existentes:
            print("🗑️  Eliminando turnos existentes...")
            session.query(Turno).delete()
            session.commit()
            print("✅ Turnos existentes eliminados")
        
        print("\n📅 Generando turnos para octubre 2025...")
        print("⏰ Horario: 7:00 - 15:00 (pausa 11:00)")
        print("📊 4 slots por hora, ocupando 3 de 4 (dejando 1 libre)\n")
        
        dias_laborables = obtener_dias_laborables_octubre_2025()
        horarios = generar_horarios_disponibles()
        
        turnos_creados = 0
        turnos_totales = len(dias_laborables) * len(horarios)
        
        print(f"📈 Días laborables: {len(dias_laborables)}")
        print(f"🕐 Horarios por día: {len(horarios)}")
        print(f"📊 Capacidad total: {turnos_totales} slots")
        print(f"🎯 Turnos a crear: {int(turnos_totales * 0.75)} (75% ocupación)\n")
        
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
                    
                    turno = Turno(
                        nombre=nombre,
                        cedula=cedula,
                        fecha_hora=fecha_hora,
                        codigo=codigo,
                        estado='activo',
                        created_at=datetime.datetime.utcnow()
                    )
                    
                    session.add(turno)
                    turnos_creados += 1
                    
                    if turnos_creados % 50 == 0:
                        session.commit()
                        print(f"  ✓ {turnos_creados} turnos creados...")
        
        session.commit()
        
        print(f"\n✅ Proceso completado exitosamente")
        print(f"📊 Total de turnos creados: {turnos_creados}")
        print(f"📈 Ocupación promedio: ~75%")
        print(f"🎯 Slots libres: ~{turnos_totales - turnos_creados}")
        
        print("\n📊 Estadísticas por horario:")
        for hora in range(7, 15):
            if hora == 11:
                continue
            count = session.query(Turno).filter(
                Turno.fecha_hora >= datetime.datetime(2025, 10, 1, hora, 0),
                Turno.fecha_hora < datetime.datetime(2025, 10, 1, hora + 1, 0)
            ).count()
            print(f"  {hora:02d}:00 - {hora:02d}:59 → {count} turnos")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()

def verificar_disponibilidad_ejemplo():
    session = Session()
    
    try:
        print("\n🔍 Verificando disponibilidad de ejemplo...")
        fecha_ejemplo = datetime.date(2025, 10, 1)
        print(f"\n📅 Disponibilidad para {fecha_ejemplo.strftime('%A %d de octubre')}:\n")
        
        for hora in range(7, 15):
            if hora == 11:
                print(f"  {hora:02d}:00 - CERRADO (Hora de almuerzo)")
                continue
            
            inicio = datetime.datetime.combine(fecha_ejemplo, datetime.time(hora, 0))
            fin = datetime.datetime.combine(fecha_ejemplo, datetime.time(hora, 59))
            
            turnos_ocupados = session.query(Turno).filter(
                Turno.fecha_hora >= inicio,
                Turno.fecha_hora <= fin,
                Turno.estado == 'activo'
            ).count()
            
            slots_totales = 4
            slots_libres = slots_totales - turnos_ocupados
            porcentaje = (turnos_ocupados / slots_totales) * 100
            
            if porcentaje >= 75:
                emoji = "🔴"
                estado = "Poca disponibilidad"
            elif porcentaje >= 50:
                emoji = "🟡"
                estado = "Disponibilidad media"
            else:
                emoji = "🟢"
                estado = "Alta disponibilidad"
            
            print(f"  {emoji} {hora:02d}:00 - {turnos_ocupados}/{slots_totales} ocupados → {estado}")
        
    except Exception as e:
        print(f"❌ Error verificando disponibilidad: {e}")
    finally:
        session.close()

def limpiar_base_datos():
    session = Session()
    try:
        count = session.query(Turno).delete()
        session.commit()
        print(f"✅ {count} turnos eliminados de la base de datos")
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 SCRIPT DE POBLACIÓN DE TURNOS - OCTUBRE 2025")
    print("=" * 60)
    
    print("\nOpciones:")
    print("1. Poblar base de datos (sin eliminar existentes)")
    print("2. Limpiar y poblar base de datos (elimina turnos actuales)")
    print("3. Solo limpiar base de datos")
    print("4. Verificar disponibilidad de ejemplo")
    print("5. Salir")
    
    opcion = input("\nSelecciona una opción (1-5): ").strip()
    
    if opcion == "1":
        print("\n📝 Poblando base de datos (conservando turnos existentes)...\n")
        poblar_base_datos(limpiar_existentes=False)
        verificar_disponibilidad_ejemplo()
    
    elif opcion == "2":
        confirmacion = input("\n⚠️  ¿Estás seguro de eliminar TODOS los turnos existentes? (si/no): ").lower()
        if confirmacion == 'si':
            print("\n🗑️  Limpiando y poblando base de datos...\n")
            poblar_base_datos(limpiar_existentes=True)
            verificar_disponibilidad_ejemplo()
        else:
            print("❌ Operación cancelada")
    
    elif opcion == "3":
        confirmacion = input("\n⚠️  ¿Estás seguro de eliminar TODOS los turnos? (si/no): ").lower()
        if confirmacion == 'si':
            limpiar_base_datos()
        else:
            print("❌ Operación cancelada")
    
    elif opcion == "4":
        verificar_disponibilidad_ejemplo()
    
    elif opcion == "5":
        print("👋 Saliendo...")
    
    else:
        print("❌ Opción inválida")
    
    print("\n" + "=" * 60)