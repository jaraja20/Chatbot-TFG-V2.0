"""Test rápido para verificar reconocimiento de cédulas con puntos"""

from orquestador_inteligente import procesar_mensaje_inteligente
import time

session_id = f"test_{int(time.time())}"

print("="*60)
print("TEST: Reconocimiento de Cédulas con Puntos")
print("="*60)

# Test 1: Cédula con puntos en frase
print("\n[Test 1] Mensaje: 'mi cedula es 25.251.654'")
resultado1 = procesar_mensaje_inteligente('mi cedula es 25.251.654', session_id)
print(f"  Intent: {resultado1.get('intent')}")
print(f"  Entidades: {resultado1.get('entities')}")
print(f"  Confianza: {resultado1.get('confidence', 0):.2%}")

# Test 2: Solo cédula con puntos
print("\n[Test 2] Mensaje: '25.251.654'")
resultado2 = procesar_mensaje_inteligente('25.251.654', session_id)
print(f"  Intent: {resultado2.get('intent')}")
print(f"  Entidades: {resultado2.get('entities')}")
print(f"  Confianza: {resultado2.get('confidence', 0):.2%}")

# Test 3: Cédula sin puntos (control)
print("\n[Test 3] Mensaje: 'mi cedula es 1234567'")
resultado3 = procesar_mensaje_inteligente('mi cedula es 1234567', session_id)
print(f"  Intent: {resultado3.get('intent')}")
print(f"  Entidades: {resultado3.get('entities')}")
print(f"  Confianza: {resultado3.get('confidence', 0):.2%}")

# Test 4: Cédula con puntos corta
print("\n[Test 4] Mensaje: '2.123.456'")
resultado4 = procesar_mensaje_inteligente('2.123.456', session_id)
print(f"  Intent: {resultado4.get('intent')}")
print(f"  Entidades: {resultado4.get('entities')}")
print(f"  Confianza: {resultado4.get('confidence', 0):.2%}")

print("\n" + "="*60)
print("✓ Tests completados")
print("="*60)
