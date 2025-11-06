"""
TEST: Validar fixes para proxima semana

PROBLEMAS:
1. "hay mas dias disponibles la proxima semana" -> No muestra lista
2. Usuario dice "el lunes" despues de recomendacion -> Bot ofrece lunes 17 en vez de lunes 10
"""
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')

from orquestador_inteligente import procesar_mensaje_inteligente

def test_simple():
    print("\n" + "="*80)
    print("TEST: Proxima semana - hay otros dias disponibles")
    print("="*80)
    
    session_id = "test_001"
    
    # Setup
    procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
    procesar_mensaje_inteligente("jhonatan villalba", session_id)
    procesar_mensaje_inteligente("35345", session_id)
    
    # Bot recomienda lunes 10
    resp1 = procesar_mensaje_inteligente("hay disponible la proxima semana?", session_id)
    print("\n[1] Usuario: hay disponible la proxima semana?")
    print(f"Bot: {resp1['text'][:100]}...")
    
    if 'lunes 10' in resp1['text'].lower():
        print("OK: Bot recomienda lunes 10")
    
    # Usuario pregunta por otros dias (sin mencionar "proxima semana")
    resp2 = procesar_mensaje_inteligente("hay otros dias disponibles?", session_id)
    print("\n[2] Usuario: hay otros dias disponibles?")
    print(f"Bot: {resp2['text']}")
    
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    dias_count = sum(1 for d in dias if d in resp2['text'].lower())
    
    print(f"\nDias mostrados: {dias_count}")
    
    if dias_count >= 3:
        print("PROBLEMA 1: RESUELTO (lista completa)")
        p1 = True
    else:
        print("PROBLEMA 1: FALLO (no muestra lista)")
        p1 = False
    
    # Usuario confirma "el lunes"
    resp3 = procesar_mensaje_inteligente("el lunes", session_id)
    print("\n[3] Usuario: el lunes")
    print(f"Bot: {resp3['text'][:100]}...")
    
    if '2025-11-10' in resp3['text']:
        print("PROBLEMA 2: RESUELTO (usa lunes 10)")
        p2 = True
    elif '2025-11-17' in resp3['text']:
        print("PROBLEMA 2: FALLO (usa lunes 17 incorrecto)")
        p2 = False
    else:
        print("PROBLEMA 2: No se puede determinar")
        p2 = False
    
    print("\n" + "="*80)
    print("RESULTADO FINAL:")
    print("="*80)
    print(f"Problema 1 (lista dias): {'PASS' if p1 else 'FAIL'}")
    print(f"Problema 2 (lunes correcto): {'PASS' if p2 else 'FAIL'}")
    
    return p1 and p2

if __name__ == '__main__':
    try:
        resultado = test_simple()
        sys.exit(0 if resultado else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
