"""
[TEST] TEST: Verificar que bot muestra LISTA de días cuando usuario pregunta por disponibilidad próxima semana

PROBLEMA REPORTADO:
Usuario: "que otros dias disponibles hay la proxima semana?"
Bot (MAL): Solo muestra recomendación de lunes
Bot (BIEN): Debe mostrar lista completa Lunes-Viernes con disponibilidad

CASO DE USO:
1. Usuario dice "quiero turno para proxima semana" → Bot recomienda lunes [OK]
2. Usuario dice "que dias disponibles hay proxima semana" → Bot muestra lista completa [OK]
"""
# -*- coding: utf-8 -*-

import sys
sys.path.append('.')

from orquestador_inteligente import procesar_mensaje_inteligente

def test_lista_disponibilidad_proxima_semana():
    """Test que el bot muestra lista completa cuando usuario pregunta por disponibilidad"""
    
    print("\n" + "="*80)
    print("[TEST] TEST: Lista de días disponibles para próxima semana")
    print("="*80)
    
    # =========================
    # CASO 1: Usuario PIDE turno para próxima semana
    # =========================
    print("\n[*] CASO 1: Usuario dice 'quiero turno para proxima semana'")
    print("-" * 70)
    
    # Primero establecer nombre y cédula
    respuesta_setup1 = procesar_mensaje_inteligente("Juan", "test_001")
    respuesta_setup2 = procesar_mensaje_inteligente("1234567", "test_001")
    
    # Ahora pedir turno para próxima semana
    respuesta1 = procesar_mensaje_inteligente(
        user_message="quiero turno para proxima semana",
        session_id="test_001"
    )
    
    print(f"[BOT] Bot responde: {respuesta1['text'][:200]}...")
    
    # Validar que recomienda un día específico (lunes)
    texto_resp1 = respuesta1['text'].lower()
    if 'lunes' in texto_resp1 and 'te recomiendo' in texto_resp1:
        print("[OK] CORRECTO: Bot recomienda lunes específicamente")
    else:
        print("[FAIL] ERROR: Bot NO recomienda día específico")
        return False
    
    # =========================
    # CASO 2: Usuario PREGUNTA por lista de días disponibles
    # =========================
    print("\n[*] CASO 2: Usuario dice 'que otros dias disponibles hay la proxima semana?'")
    print("-" * 70)
    
    # Nueva sesión
    respuesta_setup3 = procesar_mensaje_inteligente("Maria", "test_002")
    respuesta_setup4 = procesar_mensaje_inteligente("7654321", "test_002")
    
    # Ahora preguntar por disponibilidad
    respuesta2 = procesar_mensaje_inteligente(
        user_message="que otros dias disponibles hay la proxima semana?",
        session_id="test_002"
    )
    
    print(f"[BOT] Bot responde:\n{respuesta2['text']}")
    
    # Validar que muestra lista completa (debe tener varios días)
    texto_resp2 = respuesta2['text'].lower()
    
    # Debe mencionar varios días de la semana
    dias_mencionados = []
    for dia in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']:
        if dia in texto_resp2:
            dias_mencionados.append(dia)
    
    print(f"\n[STATS] Días mencionados en la respuesta: {dias_mencionados}")
    
    if len(dias_mencionados) >= 3:
        print(f"[OK] CORRECTO: Bot muestra lista de {len(dias_mencionados)} días")
    else:
        print(f"[FAIL] ERROR: Bot solo menciona {len(dias_mencionados)} día(s), debería mostrar lista completa")
        return False
    
    # Validar que NO es solo una recomendación de lunes
    if 'te recomiendo el lunes' in texto_resp2 and len(dias_mencionados) == 1:
        print("[FAIL] ERROR: Bot solo recomienda lunes, no muestra lista completa")
        return False
    
    # =========================
    # CASO 3: Variaciones de consulta de disponibilidad
    # =========================
    print("\n[*] CASO 3: Variaciones de consulta de disponibilidad")
    print("-" * 70)
    
    variaciones = [
        "que dias hay disponibles para la proxima semana?",
        "cuales son los dias disponibles?",
        "mostrar disponibilidad de la proxima semana",
        "ver disponibilidad para la proxima semana"
    ]
    
    casos_exitosos = 0
    for idx, msg in enumerate(variaciones):
        # Crear nueva sesión para cada variación
        session_id = f"test_003_{idx}"
        procesar_mensaje_inteligente("Test", session_id)
        procesar_mensaje_inteligente("1111111", session_id)
        
        respuesta = procesar_mensaje_inteligente(
            user_message=msg,
            session_id=session_id
        )
        
        texto = respuesta['text'].lower()
        dias_count = sum(1 for dia in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes'] if dia in texto)
        
        if dias_count >= 3:
            print(f"[OK] '{msg}' → Lista completa ({dias_count} días)")
            casos_exitosos += 1
        else:
            print(f"[WARN] '{msg}' → Solo {dias_count} día(s)")
    
    if casos_exitosos >= 3:
        print(f"\n[OK] {casos_exitosos}/{len(variaciones)} variaciones funcionan correctamente")
    else:
        print(f"\n[FAIL] Solo {casos_exitosos}/{len(variaciones)} variaciones funcionan")
        return False
    
    print("\n" + "="*80)
    print("[OK] TEST COMPLETO: Bot diferencia correctamente entre:")
    print("   - Solicitud de turno → Recomienda día específico (lunes)")
    print("   - Consulta de disponibilidad → Muestra lista completa (L-V)")
    print("="*80)
    
    return True

if __name__ == '__main__':
    try:
        resultado = test_lista_disponibilidad_proxima_semana()
        if resultado:
            print("\n[*] TODOS LOS TESTS PASARON [*]")
            sys.exit(0)
        else:
            print("\n[FAIL] ALGUNOS TESTS FALLARON")
            sys.exit(1)
    except Exception as e:
        print(f"\n[*] ERROR EJECUTANDO TEST: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
