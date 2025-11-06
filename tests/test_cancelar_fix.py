"""
Test para validar FIX de "cancelar" y correcciones en resumen

Problemas reportados del dashboard:
1. "Cancelar" y "Cancelar horario" → Fallback ([FAIL])
2. Usuario NO puede corregir datos en resumen final ([FAIL])

Fixes aplicados:
1. Handler para intent "cancelar" agregado
2. Resumen mejorado con instrucciones de corrección
"""
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente, SessionContext, get_or_create_context

def test_cancelar():
    """Test para validar que 'cancelar' funciona correctamente"""
    print("\n" + "="*80)
    print("TEST 1: Intent 'cancelar' - Debe resetear contexto")
    print("="*80)
    
    # Caso 1: Cancelar con datos parciales
    contexto = get_or_create_context("test-cancelar-1")
    contexto.nombre = "Juan Pérez"
    contexto.cedula = "1234567"
    contexto.fecha = "2025-11-05"
    
    resultado = procesar_mensaje_inteligente("Cancelar", "test-cancelar-1")
    
    print(f"\n[NOTE] Mensaje: 'Cancelar'")
    print(f"[TARGET] Intent detectado: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    # Validar que reseteó el contexto
    assert contexto.nombre is None, "[FAIL] Nombre NO fue reseteado"
    assert contexto.cedula is None, "[FAIL] Cédula NO fue reseteada"
    assert contexto.fecha is None, "[FAIL] Fecha NO fue reseteada"
    assert resultado['intent'] == "cancelar", f"[FAIL] Intent incorrecto: {resultado['intent']}"
    assert "cancelado correctamente" in resultado['text'].lower(), "[FAIL] Respuesta incorrecta"
    
    print("[OK] TEST 1 PASADO: 'Cancelar' resetea correctamente")
    
    # Caso 2: Cancelar horario (variación)
    contexto = get_or_create_context("test-cancelar-2")
    contexto.nombre = "Ana López"
    contexto.hora = "09:00"
    
    resultado = procesar_mensaje_inteligente("Cancelar horario", "test-cancelar-2")
    
    print(f"\n[NOTE] Mensaje: 'Cancelar horario'")
    print(f"[TARGET] Intent detectado: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    assert contexto.nombre is None, "[FAIL] Nombre NO fue reseteado"
    assert contexto.hora is None, "[FAIL] Hora NO fue reseteada"
    assert resultado['intent'] == "cancelar", f"[FAIL] Intent incorrecto: {resultado['intent']}"
    
    print("[OK] TEST 2 PASADO: 'Cancelar horario' resetea correctamente")
    
    # Caso 3: Cancelar sin datos (no hay nada que cancelar)
    resultado = procesar_mensaje_inteligente("Cancelar", "test-cancelar-3")
    
    print(f"\n[NOTE] Mensaje: 'Cancelar' (sin turno en progreso)")
    print(f"[TARGET] Intent detectado: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    assert resultado['intent'] == "cancelar", f"[FAIL] Intent incorrecto: {resultado['intent']}"
    assert "no tienes ningún turno" in resultado['text'].lower(), "[FAIL] Respuesta incorrecta para caso vacío"
    
    print("[OK] TEST 3 PASADO: 'Cancelar' sin turno responde correctamente")

def test_resumen_con_instrucciones():
    """Test para validar que resumen tiene instrucciones de corrección"""
    print("\n" + "="*80)
    print("TEST 2: Resumen con instrucciones de corrección")
    print("="*80)
    
    contexto = get_or_create_context("test-resumen")
    contexto.nombre = "María García"
    contexto.cedula = "7654321"
    contexto.fecha = "2025-11-05"
    contexto.hora = "10:00"
    contexto.email = "maria@test.com"
    
    # Simular que pedimos email (última etapa antes del resumen)
    resultado = procesar_mensaje_inteligente("maria@test.com", "test-resumen")
    
    print(f"\n[NOTE] Mensaje: 'maria@test.com' (último dato)")
    print(f"[TARGET] Intent detectado: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    # Validar que el resumen incluye instrucciones de corrección
    respuesta = resultado['text']
    assert "Resumen de tu turno" in respuesta, "[FAIL] No muestra resumen"
    assert "Confirmas estos datos" in respuesta, "[FAIL] No pide confirmación"
    assert "Cambiar" in respuesta, "[FAIL] No muestra instrucciones de cambio"
    assert "Cancelar" in respuesta, "[FAIL] No muestra opción de cancelar"
    assert "nombre" in respuesta.lower() and "cédula" in respuesta.lower(), "[FAIL] No lista todos los campos corregibles"
    
    print("[OK] TEST PASADO: Resumen incluye instrucciones completas")

def test_flujo_completo_con_cancelacion():
    """Test de flujo completo: Agendar → Cancelar → Re-agendar"""
    print("\n" + "="*80)
    print("TEST 3: Flujo completo con cancelación")
    print("="*80)
    
    contexto = get_or_create_context("test-flujo")
    
    # Paso 1: Empezar a agendar
    resultado = procesar_mensaje_inteligente("Quiero sacar un turno", "test-flujo")
    print(f"\n1[*]⃣ Inicio: {resultado['text'][:60]}...")
    assert contexto.nombre is None
    
    # Paso 2: Dar nombre
    resultado = procesar_mensaje_inteligente("Pedro Ramírez", "test-flujo")
    print(f"2[*]⃣ Nombre ingresado: {contexto.nombre}")
    assert contexto.nombre == "Pedro Ramírez"
    
    # Paso 3: Dar cédula
    resultado = procesar_mensaje_inteligente("5555555", "test-flujo")
    print(f"3[*]⃣ Cédula ingresada: {contexto.cedula}")
    assert contexto.cedula == "5555555"
    
    # Paso 4: CANCELAR en medio del proceso
    resultado = procesar_mensaje_inteligente("Cancelar", "test-flujo")
    print(f"4[*]⃣ CANCELACIÓN:")
    print(f"   Intent: {resultado['intent']}")
    print(f"   Contexto reseteado: Nombre={contexto.nombre}, Cédula={contexto.cedula}")
    
    assert resultado['intent'] == "cancelar"
    assert contexto.nombre is None, "[FAIL] Nombre NO fue reseteado"
    assert contexto.cedula is None, "[FAIL] Cédula NO fue reseteada"
    assert "cancelado correctamente" in resultado['text'].lower()
    
    # Paso 5: Empezar de nuevo
    resultado = procesar_mensaje_inteligente("Quiero sacar un turno", "test-flujo")
    print(f"5[*]⃣ Reinicio: {resultado['text'][:60]}...")
    
    # Paso 6: Nuevo nombre
    resultado = procesar_mensaje_inteligente("Carlos Rodríguez", "test-flujo")
    print(f"6[*]⃣ Nuevo nombre: {contexto.nombre}")
    assert contexto.nombre == "Carlos Rodríguez"
    
    print("\n[OK] TEST PASADO: Flujo completo con cancelación funciona")

if __name__ == "__main__":
    print("\n[TEST] INICIANDO TESTS DE FIX 'CANCELAR' Y CORRECCIONES")
    print("="*80)
    
    try:
        test_cancelar()
        test_resumen_con_instrucciones()
        test_flujo_completo_con_cancelacion()
        
        print("\n" + "="*80)
        print("[OK] TODOS LOS TESTS PASARON (3/3)")
        print("="*80)
        print("\n[*] Resumen de fixes validados:")
        print("   [OK] Intent 'cancelar' funciona correctamente")
        print("   [OK] 'Cancelar' resetea contexto completo")
        print("   [OK] 'Cancelar horario' detecta intent correcto")
        print("   [OK] Cancelar sin turno muestra mensaje apropiado")
        print("   [OK] Resumen incluye instrucciones de corrección")
        print("   [OK] Flujo completo con cancelación y re-inicio funciona")
        print("\n[TARGET] Fixes listos para producción!")
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FALLÓ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
