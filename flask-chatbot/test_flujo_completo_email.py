"""
Test para verificar el flujo completo incluyendo email, Google Calendar y encuesta
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente, SESSION_CONTEXTS

def test_flujo_completo():
    """Test: Flujo completo con email y confirmación"""
    print("\n" + "="*80)
    print("TEST: Flujo completo con email, Google Calendar y encuesta")
    print("="*80)
    
    session_id = "test_email_001"
    
    # Limpiar contexto previo
    if session_id in SESSION_CONTEXTS:
        del SESSION_CONTEXTS[session_id]
    
    conversacion = [
        ("Quiero agendar un turno", "Debe pedir nombre"),
        ("Juan Pérez", "Debe pedir cédula"),
        ("12345678", "Debe pedir fecha"),
        ("mañana", "Debe mostrar disponibilidad"),
        ("las 9", "Debe pedir email"),
        ("juan@example.com", "Debe mostrar resumen y pedir confirmación"),
        ("sí", "Debe confirmar con links de Google Calendar y encuesta"),
    ]
    
    print("\nIniciando conversacion de prueba:\n")
    
    for i, (mensaje, esperado) in enumerate(conversacion, 1):
        print(f"\n{i}. Usuario: {mensaje}")
        print(f"   Esperado: {esperado}")
        
        resultado = procesar_mensaje_inteligente(mensaje, session_id)
        respuesta = resultado.get('text', resultado.get('respuesta', 'ERROR'))
        intent = resultado.get('intent', 'unknown')
        
        print(f"   Intent: {intent}")
        print(f"   Respuesta: {respuesta[:250]}...")
        
        # Validaciones específicas
        if i == 5:  # "las 9" - debe pedir email
            if "email" in respuesta.lower() or "correo" in respuesta.lower():
                print("   [OK] Correcto: Pide email")
            else:
                print("   [ERROR] No pide email")
        
        elif i == 6:  # "juan@example.com" - debe mostrar resumen
            if "resumen" in respuesta.lower() and "confirmas" in respuesta.lower():
                print("   [OK] Correcto: Muestra resumen y pide confirmacion")
            else:
                print("   [ERROR] No muestra resumen correctamente")
        
        elif i == 7:  # "sí" - debe confirmar con links
            # Imprimir respuesta completa para debugging
            print(f"\n   --- RESPUESTA COMPLETA ---")
            print(f"{respuesta}")
            print(f"   --- FIN RESPUESTA ---\n")
            
            if "calendar.google.com" in respuesta and "forms.d/e/" in respuesta:
                print("   [OK] Correcto: Incluye link de Google Calendar y encuesta")
            else:
                print("   [ERROR] Faltan links")
                if "calendar.google.com" not in respuesta:
                    print("   [WARN] Falta link de Google Calendar")
                if "forms.d/e/" not in respuesta:
                    print("   [WARN] Falta link de encuesta")
    
    print("\n" + "="*80)
    print("Test completado")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_flujo_completo()
