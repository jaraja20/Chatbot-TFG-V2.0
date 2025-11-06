# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Script de diagnóstico para verificar el funcionamiento de la BD y motor difuso
Ejecuta pruebas detalladas y genera datos de prueba si es necesario
"""

import datetime
import sys
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('diagnostic.log')
    ]
)
logger = logging.getLogger(__name__)

# Importar modelos y funciones
try:
    from actions import (
        Turno, Base, get_db_session, 
        consultar_ocupacion_real_bd, 
        obtener_horarios_disponibles_reales,
        consultar_disponibilidad_real,
        es_frase_ambigua
    )
    logger.info("[OK] Módulos importados correctamente")
except ImportError as e:
    logger.error(f"[FAIL] Error importando módulos: {e}")
    sys.exit(1)

# Configuración BD
DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'

def test_connection():
    """Prueba la conexión a la base de datos"""
    logger.info("[SEARCH] PRUEBA 1: Conexión a base de datos")
    
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"[OK] Conexión exitosa - PostgreSQL: {version}")
            return True
    except Exception as e:
        logger.error(f"[FAIL] Error de conexión: {e}")
        return False

def test_tables():
    """Verifica que las tablas existan y tengan la estructura correcta"""
    logger.info("[SEARCH] PRUEBA 2: Estructura de tablas")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Verificar tabla turnos
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'turnos'
                ORDER BY ordinal_position
            """))
            
            columnas = result.fetchall()
            logger.info(f"[OK] Tabla 'turnos' encontrada con {len(columnas)} columnas:")
            for col in columnas:
                logger.info(f"   - {col[0]}: {col[1]}")
            
            # Verificar índices
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'turnos'
            """))
            
            indices = result.fetchall()
            logger.info(f"[OK] Índices encontrados: {len(indices)}")
            for idx in indices:
                logger.info(f"   - {idx[0]}")
            
            return True
            
    except Exception as e:
        logger.error(f"[FAIL] Error verificando tablas: {e}")
        return False

def count_existing_turnos():
    """Cuenta turnos existentes en la BD"""
    logger.info("[SEARCH] PRUEBA 3: Conteo de turnos existentes")
    
    try:
        with get_db_session() as session:
            total = session.query(Turno).count()
            activos = session.query(Turno).filter(Turno.estado == 'activo').count()
            futuros = session.query(Turno).filter(
                Turno.fecha_hora >= datetime.datetime.now(),
                Turno.estado == 'activo'
            ).count()
            
            logger.info(f"[OK] Total de turnos: {total}")
            logger.info(f"[OK] Turnos activos: {activos}")
            logger.info(f"[OK] Turnos futuros: {futuros}")
            
            # Mostrar algunos turnos recientes
            turnos_recientes = session.query(Turno).order_by(Turno.created_at.desc()).limit(5).all()
            logger.info(f"[OK] Últimos 5 turnos:")
            for turno in turnos_recientes:
                logger.info(f"   - {turno.nombre} | {turno.fecha_hora} | {turno.codigo}")
            
            return total
            
    except Exception as e:
        logger.error(f"[FAIL] Error contando turnos: {e}")
        return 0

def create_test_data():
    """Crea datos de prueba para los próximos días"""
    logger.info("[SEARCH] PRUEBA 4: Creando datos de prueba")
    
    try:
        with get_db_session() as session:
            hoy = datetime.date.today()
            datos_creados = 0
            
            # Crear turnos para próximos 3 días hábiles
            for i in range(1, 8):
                fecha = hoy + datetime.timedelta(days=i)
                if fecha.weekday() >= 5:  # Saltar fines de semana
                    continue
                
                # Crear algunos turnos distribuidos
                horarios_prueba = [
                    (8, 0), (9, 30), (10, 15), (12, 30), (14, 0), (14, 45)
                ]
                
                for j, (hora, minuto) in enumerate(horarios_prueba):
                    if j >= 4:  # Solo 4 turnos por día para dejar espacios
                        break
                        
                    fecha_hora = datetime.datetime.combine(fecha, datetime.time(hora, minuto))
                    
                    # Verificar si ya existe
                    existe = session.query(Turno).filter(Turno.fecha_hora == fecha_hora).first()
                    if not existe:
                        nuevo_turno = Turno(
                            nombre=f"Usuario Prueba {j+1}",
                            cedula=f"123456{j}",
                            fecha_hora=fecha_hora,
                            codigo=f"TEST{i}{j}",
                            estado='activo'
                        )
                        session.add(nuevo_turno)
                        datos_creados += 1
            
            logger.info(f"[OK] Datos de prueba creados: {datos_creados} turnos")
            return datos_creados
            
    except Exception as e:
        logger.error(f"[FAIL] Error creando datos de prueba: {e}")
        return 0

def test_ocupacion_functions():
    """Prueba las funciones de consulta de ocupación"""
    logger.info("[SEARCH] PRUEBA 5: Funciones de ocupación")
    
    try:
        with get_db_session() as session:
            # Probar para mañana
            manana = datetime.date.today() + datetime.timedelta(days=1)
            if manana.weekday() >= 5:  # Si es fin de semana, usar lunes
                manana = datetime.date.today() + datetime.timedelta(days=7-datetime.date.today().weekday())
            
            logger.info(f"Probando funciones para: {manana}")
            
            # Test consultar_ocupacion_real_bd
            ocupacion_manana = consultar_ocupacion_real_bd(manana, 9, 11, session)
            logger.info(f"[OK] Ocupación mañana (9-11): {ocupacion_manana}%")
            
            # Test obtener_horarios_disponibles_reales
            horarios = obtener_horarios_disponibles_reales(manana, session, 10)
            logger.info(f"[OK] Horarios disponibles: {len(horarios)}")
            logger.info(f"   Primeros 5: {horarios[:5]}")
            
            # Test consultar_disponibilidad_real
            disponibilidad = consultar_disponibilidad_real(manana, session)
            logger.info(f"[OK] Disponibilidad por franjas:")
            for franja, porcentaje in disponibilidad.items():
                logger.info(f"   - {franja}: {porcentaje}%")
            
            return True
            
    except Exception as e:
        logger.error(f"[FAIL] Error probando funciones de ocupación: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_fuzzy_detection():
    """Prueba la detección de frases ambiguas"""
    logger.info("[SEARCH] PRUEBA 6: Detección de frases ambiguas")
    
    frases_test = [
        "que horarios hay disponibles",
        "recomendame un horario",
        "lo antes posible",
        "cuando haya menos gente",
        "14:00",
        "mañana a las 10",
        "el mejor horario",
        "esta disponible las 12:00?"
    ]
    
    try:
        for frase in frases_test:
            es_ambigua = es_frase_ambigua(frase)
            status = "AMBIGUA" if es_ambigua else "ESPECÍFICA"
            logger.info(f"[OK] '{frase}' -> {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Error probando detección difusa: {e}")
        return False

def test_database_performance():
    """Prueba el rendimiento de consultas a la BD"""
    logger.info("[SEARCH] PRUEBA 7: Rendimiento de BD")
    
    try:
        import time
        with get_db_session() as session:
            # Test velocidad de consulta
            start_time = time.time()
            
            # Consulta compleja típica
            hoy = datetime.date.today()
            for i in range(3):
                fecha = hoy + datetime.timedelta(days=i+1)
                if fecha.weekday() < 5:
                    disponibilidad = consultar_disponibilidad_real(fecha, session)
                    horarios = obtener_horarios_disponibles_reales(fecha, session, 20)
            
            elapsed = time.time() - start_time
            logger.info(f"[OK] Consultas completadas en {elapsed:.2f} segundos")
            
            if elapsed > 5:
                logger.warning("[WARN] Las consultas son lentas, considera optimizar")
            
            return True
            
    except Exception as e:
        logger.error(f"[FAIL] Error probando rendimiento: {e}")
        return False

def generate_availability_report():
    """Genera un reporte detallado de disponibilidad"""
    logger.info("[SEARCH] PRUEBA 8: Reporte de disponibilidad")
    
    try:
        with get_db_session() as session:
            hoy = datetime.date.today()
            logger.info(f"\n[STATS] REPORTE DE DISPONIBILIDAD - {hoy}")
            logger.info("=" * 50)
            
            for i in range(1, 6):
                fecha = hoy + datetime.timedelta(days=i)
                if fecha.weekday() >= 5:
                    continue
                
                disponibilidad = consultar_disponibilidad_real(fecha, session)
                horarios = obtener_horarios_disponibles_reales(fecha, session, 50)
                
                logger.info(f"\n[CAL] {fecha.strftime('%A %d/%m/%Y')}:")
                logger.info(f"   Temprano (7-9): {disponibilidad['temprano']}% ocupado")
                logger.info(f"   Mañana (9-11): {disponibilidad['manana']}% ocupado")  
                logger.info(f"   Tarde (12-15): {disponibilidad['tarde']}% ocupado")
                logger.info(f"   Total horarios disponibles: {len(horarios)}")
                
                if horarios:
                    logger.info(f"   Primeros horarios: {', '.join(horarios[:8])}")
                else:
                    logger.info(f"   [WARN] Sin horarios disponibles")
            
            return True
            
    except Exception as e:
        logger.error(f"[FAIL] Error generando reporte: {e}")
        return False

def run_full_diagnostic():
    """Ejecuta el diagnóstico completo"""
    logger.info("[START] INICIANDO DIAGNÓSTICO COMPLETO DEL SISTEMA")
    logger.info("=" * 60)
    
    results = {}
    
    # Ejecutar todas las pruebas
    tests = [
        ("Conexión BD", test_connection),
        ("Estructura tablas", test_tables),
        ("Conteo turnos", count_existing_turnos),
        ("Datos prueba", create_test_data),
        ("Funciones ocupación", test_ocupacion_functions),
        ("Detección difusa", test_fuzzy_detection),
        ("Rendimiento BD", test_database_performance),
        ("Reporte disponibilidad", generate_availability_report)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results[test_name] = result
            if result:
                passed += 1
                logger.info(f"[OK] {test_name}: PASÓ")
            else:
                logger.error(f"[FAIL] {test_name}: FALLÓ")
        except Exception as e:
            logger.error(f"[FAIL] {test_name}: ERROR - {e}")
            results[test_name] = False
    
    # Resumen final
    logger.info(f"\n{'='*60}")
    logger.info(f"[*] RESUMEN FINAL DEL DIAGNÓSTICO")
    logger.info(f"{'='*60}")
    logger.info(f"[OK] Pruebas pasadas: {passed}/{total}")
    logger.info(f"[FAIL] Pruebas fallidas: {total-passed}/{total}")
    
    if passed == total:
        logger.info("[*] SISTEMA FUNCIONANDO CORRECTAMENTE")
        logger.info("[IDEA] El motor difuso debería funcionar perfectamente")
    else:
        logger.warning("[WARN] SISTEMA CON PROBLEMAS DETECTADOS")
        logger.info("[FIX] Revisa los errores arriba para solucionarlos")
    
    # Recomendaciones específicas
    logger.info(f"\n[*] RECOMENDACIONES:")
    if not results.get("Conexión BD", False):
        logger.info("- Verifica que PostgreSQL esté ejecutándose")
        logger.info("- Comprueba las credenciales de conexión")
    
    if not results.get("Datos prueba", False):
        logger.info("- La BD parece vacía, crea algunos turnos de prueba")
    
    if not results.get("Funciones ocupación", False):
        logger.info("- Problema crítico con las funciones de disponibilidad")
        logger.info("- El motor difuso no funcionará correctamente")
    
    return passed == total

if __name__ == "__main__":
    print("[SEARCH] Script de Diagnóstico del Sistema de Turnos")
    print("=" * 50)
    
    try:
        success = run_full_diagnostic()
        exit_code = 0 if success else 1
        
        print(f"\n{'='*50}")
        if success:
            print("[OK] DIAGNÓSTICO COMPLETADO - Sistema OK")
        else:
            print("[FAIL] DIAGNÓSTICO COMPLETADO - Problemas detectados")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n[WARN] Diagnóstico interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error crítico en diagnóstico: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)