"""
Test del flujo completo con fecha válida (día laboral)
"""
# -*- coding: utf-8 -*-

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

def reset_session(session_id):
    if session_id in SESSION_CONTEXTS:
        del SESSION_CONTEXTS[session_id]

session_id = "test_fecha_valida"

print("="*70)
print("TEST: Flujo completo con fecha laboral válida")
print("="*70)

# Reset
reset_session(session_id)

# Paso 1: Usuario quiere agendar
print("\n[USER] Usuario: Quiero agendar un turno")
resultado = procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
print(f"[BOT] Bot: {resultado['text'][:80]}...")

# Paso 2: Usuario da cédula
print("\n[USER] Usuario: 5264036")
resultado = procesar_mensaje_inteligente("5264036", session_id)
print(f"[BOT] Bot: {resultado['text'][:80]}...")

# Paso 3: Usuario da fecha válida (LUNES 17 de noviembre)
print("\n[USER] Usuario: 17 de Noviembre")
resultado = procesar_mensaje_inteligente("17 de Noviembre", session_id)
print(f"[BOT] Bot: {resultado['text'][:120]}...")

# Verificar contexto
contexto = get_or_create_context(session_id)
print("\n" + "="*70)
print("VERIFICACIÓN")
print("="*70)
print(f"Intent detectado: {resultado.get('intent')}")
print(f"Confianza: {resultado.get('confidence', 0):.2f}")
print(f"Fecha guardada: {contexto.fecha}")

if contexto.fecha == "2025-11-17":
    print("\n[OK] ¡ÉXITO! La fecha se detectó y guardó correctamente")
    print("[OK] El sistema ahora reconoce fechas en formato 'DD de Mes'")
else:
    print(f"\n[FAIL] ERROR: Fecha esperada '2025-11-17', obtenida '{contexto.fecha}'")

print("\n" + "="*70)
print("TEST ADICIONAL: Fecha en formato abreviado")
print("="*70)

# Reset y test con abreviación
reset_session(session_id)

# Flujo rápido
procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
procesar_mensaje_inteligente("5264036", session_id)

print("\n[USER] Usuario: 18 de nov")
resultado = procesar_mensaje_inteligente("18 de nov", session_id)
print(f"[BOT] Bot: {resultado['text'][:120]}...")

contexto = get_or_create_context(session_id)
print(f"\nIntent: {resultado.get('intent')}")
print(f"Fecha: {contexto.fecha}")

if contexto.fecha == "2025-11-18":
    print("[OK] También funciona con abreviación de mes")
else:
    print(f"[WARN] Fecha detectada: {contexto.fecha}")
