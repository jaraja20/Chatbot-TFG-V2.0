"""
Test de detección de confirmación (affirm)
"""
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "flask-chatbot"))

from razonamiento_difuso import clasificar_con_logica_difusa

def main():
    casos_affirm = [
        "si",
        "sí",
        "confirmo",
        "acepto",
        "ok",
        "vale",
        "está bien",
        "de acuerdo",
        "correcto",
        "exacto",
    ]

    print("="*60)
    print("[OK] TEST DE DETECCIÓN DE CONFIRMACIÓN (affirm)")
    print("="*60)

    correctos = 0
    total = len(casos_affirm)
    
    for caso in casos_affirm:
        intent, conf = clasificar_con_logica_difusa(caso, threshold=0.3)
        es_correcto = intent == "affirm"
        emoji = "[OK]" if es_correcto else "[FAIL]"
        print(f"{emoji} '{caso}' → {intent} ({conf:.2f})")
        if es_correcto:
            correctos += 1

    print("="*60)
    print(f"\n[OK] Casos correctos: {correctos}/{total}")
    
    # Retornar código de salida apropiado
    if correctos == total:
        print("\n[SUCCESS] Test completado exitosamente")
        return 0
    else:
        print(f"\n[FAIL] Fallaron {total - correctos} casos")
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
