"""
Test para verificar que las consultas informativas no interrumpen el formulario
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente, SESSION_CONTEXTS

def test_flujo_formulario():
    """Test: Consultas informativas durante el formulario"""
    print("\n" + "="*80)
    print("TEST: Flujo del formulario con consultas informativas")
    print("="*80)
    
    session_id = "test_flujo_001"
    
    # Limpiar contexto previo
    if session_id in SESSION_CONTEXTS:
        del SESSION_CONTEXTS[session_id]
    
    conversacion = [
        ("Quiero agendar un turno", "Debe pedir nombre"),
        ("Qué requisitos necesito", "Debe mostrar requisitos Y pedir nombre"),
        ("jhonatan", "Debe RECHAZAR (solo 1 palabra)"),
        ("jhonatan villalba", "Debe ACEPTAR nombre completo"),
        ("Cuánto voy a esperar", "Debe mostrar tiempo de espera Y pedir cédula"),
        ("Cuánto cuesta", "Debe mostrar costos Y pedir cédula"),
        ("12345678", "Debe aceptar cédula y pedir fecha"),
    ]
    
    print("\n📝 Iniciando conversación de prueba:\n")
    
    for i, (mensaje, esperado) in enumerate(conversacion, 1):
        print(f"\n{i}. 👤 Usuario: {mensaje}")
        print(f"   ⚠️  Esperado: {esperado}")
        
        resultado = procesar_mensaje_inteligente(mensaje, session_id)
        respuesta = resultado.get('text', resultado.get('respuesta', 'ERROR'))
        intent = resultado.get('intent', 'unknown')
        
        print(f"   🤖 Intent: {intent}")
        print(f"   💬 Respuesta: {respuesta[:200]}...")
        
        # Validaciones específicas
        if i == 2:  # "Qué requisitos necesito"
            if "📋" in respuesta and "nombre completo" in respuesta.lower():
                print("   ✅ Correcto: Muestra requisitos Y pide nombre")
            else:
                print("   ❌ Error: No mantiene el flujo del formulario")
        
        elif i == 3:  # "jhonatan" (1 palabra)
            if "apellido" in respuesta.lower() or "nombre completo" in respuesta.lower():
                print("   ✅ Correcto: Rechaza nombre de 1 sola palabra")
            else:
                print("   ❌ Error: Aceptó nombre de 1 palabra")
        
        elif i == 4:  # "jhonatan villalba"
            if "villalba" in respuesta.lower() and "cédula" in respuesta.lower():
                print("   ✅ Correcto: Acepta nombre completo y pide cédula")
            else:
                print("   ❌ Error: No aceptó el nombre correctamente")
        
        elif i == 5:  # "Cuánto voy a esperar"
            if ("tiempo" in respuesta.lower() or "espera" in respuesta.lower()) and "cédula" in respuesta.lower():
                print("   ✅ Correcto: Muestra tiempo Y pide cédula")
            else:
                print(f"   ❌ Error: Intent detectado como '{intent}' en lugar de 'consulta_tiempo_espera'")
                if "costo" in respuesta.lower() or "precio" in respuesta.lower():
                    print("   ⚠️  Está detectando como 'consultar_costo' en lugar de 'consulta_tiempo_espera'")
        
        elif i == 6:  # "Cuánto cuesta"
            if ("costo" in respuesta.lower() or "precio" in respuesta.lower()) and "cédula" in respuesta.lower():
                print("   ✅ Correcto: Muestra costos Y pide cédula")
            else:
                print("   ❌ Error: No mantiene el flujo del formulario")
        
        elif i == 7:  # "12345678"
            if "fecha" in respuesta.lower() or "día" in respuesta.lower():
                print("   ✅ Correcto: Acepta cédula y pide fecha")
            else:
                print("   ❌ Error: No avanzó correctamente")
    
    print("\n" + "="*80)
    print("Test completado")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_flujo_formulario()
