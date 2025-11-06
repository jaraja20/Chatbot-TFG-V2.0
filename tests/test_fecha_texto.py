"""
Test rápido para validar detección de fechas en formato "DD de Mes"
"""
# -*- coding: utf-8 -*-

from orquestador_inteligente import extraer_entidades, SessionContext

# Test cases
test_cases = [
    "15 de Noviembre",
    "20 de diciembre",
    "5 de enero",
    "el 10 de marzo",
    "para el 25 de abril"
]

print("="*60)
print("TEST: Detección de fechas en formato 'DD de Mes'")
print("="*60)

ctx = SessionContext('test')

for msg in test_cases:
    result = extraer_entidades(msg, 'informar_fecha', ctx)
    fecha = result.get('fecha', 'NO DETECTADA')
    print(f"\n[NOTE] Mensaje: {msg}")
    print(f"   Fecha: {fecha}")
    
print("\n" + "="*60)
print("TEST COMPLETADO")
print("="*60)
