"""
Test rápido para verificar detección de modo_desarrollador
"""
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, 'c:\\tfg funcional\\Chatbot-TFG-V2.0\\flask-chatbot')

from orquestador_inteligente import procesar_mensaje_inteligente

# Test
mensajes = ['dashboard', 'modo desarrollador', 'admin']

for msg in mensajes:
    print(f"\n{'='*60}")
    print(f"Probando: '{msg}'")
    print('='*60)
    
    try:
        resultado = procesar_mensaje_inteligente(msg, "test_session_123")
        print(f"[OK] Resultado exitoso:")
        print(f"   Intent: {resultado.get('intent')}")
        print(f"   Text: {resultado.get('text')[:100] if resultado.get('text') else 'None'}...")
        print(f"   Show Dashboard: {resultado.get('show_dashboard_button')}")
        print(f"   Dashboard URL: {resultado.get('dashboard_url')}")
    except Exception as e:
        print(f"[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
