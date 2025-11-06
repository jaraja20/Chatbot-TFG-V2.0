"""
Test: Detección de "próximo [día]" y "para el [día]"
"""
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(__file__))

from orquestador_inteligente import SessionContext, ClasificadorIntentsMejorado, extraer_entidades
from datetime import datetime, timedelta

print("=" * 70)
print("[TEST] TEST: Detección de Próximo Jueves / Para el Día")
print("=" * 70)

clasificador = ClasificadorIntentsMejorado()

# Obtener día actual
hoy = datetime.now()
dia_actual = hoy.strftime('%A')
print(f"\n[CAL] Hoy es: {dia_actual} {hoy.strftime('%Y-%m-%d')}")

# Test cases
casos = [
    "para el próximo jueves",
    "proximo jueves",
    "para el jueves",
    "el próximo viernes",
    "para el lunes",
    "próxima semana jueves",
    "jueves",  # Sin "próximo"
]

print("\n" + "=" * 70)
print("[*] CASOS DE PRUEBA")
print("=" * 70)

for i, mensaje in enumerate(casos, 1):
    print(f"\n[TEST] Test #{i}: '{mensaje}'")
    print("-" * 70)
    
    # Crear contexto limpio
    contexto = SessionContext(session_id=f"test_{i}")
    
    # Clasificar
    intent, confianza = clasificador.clasificar(mensaje, contexto)
    print(f"   Intent: {intent} (confianza: {confianza})")
    
    # Extraer entidades
    entidades = extraer_entidades(mensaje, intent, contexto)
    
    if 'fecha' in entidades:
        fecha_obj = datetime.strptime(entidades['fecha'], '%Y-%m-%d')
        dia_semana = fecha_obj.strftime('%A')
        print(f"   [OK] Fecha detectada: {entidades['fecha']} ({dia_semana})")
        
        # Verificar si es próxima ocurrencia
        dias_diferencia = (fecha_obj - hoy).days
        if dias_diferencia > 0:
            print(f"   [*] Dentro de {dias_diferencia} días")
        elif dias_diferencia == 0:
            print(f"   [*] Es hoy")
        else:
            print(f"   [WARN]  Fecha en el pasado ({abs(dias_diferencia)} días atrás)")
    else:
        print(f"   [FAIL] No se detectó fecha")
    
    if 'proxima_semana' in entidades:
        print(f"   [*] Flag proxima_semana: {entidades['proxima_semana']}")

print("\n" + "=" * 70)
print("[STATS] RESUMEN")
print("=" * 70)

# Calcular próximo jueves manualmente para comparar
dia_actual_num = hoy.weekday()  # 0=Lunes, 3=Jueves
jueves_num = 3
dias_hasta_jueves = (jueves_num - dia_actual_num) % 7
if dias_hasta_jueves == 0:
    dias_hasta_jueves = 7  # Si es jueves hoy, próximo es en 7 días

proximo_jueves = hoy + timedelta(days=dias_hasta_jueves)
print(f"\n[OK] El PRÓXIMO JUEVES debería ser: {proximo_jueves.strftime('%Y-%m-%d')}")

print("\n[IDEA] Los tests con 'próximo jueves', 'para el jueves' deberían detectar:")
print(f"   {proximo_jueves.strftime('%Y-%m-%d')} (Jueves)")

print("\n" + "=" * 70)
