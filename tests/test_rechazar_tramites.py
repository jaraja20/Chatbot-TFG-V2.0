# -*- coding: utf-8 -*-
from orquestador_inteligente import procesar_mensaje_inteligente, SESSION_CONTEXTS

SESSION_CONTEXTS.clear()

test_cases = [
    "Necesito un pasaporte",
    "Quiero sacar licencia de conducir",
    "Necesito certificado de antecedentes",
    "Quiero agendar turno para cédula"  # Este SÍ debe funcionar
]

for i, mensaje in enumerate(test_cases, 1):
    SESSION_CONTEXTS.clear()
    print(f"\n{'='*80}")
    print(f"TEST {i}: {mensaje}")
    print(f"{'='*80}")
    
    r = procesar_mensaje_inteligente(mensaje, 'test')
    print(f"Intent: {r.get('intent')}")
    print(f"Bot: {r['text'][:120]}...")
    
    if 'pasaporte' in mensaje.lower() or 'licencia' in mensaje.lower() or 'antecedentes' in mensaje.lower():
        if 'EXCLUSIVO' in r['text'] or 'fuera' in r['text'].lower():
            print("[OK] CORRECTO: Rechaza trámite y explica que solo hace cédulas")
        else:
            print("[FAIL] ERROR: Debería rechazar este trámite")
    else:
        if 'EXCLUSIVO' not in r['text']:
            print("[OK] CORRECTO: Acepta trámite de cédula")
        else:
            print("[FAIL] ERROR: No debería rechazar trámite de cédula")
