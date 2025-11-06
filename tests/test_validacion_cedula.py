"""
Test de validación de formatos de cédula
"""
# -*- coding: utf-8 -*-

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

def reset_session(session_id):
    if session_id in SESSION_CONTEXTS:
        del SESSION_CONTEXTS[session_id]

print("="*80)
print("TEST: Validación de formatos de cédula")
print("="*80)

test_cases = [
    {
        'cedula': '1516500',
        'descripcion': 'Sin separadores (VÁLIDO)',
        'esperado': 'aceptar'
    },
    {
        'cedula': '1.516.500',
        'descripcion': 'Con puntos estándar (VÁLIDO)',
        'esperado': 'aceptar'
    },
    {
        'cedula': '1 516 500',
        'descripcion': 'Con espacios estándar (VÁLIDO)',
        'esperado': 'aceptar'
    },
    {
        'cedula': '148 65 248',
        'descripcion': 'Espacios dispersos irregulares (INVÁLIDO)',
        'esperado': 'rechazar'
    },
    {
        'cedula': '1 2 3 4 5 6 7',
        'descripcion': 'Dígitos separados uno por uno (INVÁLIDO)',
        'esperado': 'rechazar'
    },
    {
        'cedula': '1 2 3 4 5 6 7 8',
        'descripcion': 'Dígitos separados uno por uno 8 dígitos (INVÁLIDO)',
        'esperado': 'rechazar'
    }
]

for i, caso in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {caso['descripcion']}")
    print(f"{'='*80}")
    
    session_id = f"test_cedula_{i}"
    reset_session(session_id)
    
    # Flujo: agendar turno
    procesar_mensaje_inteligente("Quiero agendar un turno", session_id)
    
    # Usuario da cédula
    print(f"[USER] Usuario: {caso['cedula']}")
    resultado = procesar_mensaje_inteligente(caso['cedula'], session_id)
    contexto = get_or_create_context(session_id)
    
    print(f"[BOT] Bot: {resultado['text'][:120]}...")
    print(f"Intent: {resultado.get('intent')}")
    
    if caso['esperado'] == 'aceptar':
        cedula_esperada = caso['cedula'].replace('.', '').replace(' ', '')
        if contexto.cedula == cedula_esperada:
            print(f"[OK] CORRECTO: Cédula aceptada y normalizada a {contexto.cedula}")
        else:
            print(f"[FAIL] ERROR: Esperaba cédula '{cedula_esperada}', obtuvo '{contexto.cedula}'")
    else:  # rechazar
        if resultado.get('intent') == 'cedula_invalida' or 'formato de cédula no es válido' in resultado['text'].lower():
            print(f"[OK] CORRECTO: Formato rechazado con mensaje de error")
        elif contexto.cedula is None:
            print(f"[FAIL] PARCIAL: No aceptó cédula pero no mostró mensaje específico de error")
        else:
            print(f"[FAIL] ERROR: No debería haber aceptado la cédula, pero guardó: {contexto.cedula}")

print("\n" + "="*80)
print("FIN DEL TEST")
print("="*80)
