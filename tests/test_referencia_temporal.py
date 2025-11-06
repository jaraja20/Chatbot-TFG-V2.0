"""
Test de detección de referencias temporales aisladas
Verifica que "para el jueves" se detecte como agendar_turno cuando hay contexto previo
"""
# -*- coding: utf-8 -*-

import sys
import re

# Simular mensaje
mensajes_test = [
    "para el jueves",
    "para el próximo jueves",
    "el jueves",
    "próximo jueves",
    "para mañana",
    "mañana",
    "para el lunes",
    "el próximo martes",
    "esta semana",
    "próxima semana"
]

# Patrones agregados
PATRONES_AGENDAR = [
    r'^\s*para\s+(el\s+)?(pr[oó]ximo|proxima|pr[oó]xima)\s+(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s*$',
    r'^\s*para\s+(el\s+)?(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s*$',
    r'^\s*(el\s+)?(pr[oó]ximo|proxima|pr[oó]xima)\s+(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s*$',
    r'^\s*(el\s+)?(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+pr[oó]xim[oa]\s*$',
    r'^\s*para\s+(ma[ñn]ana|hoy|pasado\s+ma[ñn]ana)\s*$',
    r'^\s*para\s+(el\s+dia|la\s+fecha)\s+\d{1,2}\s*$',
    r'^\s*(ma[ñn]ana|hoy|pasado)\s*$',
]

print("[TEST] TEST DE DETECCIÓN DE REFERENCIAS TEMPORALES")
print("=" * 60)

for mensaje in mensajes_test:
    mensaje_lower = mensaje.lower()
    detectado = False
    patron_match = None
    
    for patron in PATRONES_AGENDAR:
        if re.search(patron, mensaje_lower):
            detectado = True
            patron_match = patron[:50] + "..." if len(patron) > 50 else patron
            break
    
    if detectado:
        print(f"[OK] '{mensaje}' → DETECTADO como agendar_turno")
    else:
        print(f"[FAIL] '{mensaje}' → NO DETECTADO")

print("\n" + "=" * 60)
print("[*] RESUMEN:")
print(f"Total mensajes: {len(mensajes_test)}")
print(f"Detectados: {sum(1 for m in mensajes_test if any(re.search(p, m.lower()) for p in PATRONES_AGENDAR))}")
print("\n[OK] Si todos están detectados, el patrón funciona correctamente")
