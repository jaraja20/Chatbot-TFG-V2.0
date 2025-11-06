"""
Script de prueba para verificar el flujo de cambio de datos
"""
# -*- coding: utf-8 -*-
import sys
import os

# Agregar el directorio al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orquestador_inteligente import SessionContext, procesar_mensaje_inteligente

def test_flujo_cambio_completo():
    """
    Simula el flujo completo de cambio de un dato en la confirmación final
    """
    print("="*80)
    print("TEST: Flujo de cambio de datos en confirmación")
    print("="*80)
    
    # 1. Crear contexto con datos completos (simulando que ya pasó por todo el flujo)
    from orquestador_inteligente import SESSION_CONTEXTS
    session_id = "test_session_123"
    contexto = SessionContext(session_id)
    contexto.nombre = "Juan Pérez"
    contexto.cedula = "1234567"
    contexto.fecha = "2024-01-15"
    contexto.hora = "09:00"
    contexto.email = "juan@example.com"
    
    # Registrar el contexto en el diccionario global
    SESSION_CONTEXTS[session_id] = contexto
    
    print("\n[*] DATOS INICIALES:")
    print(f"Nombre: {contexto.nombre}")
    print(f"Cédula: {contexto.cedula}")
    print(f"Fecha: {contexto.fecha}")
    print(f"Hora: {contexto.hora}")
    print(f"Email: {contexto.email}")
    
    # 2. Usuario dice "Cambiar cédula"
    print("\n" + "="*80)
    print("[LOOP] Usuario: 'Cambiar cédula'")
    print("="*80)
    
    respuesta = procesar_mensaje_inteligente("Cambiar cédula", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    print(f"Intent detectado: {respuesta.get('intent')}")
    
    # Verificar que se reseteó la cédula
    print(f"\n[OK] Cédula reseteada: {contexto.cedula is None}")
    
    # 3. Usuario proporciona nueva cédula
    print("\n" + "="*80)
    print("[LOOP] Usuario: '9876543'")
    print("="*80)
    
    respuesta = procesar_mensaje_inteligente("9876543", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    print(f"Intent detectado: {respuesta.get('intent')}")
    
    # Verificar que se actualizó la cédula
    print(f"\n[OK] Nueva cédula: {contexto.cedula}")
    
    # 4. Verificar que muestra el resumen de confirmación
    respuesta_texto = respuesta.get('text', str(respuesta))
    if "Resumen" in respuesta_texto and "Confirmas estos datos" in respuesta_texto:
        print("\n[OK] ¡ÉXITO! El bot mostró el resumen de confirmación actualizado")
        print("\n[*] Datos finales:")
        print(f"Nombre: {contexto.nombre}")
        print(f"Cédula: {contexto.cedula}")
        print(f"Fecha: {contexto.fecha}")
        print(f"Hora: {contexto.hora}")
        print(f"Email: {contexto.email}")
    else:
        print("\n[FAIL] ERROR: El bot NO mostró el resumen de confirmación")
        print("Respuesta recibida:")
        print(respuesta_texto)
    
    print("\n" + "="*80)

def test_cambiar_generico():
    """
    Prueba el comando genérico "cambiar" sin especificar qué
    """
    print("\n\n" + "="*80)
    print("TEST: Comando genérico 'cambiar'")
    print("="*80)
    
    from orquestador_inteligente import SESSION_CONTEXTS
    session_id = "test_session_456"
    contexto = SessionContext(session_id)
    contexto.nombre = "María López"
    contexto.cedula = "5555555"
    contexto.fecha = "2024-01-20"
    contexto.hora = "14:00"
    contexto.email = "maria@example.com"
    SESSION_CONTEXTS[session_id] = contexto
    
    print("\n[LOOP] Usuario: 'cambiar'")
    
    respuesta = procesar_mensaje_inteligente("cambiar", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    print(f"Intent detectado: {respuesta.get('intent')}")
    
    respuesta_texto = respuesta.get('text', str(respuesta))
    if "qué dato quieres cambiar" in respuesta_texto.lower() or "cambiar nombre" in respuesta_texto.lower():
        print("\n[OK] ¡ÉXITO! El bot pidió aclaración de qué dato cambiar")
    else:
        print("\n[FAIL] ERROR: El bot no manejó correctamente el comando genérico")
    
    print("\n" + "="*80)

def test_cambiar_email():
    """
    Prueba el cambio de email
    """
    print("\n\n" + "="*80)
    print("TEST: Cambiar email")
    print("="*80)
    
    from orquestador_inteligente import SESSION_CONTEXTS
    session_id = "test_session_789"
    contexto = SessionContext(session_id)
    contexto.nombre = "Pedro Gómez"
    contexto.cedula = "7777777"
    contexto.fecha = "2024-01-25"
    contexto.hora = "10:30"
    contexto.email = "pedro_viejo@example.com"
    SESSION_CONTEXTS[session_id] = contexto
    
    print(f"\n[EMAIL] Email inicial: {contexto.email}")
    
    print("\n[LOOP] Usuario: 'Cambiar email'")
    respuesta = procesar_mensaje_inteligente("Cambiar email", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    
    print(f"\n[OK] Email reseteado: {contexto.email is None}")
    
    print("\n[LOOP] Usuario: 'pedro_nuevo@example.com'")
    respuesta = procesar_mensaje_inteligente("pedro_nuevo@example.com", session_id)
    print(f"\n[BOT] Bot: {respuesta.get('text', respuesta)}")
    
    print(f"\n[OK] Nuevo email: {contexto.email}")
    
    respuesta_texto = respuesta.get('text', str(respuesta))
    if "Resumen" in respuesta_texto:
        print("\n[OK] ¡ÉXITO! Mostró resumen después de cambiar email")
    else:
        print("\n[FAIL] ERROR: No mostró resumen")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print("\n[TEST] INICIANDO PRUEBAS DE CAMBIO DE DATOS\n")
    
    try:
        test_flujo_cambio_completo()
        test_cambiar_generico()
        test_cambiar_email()
        
        print("\n\n" + "="*80)
        print("[OK] TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80)
        
    except Exception as e:
        print(f"\n[FAIL] ERROR EN LAS PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
