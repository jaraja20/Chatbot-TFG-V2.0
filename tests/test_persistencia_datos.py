"""
Test para verificar que se mantiene la información previa al corregir un dato
"""
# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orquestador_inteligente import SessionContext, procesar_mensaje_inteligente, SESSION_CONTEXTS

def test_mantener_info_previa():
    """
    Verifica que al corregir un dato, se mantengan los demás
    """
    print("="*80)
    print("TEST: Mantener información previa al corregir")
    print("="*80)
    
    from orquestador_inteligente import SESSION_CONTEXTS
    session_id = "test_correccion_123"
    contexto = SessionContext(session_id)
    
    # Simular que el usuario ya dio varios datos
    contexto.nombre = "Nombre Incorrecto Y Quiero Turno"
    contexto.cedula = "1234567"
    contexto.fecha = "2024-01-15"
    contexto.hora = "09:00"
    # No tiene email todavía
    
    SESSION_CONTEXTS[session_id] = contexto
    
    print("\n[*] DATOS INICIALES:")
    print(f"Nombre: {contexto.nombre}")
    print(f"Cédula: {contexto.cedula}")
    print(f"Fecha: {contexto.fecha}")
    print(f"Hora: {contexto.hora}")
    print(f"Email: {contexto.email}")
    
    # Usuario intenta corregir el nombre
    print("\n" + "="*80)
    print("[LOOP] Usuario: 'no mi nombre es solo jhonatan villalba'")
    print("="*80)
    
    respuesta = procesar_mensaje_inteligente("no mi nombre es solo jhonatan villalba", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    print(f"Intent detectado: {respuesta.get('intent')}")
    
    # Verificar que se reseteó el nombre pero NO los demás datos
    print(f"\n[STATS] Estado del contexto después de detectar corrección:")
    print(f"Nombre: {contexto.nombre} (debe ser None para pedir nuevo)")
    print(f"Cédula: {contexto.cedula} (debe mantenerse: 1234567)")
    print(f"Fecha: {contexto.fecha} (debe mantenerse: 2024-01-15)")
    print(f"Hora: {contexto.hora} (debe mantenerse: 09:00)")
    
    # Ahora el usuario da el nombre correcto
    print("\n" + "="*80)
    print("[LOOP] Usuario: 'jhonatan villalba'")
    print("="*80)
    
    respuesta = procesar_mensaje_inteligente("jhonatan villalba", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    
    print(f"\n[STATS] Estado final del contexto:")
    print(f"Nombre: {contexto.nombre}")
    print(f"Cédula: {contexto.cedula}")
    print(f"Fecha: {contexto.fecha}")
    print(f"Hora: {contexto.hora}")
    
    # Verificar que TODO se mantuvo excepto el nombre que se corrigió
    if contexto.cedula == "1234567" and contexto.fecha == "2024-01-15" and contexto.hora == "09:00":
        if contexto.nombre and "Jhonatan Villalba" in contexto.nombre:
            print("\n[OK] ¡ÉXITO! Los datos previos se mantuvieron y el nombre se corrigió")
            print("\n[*] Verificación:")
            print(f"  [OK] Nombre corregido: {contexto.nombre}")
            print(f"  [OK] Cédula mantenida: {contexto.cedula}")
            print(f"  [OK] Fecha mantenida: {contexto.fecha}")
            print(f"  [OK] Hora mantenida: {contexto.hora}")
        else:
            print(f"\n[FAIL] ERROR: El nombre no se corrigió correctamente: {contexto.nombre}")
    else:
        print("\n[FAIL] ERROR: Se perdieron datos previos")
        print(f"  Cédula esperada: 1234567, actual: {contexto.cedula}")
        print(f"  Fecha esperada: 2024-01-15, actual: {contexto.fecha}")
        print(f"  Hora esperada: 09:00, actual: {contexto.hora}")
    
    print("\n" + "="*80)

def test_cambiar_email_mantiene_resto():
    """
    Verifica que al cambiar el email, se mantengan los demás datos
    """
    print("\n\n" + "="*80)
    print("TEST: Cambiar email manteniendo todo lo demás")
    print("="*80)
    
    from orquestador_inteligente import SESSION_CONTEXTS
    session_id = "test_email_123"
    contexto = SessionContext(session_id)
    
    # Usuario con todos los datos completos
    contexto.nombre = "Pedro Gómez"
    contexto.cedula = "7777777"
    contexto.fecha = "2024-01-25"
    contexto.hora = "10:30"
    contexto.email = "viejo@example.com"
    
    SESSION_CONTEXTS[session_id] = contexto
    
    print("\n[*] DATOS INICIALES:")
    print(f"Nombre: {contexto.nombre}")
    print(f"Cédula: {contexto.cedula}")
    print(f"Fecha: {contexto.fecha}")
    print(f"Hora: {contexto.hora}")
    print(f"Email: {contexto.email}")
    
    # Usuario dice que se equivocó en el email
    print("\n" + "="*80)
    print("[LOOP] Usuario: 'me equivoque, mi email es nuevo@example.com'")
    print("="*80)
    
    respuesta = procesar_mensaje_inteligente("me equivoque, mi email es nuevo@example.com", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    
    print(f"\n[STATS] Estado final del contexto:")
    print(f"Nombre: {contexto.nombre}")
    print(f"Cédula: {contexto.cedula}")
    print(f"Fecha: {contexto.fecha}")
    print(f"Hora: {contexto.hora}")
    print(f"Email: {contexto.email}")
    
    # Verificar que todo se mantuvo y el email se actualizó
    if (contexto.nombre == "Pedro Gómez" and 
        contexto.cedula == "7777777" and 
        contexto.fecha == "2024-01-25" and 
        contexto.hora == "10:30"):
        if contexto.email == "nuevo@example.com":
            print("\n[OK] ¡ÉXITO! El email se actualizó y todo lo demás se mantuvo")
        else:
            print(f"\n[FAIL] Email no se actualizó correctamente: {contexto.email}")
    else:
        print("\n[FAIL] ERROR: Se perdieron datos")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print("\n[TEST] INICIANDO PRUEBAS DE PERSISTENCIA DE DATOS\n")
    
    try:
        test_mantener_info_previa()
        test_cambiar_email_mantiene_resto()
        
        print("\n\n" + "="*80)
        print("[OK] TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80)
        
    except Exception as e:
        print(f"\n[FAIL] ERROR EN LAS PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
