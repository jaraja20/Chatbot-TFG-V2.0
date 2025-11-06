# -*- coding: utf-8 -*-
from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

SESSION_CONTEXTS.clear()

print("="*80)
print("TEST: Preferencias de horario")
print("="*80)

# Test 1: "No puedo por la mañana"
print("\n1. Usuario: No puedo por la mañana")
r1 = procesar_mensaje_inteligente("No puedo por la mañana", 'test')
ctx = get_or_create_context('test')
print(f"Franja: {ctx.franja_horaria}")
print(f"Fecha asignada: {ctx.fecha}")
print(f"Bot: {r1['text'][:150]}...")

if ctx.franja_horaria == 'tarde' and ctx.fecha:
    print("[OK] CORRECTO: Detecta preferencia de tarde y asigna fecha")
else:
    print(f"[FAIL] ERROR: franja={ctx.franja_horaria}, fecha={ctx.fecha}")

# Test 2: "Después del mediodía"
SESSION_CONTEXTS.clear()
print("\n" + "="*80)
print("2. Usuario: Después del mediodía")
r2 = procesar_mensaje_inteligente("Después del mediodía", 'test2')
ctx2 = get_or_create_context('test2')
print(f"Franja: {ctx2.franja_horaria}")
print(f"Fecha asignada: {ctx2.fecha}")
print(f"Bot: {r2['text'][:150]}...")

if ctx2.franja_horaria == 'tarde' and ctx2.fecha:
    print("[OK] CORRECTO: Detecta 'después del mediodía' como tarde")
else:
    print(f"[FAIL] ERROR: franja={ctx2.franja_horaria}, fecha={ctx2.fecha}")
