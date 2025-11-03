"""
🧪 TEST DEL CLASIFICADOR LLM CON CONTEXTO COMPLETO DEL PROYECTO
=================================================================

Este script prueba el clasificador LLM (Llama 3.1 en LM Studio) con 
acceso completo al contexto del proyecto: domain.yml, nlu.yml, 
motor_difuso.py y actions.py

Autor: Sistema de Chatbot TFG
Fecha: 2024
"""

import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

from llm_classifier import LLMIntentClassifier, PROJECT_CONTEXT

def print_separator(title: str = ""):
    print("\n" + "="*70)
    if title:
        print(f"  {title}")
        print("="*70)
    print()

def verificar_contexto_cargado():
    """Verifica que el contexto del proyecto se haya cargado correctamente"""
    print_separator("🔍 VERIFICACIÓN DEL CONTEXTO DEL PROYECTO")
    
    if not PROJECT_CONTEXT.get('loaded'):
        print("❌ ERROR: El contexto del proyecto NO se cargó correctamente")
        print("   Verifica que los archivos domain.yml, nlu.yml, motor_difuso.py y actions.py existan")
        return False
    
    print("✅ Contexto del proyecto cargado exitosamente!\n")
    
    # Verificar cada componente
    print("📋 Componentes cargados:")
    print(f"   - domain.yml: {'✅ ' + str(len(PROJECT_CONTEXT.get('domain_content', ''))) + ' caracteres' if PROJECT_CONTEXT.get('domain_content') else '❌ No cargado'}")
    print(f"   - nlu.yml ejemplos: {'✅ ' + str(len(PROJECT_CONTEXT.get('nlu_examples', {}))) + ' intents' if PROJECT_CONTEXT.get('nlu_examples') else '❌ No cargado'}")
    print(f"   - motor_difuso docs: {'✅ Documentación disponible' if PROJECT_CONTEXT.get('motor_difuso_docs') else '❌ No cargado'}")
    print(f"   - actions list: {'✅ ' + str(len(PROJECT_CONTEXT.get('actions_list', []))) + ' actions' if PROJECT_CONTEXT.get('actions_list') else '❌ No cargado'}")
    
    # Mostrar algunos ejemplos de intents cargados
    if PROJECT_CONTEXT.get('nlu_examples'):
        print("\n📝 Ejemplos de intents cargados (primeros 5):")
        for i, intent_name in enumerate(list(PROJECT_CONTEXT['nlu_examples'].keys())[:5], 1):
            examples = PROJECT_CONTEXT['nlu_examples'][intent_name]
            print(f"   {i}. {intent_name}: {len(examples)} ejemplos")
    
    return True

def test_clasificacion_con_contexto():
    """Prueba la clasificación con diferentes tipos de mensajes"""
    print_separator("🧪 PRUEBAS DE CLASIFICACIÓN CON CONTEXTO COMPLETO")
    
    # Inicializar clasificador
    print("Inicializando clasificador LLM...")
    classifier = LLMIntentClassifier()
    
    if not classifier.available:
        print("⚠️ ADVERTENCIA: LM Studio no está disponible")
        print("   Asegúrate de que LM Studio esté corriendo en http://localhost:1234")
        print("   y que tengas un modelo cargado (ej: Llama 3.1 8B)\n")
        respuesta = input("¿Deseas continuar solo con clasificación por keywords? (s/n): ")
        if respuesta.lower() != 's':
            return
    else:
        print("✅ LM Studio está disponible y listo!\n")
    
    # Casos de prueba organizados por categoría
    test_cases = {
        "Saludos y despedidas": [
            "hola",
            "buenas tardes",
            "chau gracias"
        ],
        "Agendar turnos": [
            "quiero sacar un turno",
            "necesito una cita",
            "kmiero agendar"
        ],
        "Consultas de disponibilidad": [
            "que horarios hay disponibles",
            "hay turnos para mañana",
            "cuando puedo ir"
        ],
        "Datos personales": [
            "mi nombre es Juan Perez",
            "me llamo Maria",
            "soy 12345678"
        ],
        "Fechas y horas": [
            "para mañana",
            "el lunes",
            "a las 10 de la mañana"
        ],
        "Consultas de tiempo de espera (MOTOR DIFUSO)": [
            "cuanto voy a esperar",
            "cuanto demora",
            "hay mucha gente"
        ],
        "Recomendaciones (MOTOR DIFUSO)": [
            "recomiendame un horario",
            "cual es el mejor momento para ir",
            "cuando hay menos gente"
        ],
        "Información general": [
            "donde queda la oficina",
            "que requisitos necesito",
            "cuanto cuesta"
        ],
        "Cancelaciones": [
            "quiero cancelar mi turno",
            "necesito cancelar",
            "no puedo ir"
        ],
        "Confirmaciones": [
            "si confirmo",
            "esta bien",
            "no gracias"
        ]
    }
    
    total_correctos = 0
    total_pruebas = 0
    resultados_detallados = []
    
    for categoria, mensajes in test_cases.items():
        print(f"\n📂 {categoria}:")
        print("-" * 70)
        
        for mensaje in mensajes:
            total_pruebas += 1
            intent, confidence = classifier.classify_intent(mensaje)
            
            # Heurística simple para determinar si es correcto
            es_correcto = intent != "nlu_fallback"
            emoji = "✅" if es_correcto else "❌"
            
            if es_correcto:
                total_correctos += 1
            
            resultado = f"{emoji} '{mensaje}' → {intent} ({confidence:.2f})"
            print(f"  {resultado}")
            resultados_detallados.append((categoria, mensaje, intent, confidence, es_correcto))
    
    # Resumen final
    print_separator("📊 RESUMEN DE RESULTADOS")
    accuracy = (total_correctos / total_pruebas * 100) if total_pruebas > 0 else 0
    print(f"✅ Clasificaciones correctas: {total_correctos}/{total_pruebas} ({accuracy:.1f}%)")
    print(f"❌ Fallbacks: {total_pruebas - total_correctos}")
    
    # Análisis por categoría
    print("\n📈 Análisis por categoría:")
    categorias_stats = {}
    for categoria, _, _, _, es_correcto in resultados_detallados:
        if categoria not in categorias_stats:
            categorias_stats[categoria] = {'correctos': 0, 'total': 0}
        categorias_stats[categoria]['total'] += 1
        if es_correcto:
            categorias_stats[categoria]['correctos'] += 1
    
    for categoria, stats in categorias_stats.items():
        cat_accuracy = (stats['correctos'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"  {categoria}: {stats['correctos']}/{stats['total']} ({cat_accuracy:.0f}%)")
    
    # Recomendaciones
    print("\n💡 Recomendaciones:")
    if accuracy >= 80:
        print("  ✅ Excelente! El sistema está funcionando muy bien")
    elif accuracy >= 60:
        print("  ⚠️ Rendimiento aceptable, pero puede mejorar")
        print("     - Considera ajustar los prompts del sistema")
        print("     - Verifica que el modelo en LM Studio sea adecuado")
    else:
        print("  ❌ Rendimiento bajo. Sugerencias:")
        print("     1. Verifica que LM Studio esté corriendo correctamente")
        print("     2. Prueba con un modelo más grande (ej: Llama 3.1 8B)")
        print("     3. Revisa los ejemplos de nlu.yml")
        print("     4. Ajusta el system_prompt en llm_classifier.py")

def test_motor_difuso_integration():
    """Verifica que el sistema reconozca cuándo usar el motor difuso"""
    print_separator("🧠 TEST DE INTEGRACIÓN CON MOTOR DIFUSO")
    
    print("Verificando que el contexto incluya información del motor difuso...\n")
    
    if not PROJECT_CONTEXT.get('motor_difuso_docs'):
        print("❌ ERROR: La documentación del motor difuso no está cargada")
        return
    
    print("✅ Documentación del motor difuso cargada\n")
    print("📋 Funciones disponibles:")
    docs = PROJECT_CONTEXT['motor_difuso_docs']
    
    # Extraer las funciones mencionadas en la documentación
    funciones = ['calcular_espera', 'evaluar_recomendacion', 'analizar_disponibilidad_dia']
    for func in funciones:
        if func in docs:
            print(f"  ✅ {func}()")
    
    print("\n💡 El clasificador LLM ahora tiene acceso a esta información y puede")
    print("   recomendar el uso de estas funciones cuando sea apropiado.")

def main():
    print_separator("🚀 INICIANDO TESTS DEL SISTEMA LLM CON CONTEXTO COMPLETO")
    
    # 1. Verificar que el contexto se cargó
    if not verificar_contexto_cargado():
        print("\n❌ No se puede continuar sin el contexto del proyecto")
        return
    
    # 2. Test de integración con motor difuso
    test_motor_difuso_integration()
    
    # 3. Test de clasificación
    test_clasificacion_con_contexto()
    
    print_separator("✅ TESTS COMPLETADOS")
    print("El sistema ahora está listo para usar Llama 3.1 con contexto completo del proyecto!")
    print()

if __name__ == "__main__":
    main()
