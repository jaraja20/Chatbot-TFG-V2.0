# -*- coding: utf-8 -*-
from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

SESSION_CONTEXTS.clear()
print("1. Agendar turno")
r1 = procesar_mensaje_inteligente('Quiero agendar', 'test')
print(f"Bot: {r1['text'][:80]}")

print("\n2. Dar cédula")
r2 = procesar_mensaje_inteligente('5264036', 'test')
ctx = get_or_create_context('test')
print(f"Bot: {r2['text'][:80]}")
print(f"Cédula guardada: {ctx.cedula}")

print("\n3. Cambiar cédula")
r3 = procesar_mensaje_inteligente('Cambiar cédula', 'test')
ctx = get_or_create_context('test')
print(f"Bot: {r3['text'][:80]}")
print(f"Cédula después de cambiar: {ctx.cedula}")
print(f"Campo en cambio: {ctx.campo_en_cambio}")

if "nueva cédula" in r3['text'] or ctx.cedula is None:
    print("[OK] CORRECTO: Resetea cédula y pide nueva (mensaje apropiado)")
else:
    print("[FAIL] ERROR: No maneja correctamente el cambio")
