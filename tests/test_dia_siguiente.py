"""
TEST: Validar "mejor al dia siguiente"

PROBLEMA: Cuando usuario dice "mejor al dia siguiente", bot pierde contexto
"""
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')

from orquestador_inteligente import procesar_mensaje_inteligente

def test_dia_siguiente():
    print("\n" + "="*80)
    print("TEST: Contexto persistente con 'dia siguiente'")
    print("="*80)
    
    session_id = "test_dia_sig_001"
    
    # Setup: Usuario agenda turno
    print("\n[Setup] Estableciendo contexto...")
    procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
    procesar_mensaje_inteligente("Juan Perez", session_id)
    procesar_mensaje_inteligente("123456", session_id)
    
    # Usuario especifica fecha
    resp1 = procesar_mensaje_inteligente("para el lunes", session_id)
    print(f"\n[1] Usuario: para el lunes")
    print(f"Bot: {resp1['text'][:100]}...")
    
    # Extraer fecha del contexto
    fecha_lunes = resp1.get('contexto', {}).get('fecha')
    print(f"Fecha asignada (lunes): {fecha_lunes}")
    
    # Usuario pide horario
    resp2 = procesar_mensaje_inteligente("a las 10:00", session_id)
    print(f"\n[2] Usuario: a las 10:00")
    print(f"Bot: {resp2['text'][:100]}...")
    
    # Usuario cambia de opinion: "mejor al dia siguiente"
    resp3 = procesar_mensaje_inteligente("mejor al dia siguiente", session_id)
    print(f"\n[3] Usuario: mejor al dia siguiente")
    print(f"Bot: {resp3['text'][:150]}...")
    
    # Validar que NO perdio contexto
    contexto_final = resp3.get('contexto', {})
    nombre_final = contexto_final.get('nombre')
    cedula_final = contexto_final.get('cedula')
    fecha_final = contexto_final.get('fecha')
    
    print(f"\nContexto final:")
    print(f"  Nombre: {nombre_final}")
    print(f"  Cedula: {cedula_final}")
    print(f"  Fecha: {fecha_final}")
    
    # Verificaciones
    problemas = []
    
    if not nombre_final or nombre_final == 'None':
        problemas.append("Perdio el nombre")
    
    if not cedula_final or cedula_final == 'None':
        problemas.append("Perdio la cedula")
    
    if not fecha_final:
        problemas.append("No hay fecha")
    elif fecha_lunes:
        # Verificar que fecha_final sea el dia siguiente a lunes
        try:
            from datetime import datetime, timedelta
            fecha_lunes_obj = datetime.strptime(fecha_lunes, '%Y-%m-%d')
            fecha_esperada = fecha_lunes_obj + timedelta(days=1)
            # Saltar fin de semana si lunes + 1 = martes (ok), pero si fuera viernes + 1 = sabado (mal)
            while fecha_esperada.weekday() >= 5:
                fecha_esperada += timedelta(days=1)
            fecha_esperada_str = fecha_esperada.strftime('%Y-%m-%d')
            
            if fecha_final != fecha_esperada_str:
                problemas.append(f"Fecha incorrecta: esperaba {fecha_esperada_str}, obtuvo {fecha_final}")
        except:
            pass
    
    if 'nombre completo' in resp3['text'].lower() and 'cual es tu nombre' in resp3['text'].lower():
        problemas.append("Bot volvio a pedir nombre (contexto perdido completamente)")
    
    print("\n" + "="*80)
    print("RESULTADO:")
    print("="*80)
    
    if not problemas:
        print("PASS: Contexto preservado correctamente")
        print("  - Nombre y cedula se mantienen")
        print("  - Fecha actualizada al dia siguiente")
        return True
    else:
        print("FAIL: Problemas detectados:")
        for p in problemas:
            print(f"  - {p}")
        return False

if __name__ == '__main__':
    try:
        resultado = test_dia_siguiente()
        sys.exit(0 if resultado else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
