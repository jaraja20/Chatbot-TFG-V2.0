"""Test para oraciones compuestas y contextos complejos"""

from orquestador_inteligente import procesar_mensaje_inteligente
import time

session_id = f"test_compuesto_{int(time.time())}"

print("="*70)
print("TEST: Oraciones Compuestas y Contextos Complejos")
print("="*70)

casos = [
    {
        'mensaje': 'quiero para la proxima semana, que dia hay disponible?',
        'intent_esperado': 'consultar_disponibilidad',
        'descripcion': 'Consulta con tiempo + pregunta disponibilidad'
    },
    {
        'mensaje': 'necesito turno para la proxima semana, que dia tenes disponible?',
        'intent_esperado': 'consultar_disponibilidad',
        'descripcion': 'Necesito turno + consulta disponibilidad'
    },
    {
        'mensaje': 'quiero agendar para la proxima semana',
        'intent_esperado': 'agendar_turno',
        'descripcion': 'Agendar con tiempo futuro'
    },
    {
        'mensaje': 'hola, necesito turno pero no se cuanto cuesta',
        'intent_esperado': 'agendar_turno',
        'descripcion': 'Múltiples intents, pero prioridad agendar'
    },
    {
        'mensaje': 'que dias tienen disponible la proxima semana?',
        'intent_esperado': 'consultar_disponibilidad',
        'descripcion': 'Pregunta directa sobre disponibilidad'
    },
    {
        'mensaje': 'para cuando hay turnos disponibles?',
        'intent_esperado': 'consultar_disponibilidad',
        'descripcion': 'Consulta temporal abierta'
    },
]

exitosos = 0
fallidos = 0

for i, caso in enumerate(casos, 1):
    print(f"\n[Test {i}] {caso['descripcion']}")
    print(f"  Mensaje: '{caso['mensaje']}'")
    
    resultado = procesar_mensaje_inteligente(caso['mensaje'], session_id)
    intent_detectado = resultado.get('intent')
    confianza = resultado.get('confidence', 0)
    
    if intent_detectado == caso['intent_esperado']:
        print(f"  ✅ OK - Intent: {intent_detectado} ({confianza:.2%})")
        exitosos += 1
    else:
        print(f"  ❌ FAIL")
        print(f"     Esperado: {caso['intent_esperado']}")
        print(f"     Detectado: {intent_detectado} ({confianza:.2%})")
        fallidos += 1

print("\n" + "="*70)
print(f"RESULTADOS: {exitosos}/{len(casos)} exitosos ({exitosos/len(casos)*100:.1f}%)")
if fallidos > 0:
    print(f"⚠️  {fallidos} casos fallaron")
else:
    print("✅ Todos los casos pasaron correctamente!")
print("="*70)
