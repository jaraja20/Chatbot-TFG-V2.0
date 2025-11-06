"""
Test de detección de urgencia
"""
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "flask-chatbot"))

from razonamiento_difuso import clasificar_con_logica_difusa

def main():
    casos_urgencia = [
        "lo antes posible porfavor",
        "estoy apurado necesito ya",
        "urgente",
        "necesito turno rapido",
        "cuanto antes mejor",
        "ahora mismo",
    ]

    print("="*60)
    print("[*] TEST DE DETECCIÓN DE URGENCIA")
    print("="*60)

    correctos = 0
    total = len(casos_urgencia)
    
    for caso in casos_urgencia:
        intent, conf = clasificar_con_logica_difusa(caso, threshold=0.3)
        es_correcto = intent == "frase_ambigua"
        emoji = "[OK]" if es_correcto else "[FAIL]"
        print(f"{emoji} '{caso}'")
        print(f"   → {intent} ({conf:.2f})")
        print()
        if es_correcto:
            correctos += 1

    print("="*60)
    print(f"\n[RESULT] Casos correctos: {correctos}/{total}")
    
    if correctos == total:
        print("[SUCCESS] Test completado exitosamente")
        return 0
    else:
        print(f"[FAIL] Fallaron {total - correctos} casos")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
