"""
Test rápido de motor difuso con casos fallidos
"""
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "flask-chatbot"))

from razonamiento_difuso import clasificar_con_logica_difusa

# Casos que fallaron en el mega test
casos_fallidos = [
    ('cuanto bale sacar la cedula?', 'consultar_costo'),
    ('documentos', 'consultar_requisitos'),
    ('buenas, para cuando hay hueco?', 'consultar_disponibilidad'),
    ('vieja, necesito sacar turno urgente', 'agendar_turno'),
    ('dame un dia intermedio de la semana', 'consultar_disponibilidad'),
    ('no, esa hora no me sirve', 'negacion'),
    ('mejor otro día', 'negacion'),
    ('cancelar', 'cancelar'),
    ('tienen temprano?', 'frase_ambigua'),
]

print("=" * 70)
print("TEST: Motor Difuso con Casos Fallidos del Mega Test")
print("=" * 70)

correctos = 0
total = len(casos_fallidos)

for i, (mensaje, esperado) in enumerate(casos_fallidos, 1):
    intent_fuzzy, score_fuzzy = clasificar_con_logica_difusa(mensaje)
    correcto = "[OK]" if intent_fuzzy == esperado else "[FAIL]"
    
    if intent_fuzzy == esperado:
        correctos += 1
    
    print(f"\n[{i}/{total}] \"{mensaje}\"")
    print(f"   Esperado: {esperado}")
    print(f"   Fuzzy:    {intent_fuzzy} ({score_fuzzy:.2f}) {correcto}")

print("\n" + "=" * 70)
print(f"[STATS] Resultado: {correctos}/{total} correctos ({correctos/total*100:.1f}%)")
print("=" * 70)

if __name__ == "__main__":
    # Test pasa si al menos el 80% son correctos
    porcentaje = (correctos/total) * 100
    if porcentaje >= 80:
        print("[SUCCESS] Test completado exitosamente")
        sys.exit(0)
    else:
        print(f"[FAIL] Solo {porcentaje:.1f}% correcto, se requiere 80%")
        sys.exit(1)
