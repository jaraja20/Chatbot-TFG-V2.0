"""
Test para verificar detección de "quiero hablar con alguien" → consultar_ubicacion
"""
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "flask-chatbot"))

from orquestador_inteligente import procesar_mensaje_inteligente

def test_contacto_humano():
    print("[TEST] TEST: Detección de contacto humano")
    print("=" * 60)
    
    casos = [
        "Quiero hablar con alguien",
        "necesito hablar con una persona",
        "puedo hablar con un operador",
        "contacto humano",
        "hablar con alguien",
        "como me comunico con alguien",
        "kiero ablar con alguien",  # Ortografía extrema
    ]
    
    correctos = 0
    for i, mensaje in enumerate(casos, 1):
        session_id = f"test_contacto_{i}"
        respuesta = procesar_mensaje_inteligente(mensaje, session_id)
        
        # Verificar que la respuesta contenga los números de contacto
        tiene_numeros = ("+595 976 200472" in respuesta or 
                        "+595 976 200641" in respuesta)
        
        if tiene_numeros:
            print(f"[OK] {i}. '{mensaje}' → Mostró contactos")
            correctos += 1
        else:
            print(f"[FAIL] {i}. '{mensaje}' → NO mostró contactos")
            respuesta_str = str(respuesta)[:100] if respuesta else "None"
            print(f"   Respuesta: {respuesta_str}...")
    
    print("=" * 60)
    print(f"[TARGET] Resultado: {correctos}/{len(casos)} correctos ({correctos/len(casos)*100:.1f}%)")
    
    if correctos == len(casos):
        print("[*] ¡TODOS LOS CASOS PASARON!")
    else:
        print("[WARN] Algunos casos fallaron")
    
    return correctos == len(casos)

if __name__ == "__main__":
    try:
        exito = test_contacto_humano()
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
