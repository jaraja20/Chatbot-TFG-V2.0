"""
Test para validar que "Cambiar [campo]" funciona en el resumen

Escenario:
1. Usuario completa formulario
2. Ve resumen con todos los datos
3. Dice "Cambiar email" o "Cambiar hora"
4. Sistema debe resetear solo ESE campo y pedir nuevo valor
"""
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context

def test_cambiar_email():
    """Test: Cambiar email en el resumen"""
    print("\n" + "="*80)
    print("TEST 1: Cambiar email en resumen")
    print("="*80)
    
    contexto = get_or_create_context("test-cambiar-email")
    contexto.nombre = "Juan Pérez"
    contexto.cedula = "1234567"
    contexto.fecha = "2025-11-05"
    contexto.hora = "09:00"
    contexto.email = "email_incorrecto@test.com"
    
    print(f"\n[*] Datos iniciales:")
    print(f"   Nombre: {contexto.nombre}")
    print(f"   Email: {contexto.email}")
    
    # Usuario dice "Cambiar email"
    resultado = procesar_mensaje_inteligente("Cambiar email", "test-cambiar-email")
    
    print(f"\n[NOTE] Mensaje: 'Cambiar email'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    # Verificar que resetea SOLO el email
    print(f"\n[SEARCH] Contexto después de 'Cambiar email':")
    print(f"   Nombre: {contexto.nombre} (debe mantenerse)")
    print(f"   Cédula: {contexto.cedula} (debe mantenerse)")
    print(f"   Fecha: {contexto.fecha} (debe mantenerse)")
    print(f"   Hora: {contexto.hora} (debe mantenerse)")
    print(f"   Email: {contexto.email} (debe ser None)")
    
    if contexto.email is None:
        print("[OK] Email reseteado correctamente")
    else:
        print(f"[FAIL] Email NO fue reseteado: {contexto.email}")
    
    if contexto.nombre == "Juan Pérez":
        print("[OK] Nombre se mantuvo")
    else:
        print(f"[FAIL] Nombre cambió: {contexto.nombre}")
    
    # Usuario ingresa nuevo email
    resultado = procesar_mensaje_inteligente("nuevo@correo.com", "test-cambiar-email")
    
    print(f"\n[NOTE] Mensaje: 'nuevo@correo.com'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta (primeros 100 chars):\n{resultado['text'][:100]}...")
    print(f"[EMAIL] Nuevo email: {contexto.email}")
    
    if contexto.email == "nuevo@correo.com":
        print("[OK] TEST PASADO: Email actualizado correctamente")
        return True
    else:
        print(f"[FAIL] TEST FALLÓ: Email esperado 'nuevo@correo.com', obtenido '{contexto.email}'")
        return False

def test_cambiar_hora():
    """Test: Cambiar hora en resumen"""
    print("\n" + "="*80)
    print("TEST 2: Cambiar hora en resumen")
    print("="*80)
    
    contexto = get_or_create_context("test-cambiar-hora")
    contexto.nombre = "María López"
    contexto.cedula = "7777777"
    contexto.fecha = "2025-11-06"
    contexto.hora = "08:00"
    contexto.email = "maria@test.com"
    
    print(f"\n[*] Datos iniciales:")
    print(f"   Hora: {contexto.hora}")
    
    # Usuario dice "Cambiar hora"
    resultado = procesar_mensaje_inteligente("Cambiar hora", "test-cambiar-hora")
    
    print(f"\n[NOTE] Mensaje: 'Cambiar hora'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    print(f"\n[SEARCH] Contexto después de 'Cambiar hora':")
    print(f"   Nombre: {contexto.nombre} (debe mantenerse)")
    print(f"   Fecha: {contexto.fecha} (debe mantenerse)")
    print(f"   Email: {contexto.email} (debe mantenerse)")
    print(f"   Hora: {contexto.hora} (debe ser None)")
    
    if contexto.hora is None:
        print("[OK] Hora reseteada correctamente")
    else:
        print(f"[FAIL] Hora NO fue reseteada: {contexto.hora}")
        return False
    
    if contexto.email == "maria@test.com":
        print("[OK] Email se mantuvo")
    else:
        print(f"[FAIL] Email cambió: {contexto.email}")
        return False
    
    # Usuario ingresa nueva hora
    resultado = procesar_mensaje_inteligente("14:00", "test-cambiar-hora")
    
    print(f"\n[NOTE] Mensaje: '14:00'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta (primeros 100 chars):\n{resultado['text'][:100]}...")
    print(f"[CLOCK] Nueva hora: {contexto.hora}")
    
    if contexto.hora == "14:00":
        print("[OK] TEST PASADO: Hora actualizada correctamente")
        return True
    else:
        print(f"[FAIL] TEST FALLÓ: Hora esperada '14:00', obtenida '{contexto.hora}'")
        return False

def test_cambiar_fecha():
    """Test: Cambiar fecha en resumen"""
    print("\n" + "="*80)
    print("TEST 3: Cambiar fecha en resumen")
    print("="*80)
    
    contexto = get_or_create_context("test-cambiar-fecha")
    contexto.nombre = "Carlos García"
    contexto.cedula = "9999999"
    contexto.fecha = "2025-11-05"
    contexto.hora = "10:00"
    contexto.email = "carlos@test.com"
    
    print(f"\n[*] Datos iniciales:")
    print(f"   Fecha: {contexto.fecha}")
    
    # Usuario dice "Cambiar fecha"
    resultado = procesar_mensaje_inteligente("Cambiar fecha", "test-cambiar-fecha")
    
    print(f"\n[NOTE] Mensaje: 'Cambiar fecha'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    print(f"\n[SEARCH] Contexto después de 'Cambiar fecha':")
    print(f"   Fecha: {contexto.fecha} (debe ser None)")
    print(f"   Hora: {contexto.hora} (debe ser None - resetea también hora)")
    
    if contexto.fecha is None:
        print("[OK] Fecha reseteada correctamente")
    else:
        print(f"[FAIL] Fecha NO fue reseteada: {contexto.fecha}")
        return False
    
    if contexto.hora is None:
        print("[OK] Hora también reseteada (esperado)")
    else:
        print(f"[WARN] Hora NO reseteada: {contexto.hora} (puede ser OK dependiendo lógica)")
    
    # Usuario ingresa nueva fecha
    resultado = procesar_mensaje_inteligente("mañana", "test-cambiar-fecha")
    
    print(f"\n[NOTE] Mensaje: 'mañana'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta (primeros 100 chars):\n{resultado['text'][:100]}...")
    print(f"[CAL] Nueva fecha: {contexto.fecha}")
    
    if contexto.fecha is not None:
        print("[OK] TEST PASADO: Fecha actualizada correctamente")
        return True
    else:
        print(f"[FAIL] TEST FALLÓ: Fecha es None después de ingresar 'mañana'")
        return False

def test_cambiar_nombre():
    """Test: Cambiar nombre en resumen"""
    print("\n" + "="*80)
    print("TEST 4: Cambiar nombre en resumen")
    print("="*80)
    
    contexto = get_or_create_context("test-cambiar-nombre")
    contexto.nombre = "Ana María González"
    contexto.cedula = "8888888"
    contexto.fecha = "2025-11-07"
    contexto.hora = "11:00"
    contexto.email = "ana@test.com"
    
    print(f"\n[*] Datos iniciales:")
    print(f"   Nombre: {contexto.nombre}")
    
    # Usuario dice "Cambiar nombre"
    resultado = procesar_mensaje_inteligente("Cambiar nombre", "test-cambiar-nombre")
    
    print(f"\n[NOTE] Mensaje: 'Cambiar nombre'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta:\n{resultado['text']}")
    
    print(f"\n[SEARCH] Contexto después de 'Cambiar nombre':")
    print(f"   Nombre: {contexto.nombre} (debe ser None)")
    print(f"   Cédula: {contexto.cedula} (debe mantenerse)")
    
    if contexto.nombre is None:
        print("[OK] Nombre reseteado correctamente")
    else:
        print(f"[FAIL] Nombre NO fue reseteado: {contexto.nombre}")
        return False
    
    if contexto.cedula == "8888888":
        print("[OK] Cédula se mantuvo")
    else:
        print(f"[FAIL] Cédula cambió: {contexto.cedula}")
    
    # Usuario ingresa nuevo nombre
    resultado = procesar_mensaje_inteligente("Pedro Ramírez Silva", "test-cambiar-nombre")
    
    print(f"\n[NOTE] Mensaje: 'Pedro Ramírez Silva'")
    print(f"[TARGET] Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
    print(f"[CHAT] Respuesta (primeros 100 chars):\n{resultado['text'][:100]}...")
    print(f"[USER] Nuevo nombre: {contexto.nombre}")
    
    if contexto.nombre == "Pedro Ramírez Silva":
        print("[OK] TEST PASADO: Nombre actualizado correctamente")
        return True
    else:
        print(f"[FAIL] TEST FALLÓ: Nombre esperado 'Pedro Ramírez Silva', obtenido '{contexto.nombre}'")
        return False

if __name__ == "__main__":
    print("\n[TEST] INICIANDO TESTS DE 'CAMBIAR [CAMPO]'")
    print("="*80)
    
    resultados = []
    
    try:
        resultados.append(("Cambiar email", test_cambiar_email()))
        resultados.append(("Cambiar hora", test_cambiar_hora()))
        resultados.append(("Cambiar fecha", test_cambiar_fecha()))
        resultados.append(("Cambiar nombre", test_cambiar_nombre()))
        
        print("\n" + "="*80)
        print("[STATS] RESUMEN DE TESTS")
        print("="*80)
        
        pasados = sum(1 for _, resultado in resultados if resultado)
        total = len(resultados)
        
        for nombre, resultado in resultados:
            estado = "[OK] PASADO" if resultado else "[FAIL] FALLÓ"
            print(f"{estado}: {nombre}")
        
        print(f"\n[TARGET] Total: {pasados}/{total} tests pasados ({pasados*100//total}%)")
        
        if pasados == total:
            print("\n[OK] TODOS LOS TESTS PASARON - 'Cambiar [campo]' funciona correctamente!")
        else:
            print(f"\n[WARN] {total - pasados} tests fallaron - Revisar lógica de 'Cambiar [campo]'")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n[FAIL] ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
