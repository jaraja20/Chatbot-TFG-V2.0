# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "flask-chatbot"))

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context, SESSION_CONTEXTS

def main():
    SESSION_CONTEXTS.clear()
    procesar_mensaje_inteligente('Quiero agendar', 'test')
    procesar_mensaje_inteligente('5264036', 'test')
    r = procesar_mensaje_inteligente('Necesito turno con urgencia la fecha más cercana', 'test')
    ctx = get_or_create_context('test')
    
    print("[TEST] Test de urgencia rápido")
    print("="*60)
    print(f"Intent: {r.get('intent')}")
    print(f"Fecha: {ctx.fecha}")
    print(f"Bot: {r['text'][:150]}")
    print("="*60)
    
    # Verificar que se asignó una fecha cercana
    if ctx.fecha:
        print("[SUCCESS] Test completado - Fecha asignada")
        return 0
    else:
        print("[FAIL] No se asignó fecha")
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
