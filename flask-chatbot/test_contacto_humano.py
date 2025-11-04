"""
Test para verificar detección de "quiero hablar con alguien" → consultar_ubicacion
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente

def test_contacto_humano():
    print("🧪 TEST: Detección de contacto humano")
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
            print(f"✅ {i}. '{mensaje}' → Mostró contactos")
            correctos += 1
        else:
            print(f"❌ {i}. '{mensaje}' → NO mostró contactos")
            print(f"   Respuesta: {respuesta[:100]}...")
    
    print("=" * 60)
    print(f"🎯 Resultado: {correctos}/{len(casos)} correctos ({correctos/len(casos)*100:.1f}%)")
    
    if correctos == len(casos):
        print("🏆 ¡TODOS LOS CASOS PASARON!")
    else:
        print("⚠️ Algunos casos fallaron")
    
    return correctos == len(casos)

if __name__ == "__main__":
    test_contacto_humano()
