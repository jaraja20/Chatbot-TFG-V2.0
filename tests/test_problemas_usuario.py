"""
Test de los problemas reportados por el usuario
"""
# -*- coding: utf-8 -*-

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

def reset_session(session_id):
    if session_id in SESSION_CONTEXTS:
        del SESSION_CONTEXTS[session_id]

print("="*80)
print("PROBLEMA 1: 'Qué trámites hacen?' → Responde con costos")
print("="*80)

session_id = "test_p1"
reset_session(session_id)

resultado = procesar_mensaje_inteligente("Que trámites hacen?", session_id)
print(f"[USER] Usuario: Que trámites hacen?")
print(f"[BOT] Bot: {resultado['text'][:150]}...")
print(f"Intent detectado: {resultado.get('intent')}")
print(f"[OK] ESPERADO: Debe explicar que hacen cédulas, antecedentes, etc, pero el bot solo agenda cédulas")

print("\n" + "="*80)
print("PROBLEMA 2: 'Cambiar cédula' cuando YA tiene cédula → Pide cédula de nuevo")
print("="*80)

session_id = "test_p2"
reset_session(session_id)

# Flujo: agendar → dar cédula → cambiar cédula
procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
procesar_mensaje_inteligente("5264036", session_id)
contexto = get_or_create_context(session_id)
print(f"Cédula guardada: {contexto.cedula}")

resultado = procesar_mensaje_inteligente("Cambiar cédula", session_id)
print(f"\n[USER] Usuario: Cambiar cédula")
print(f"[BOT] Bot: {resultado['text'][:100]}...")
print(f"Intent detectado: {resultado.get('intent')}")
print(f"Cédula después del cambio: {contexto.cedula}")
print(f"[OK] ESPERADO: Debe resetear cédula y pedir nueva (sin volver a preguntar si ya está reseteada)")

print("\n" + "="*80)
print("PROBLEMA 3: 'fecha más cercana/urgencia' → No agenda automáticamente")
print("="*80)

session_id = "test_p3"
reset_session(session_id)

procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
procesar_mensaje_inteligente("5264036", session_id)

resultado = procesar_mensaje_inteligente("Necesito turno con urgencia la fecha más cercana", session_id)
contexto = get_or_create_context(session_id)
print(f"\n[USER] Usuario: Necesito turno con urgencia la fecha más cercana")
print(f"[BOT] Bot: {resultado['text'][:150]}...")
print(f"Intent detectado: {resultado.get('intent')}")
print(f"Fecha asignada: {contexto.fecha}")
print(f"[OK] ESPERADO: Debe detectar urgencia y asignar automáticamente mañana o fecha más cercana")

print("\n" + "="*80)
print("PROBLEMA 4: Cédulas con espacios ('148 65 248', '1 2 3 4 5 6 7 8')")
print("="*80)

session_id = "test_p4"
reset_session(session_id)

procesar_mensaje_inteligente("Quiero agendar un turno", session_id)

resultado1 = procesar_mensaje_inteligente("148 65 248", session_id)
contexto = get_or_create_context(session_id)
print(f"\n[USER] Usuario: 148 65 248")
print(f"[BOT] Bot: {resultado1['text'][:100]}...")
print(f"Intent: {resultado1.get('intent')}")
print(f"Cédula guardada: {contexto.cedula}")

reset_session(session_id)
procesar_mensaje_inteligente("Quiero agendar un turno", session_id)

resultado2 = procesar_mensaje_inteligente("1 2 3 4 5 6 7 8", session_id)
contexto = get_or_create_context(session_id)
print(f"\n[USER] Usuario: 1 2 3 4 5 6 7 8")
print(f"[BOT] Bot: {resultado2['text'][:100]}...")
print(f"Intent: {resultado2.get('intent')}")
print(f"Cédula guardada: {contexto.cedula}")
print(f"[OK] ESPERADO: Debe normalizar espacios y extraer '14865248' y '12345678'")
