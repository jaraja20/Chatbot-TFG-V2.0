"""
Test rápido del orquestador
"""
import sys
sys.path.insert(0, r'c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot')

from orquestador_inteligente import procesar_mensaje_inteligente, SessionContext

# Test 1: Agendar turno (debe funcionar)
print("\n" + "="*70)
print("TEST 1: Intent de AGENDAR TURNO")
print("="*70)
contexto = SessionContext('test123')
resultado = procesar_mensaje_inteligente('Quiero agendar un turno', contexto)
print(f"Intent detectado: {resultado['intent']}")
print(f"Confianza: {resultado['confidence']}")
print(f"Respuesta:\n{resultado['text']}")

# Test 2: Nombre inválido (debe rechazarse)
print("\n" + "="*70)
print("TEST 2: Nombre INVÁLIDO (yo soy muy loco)")
print("="*70)
contexto = SessionContext('test456')
resultado = procesar_mensaje_inteligente('yo soy muy loco', contexto)
print(f"Intent detectado: {resultado['intent']}")
print(f"Confianza: {resultado['confidence']}")
print(f"Respuesta:\n{resultado['text']}")

# Test 3: Nombre válido (debe aceptarse)
print("\n" + "="*70)
print("TEST 3: Nombre VÁLIDO (Juan Pérez)")
print("="*70)
contexto = SessionContext('test789')
resultado = procesar_mensaje_inteligente('Juan Pérez', contexto)
print(f"Intent detectado: {resultado['intent']}")
print(f"Confianza: {resultado['confidence']}")
print(f"Nombre extraído: {contexto.nombre}")
print(f"Respuesta:\n{resultado['text']}")

print("\n" + "="*70)
print("✅ Tests completados")
print("="*70)
