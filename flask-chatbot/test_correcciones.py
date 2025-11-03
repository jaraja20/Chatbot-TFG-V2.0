"""
Test de todas las correcciones implementadas
"""
import sys
sys.path.insert(0, r'c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot')

from orquestador_inteligente import procesar_mensaje_inteligente, SessionContext, get_or_create_context

print("\n" + "="*70)
print("TEST DE CORRECCIONES")
print("="*70)

# Test 1: Gorilla Insano debe ser rechazado
print("\n📋 TEST 1: Rechazar 'gorilla insano'")
print("-" * 70)
contexto = SessionContext('test1')
resultado = procesar_mensaje_inteligente('gorilla insano', 'test1')
print(f"Intent: {resultado['intent']}")
print(f"Respuesta: {resultado['text'][:100]}...")
assert resultado['intent'] == 'desconocido', "❌ No rechazó 'gorilla insano'"
print("✅ CORRECTO: Rechazó 'gorilla insano'\n")

# Test 2: Mantener contexto entre mensajes
print("\n📋 TEST 2: Mantener contexto (mismo session_id)")
print("-" * 70)
SESSION_ID = 'test_permanente'

# Mensaje 1: Agendar turno
resultado1 = procesar_mensaje_inteligente('Quiero agendar un turno', SESSION_ID)
print(f"Mensaje 1: {resultado1['text'][:50]}...")

# Mensaje 2: Dar nombre
resultado2 = procesar_mensaje_inteligente('Juan Pérez', SESSION_ID)
print(f"Mensaje 2: {resultado2['text'][:50]}...")

# Mensaje 3: Dar cédula
resultado3 = procesar_mensaje_inteligente('245343', SESSION_ID)
print(f"Mensaje 3: {resultado3['text'][:50]}...")

# Verificar que el contexto se mantuvo
contexto_final = get_or_create_context(SESSION_ID)
print(f"\n📊 Contexto final:")
print(f"- Nombre: {contexto_final.nombre}")
print(f"- Cédula: {contexto_final.cedula}")

assert contexto_final.nombre == "Juan Pérez", "❌ No guardó el nombre"
assert contexto_final.cedula == "245343", "❌ No guardó la cédula"
print("✅ CORRECTO: Contexto mantenido correctamente\n")

# Test 3: "Esta semana" vs "Próxima semana"
print("\n📋 TEST 3: Detectar 'esta semana' y 'próxima semana'")
print("-" * 70)

# Esta semana
resultado_esta = procesar_mensaje_inteligente('que tal la disponibilidad para esta semana?', 'test3')
print(f"Esta semana: {resultado_esta['text'][:80]}...")
assert 'esta semana' in resultado_esta['text'].lower(), "❌ No detectó 'esta semana'"
print("✅ CORRECTO: Detectó 'esta semana'\n")

# Próxima semana
resultado_proxima = procesar_mensaje_inteligente('que tal la disponibilidad para la proxima semana?', 'test4')
print(f"Próxima semana: {resultado_proxima['text'][:80]}...")
assert 'próxima semana' in resultado_proxima['text'].lower(), "❌ No detectó 'próxima semana'"
print("✅ CORRECTO: Detectó 'próxima semana'\n")

# Test 4: Recordar fecha en conversación
print("\n📋 TEST 4: Recordar fecha cuando se menciona día específico")
print("-" * 70)
SESSION_ID_4 = 'test_fecha'

# Establecer contexto
procesar_mensaje_inteligente('Quiero agendar un turno', SESSION_ID_4)
procesar_mensaje_inteligente('Juan Pérez', SESSION_ID_4)
procesar_mensaje_inteligente('245343', SESSION_ID_4)
procesar_mensaje_inteligente('que tal la disponibilidad para la proxima semana?', SESSION_ID_4)

# Ahora pedir para el lunes 10
resultado_lunes = procesar_mensaje_inteligente('que horarios hay para el lunes 10?', SESSION_ID_4)
print(f"Respuesta: {resultado_lunes['text'][:100]}...")

# Verificar contexto
contexto_4 = get_or_create_context(SESSION_ID_4)
print(f"\n📊 Contexto:")
print(f"- Nombre: {contexto_4.nombre}")
print(f"- Cédula: {contexto_4.cedula}")
print(f"- Fecha: {contexto_4.fecha}")

assert contexto_4.nombre == "Juan Pérez", "❌ Olvidó el nombre"
assert contexto_4.cedula == "245343", "❌ Olvidó la cédula"
print("✅ CORRECTO: Mantuvo nombre y cédula\n")

print("="*70)
print("✅ TODOS LOS TESTS PASARON")
print("="*70)
