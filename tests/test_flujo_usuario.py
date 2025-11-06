"""
Test del flujo completo simulando el caso reportado por el usuario
"""
# -*- coding: utf-8 -*-

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

def reset_session(session_id):
    if session_id in SESSION_CONTEXTS:
        del SESSION_CONTEXTS[session_id]

session_id = "test_usuario_fecha"

print("="*70)
print("SIMULACIÓN DEL FLUJO DEL USUARIO")
print("="*70)

# Reset
reset_session(session_id)

# Paso 1: Usuario quiere agendar
print("\n[USER] Usuario: Quiero agendar un turno")
resultado = procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
print(f"[BOT] Bot: {resultado['text'][:100]}...")

# Paso 2: Usuario da cédula
print("\n[USER] Usuario: 5264036")
resultado = procesar_mensaje_inteligente("5264036", session_id)
print(f"[BOT] Bot: {resultado['text'][:100]}...")

# Paso 3: Usuario da fecha en formato texto
print("\n[USER] Usuario: 15 de Noviembre")
resultado = procesar_mensaje_inteligente("15 de Noviembre", session_id)
print(f"[BOT] Bot: {resultado['text'][:200]}...")

# Verificar contexto
contexto = get_or_create_context(session_id)
print("\n" + "="*70)
print("VERIFICACIÓN DE CONTEXTO")
print("="*70)
print(f"Fecha guardada: {contexto.fecha}")
print(f"Intent detectado: {resultado.get('intent')}")
print(f"Confianza: {resultado.get('confidence', 0):.2f}")

if contexto.fecha == "2025-11-15":
    print("\n[OK] ¡ÉXITO! La fecha se detectó correctamente")
else:
    print(f"\n[FAIL] ERROR: Fecha esperada '2025-11-15', obtenida '{contexto.fecha}'")
