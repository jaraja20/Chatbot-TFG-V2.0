# -*- coding: utf-8 -*-
from orquestador_inteligente import procesar_mensaje_inteligente, SESSION_CONTEXTS

SESSION_CONTEXTS.clear()

print("TEST: '¿Qué trámites hacen?'")
print("="*80)

r = procesar_mensaje_inteligente('Qué trámites hacen?', 'test')
print(f"Intent: {r.get('intent')}")
print(f"\nBot:\n{r['text']}")

if 'cédula' in r['text'] and 'antecedentes' in r['text'] and 'chatbot' in r['text'].lower():
    print("\n[OK] CORRECTO: Explica los servicios del departamento y aclara que el bot solo agenda cédulas")
else:
    print("\n[FAIL] ERROR: Respuesta no apropiada")
