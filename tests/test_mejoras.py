"""
Test de las mejoras implementadas
"""
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot')

from orquestador_inteligente import procesar_mensaje_inteligente, SessionContext

# Test 1: Rechazar "macaco volador"
print("\n" + "="*70)
print("TEST 1: Rechazar nombre INVÁLIDO (macaco volador)")
print("="*70)
contexto = SessionContext('test1')
resultado = procesar_mensaje_inteligente('macaco volador', contexto)
print(f"Intent detectado: {resultado['intent']}")
print(f"Confianza: {resultado['confidence']}")
print(f"Respuesta:\n{resultado['text']}")

# Test 2: Consultar disponibilidad para próxima semana
print("\n" + "="*70)
print("TEST 2: Consultar disponibilidad PRÓXIMA SEMANA")
print("="*70)
contexto2 = SessionContext('test2')
resultado2 = procesar_mensaje_inteligente('que tal la disponibilidad para la proxima semana?', contexto2)
print(f"Intent detectado: {resultado2['intent']}")
print(f"Confianza: {resultado2['confidence']}")
print(f"Respuesta:\n{resultado2['text']}")

print("\n" + "="*70)
print("[OK] Tests completados")
print("="*70)
