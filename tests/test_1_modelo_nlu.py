"""
SCRIPT 1: EVALUACIÓN DEL MODELO NLU DE RASA
============================================

Este script evalúa el rendimiento del clasificador de intenciones
y extractor de entidades del modelo Rasa.

Genera:
- Métricas de precisión por intent
- F1-score global
- Matriz de confusión
- Análisis de extracción de entidades
- Gráficos de rendimiento

INSTRUCCIONES:
1. Ejecuta tu servidor Rasa: rasa run --enable-api
2. Ejecuta este script: python test_1_modelo_nlu.py
"""

import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from collections import defaultdict
import time
from pathlib import Path

# =====================================================
# CONFIGURACIÓN
# =====================================================

RASA_URL = "http://localhost:5005"
OUTPUT_DIR = "./resultados_testing/"
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# Casos de prueba por intent (agrega más según tus intents)
CASOS_PRUEBA = {
    "solicitar_turno": [
        "Quiero sacar un turno para la cédula",
        "Necesito agendar una cita",
        "¿Puedo reservar un turno?",
        "Quiero hacer una reserva",
        "Necesito programar una visita",
        "¿Cómo saco turno?",
        "Quiero agendar",
        "Necesito una cita para mañana"
    ],
    "consultar_requisitos": [
        "¿Qué documentos necesito?",
        "¿Cuáles son los requisitos?",
        "¿Qué tengo que llevar?",
        "¿Qué papeles necesito presentar?",
        "Requisitos para la cédula",
        "Documentación necesaria",
        "¿Qué debo traer?",
        "Papeles para el trámite"
    ],
    "consultar_horarios": [
        "¿Qué horarios tienen?",
        "¿A qué hora abren?",
        "¿Cuándo atienden?",
        "Horarios de atención",
        "¿Hasta qué hora trabajan?",
        "¿Qué días están abiertos?",
        "Horario de funcionamiento",
        "¿Cuándo puedo ir?"
    ],
    "consultar_costos": [
        "¿Cuánto cuesta?",
        "¿Cuál es el precio?",
        "Costo de la cédula",
        "¿Cuánto hay que pagar?",
        "Precio del trámite",
        "¿Cuánto vale?",
        "Tarifas",
        "¿Es gratis?"
    ],
    "consultar_ubicacion": [
        "¿Dónde están ubicados?",
        "¿Cuál es la dirección?",
        "¿Dónde queda?",
        "Ubicación de la oficina",
        "¿Cómo llego?",
        "Dirección del lugar",
        "¿En qué zona están?",
        "¿Dónde es?"
    ],
    "saludo": [
        "Hola",
        "Buenos días",
        "Buenas tardes",
        "Hi",
        "Saludos",
        "¿Qué tal?",
        "Hola, ¿cómo están?",
        "Buenos días, necesito ayuda"
    ],
    "despedida": [
        "Gracias",
        "Adiós",
        "Hasta luego",
        "Muchas gracias",
        "Chau",
        "Nos vemos",
        "Perfecto, gracias",
        "Ok, gracias"
    ]
}

# Casos con entidades para testing
CASOS_CON_ENTIDADES = [
    ("Quiero turno para el lunes", "lunes", "dia_semana"),
    ("Necesito cita para mañana por la mañana", "mañana", "tiempo_relativo"),
    ("¿Hay turno el 15 de diciembre?", "15 de diciembre", "fecha"),
    ("Quiero agendar para las 10:30", "10:30", "hora"),
    ("Necesito para mi hijo Juan", "Juan", "nombre_persona"),
    ("Turno para renovar cédula", "renovar", "tipo_tramite"),
    ("Primera vez sacando cédula", "primera vez", "tipo_tramite")
]

# =====================================================
# FUNCIONES DE TESTING
# =====================================================

def test_servidor_activo():
    """Verifica que el servidor Rasa esté funcionando"""
    try:
        response = requests.get(f"{RASA_URL}/status", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor Rasa activo")
            return True
        else:
            print(f"❌ Servidor responde con código {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("\n💡 Solución: Ejecuta 'rasa run --enable-api' en otra terminal")
        return False

def enviar_mensaje_nlu(texto):
    """Envía un mensaje al endpoint /parse de Rasa"""
    try:
        payload = {"text": texto}
        response = requests.post(f"{RASA_URL}/model/parse", json=payload, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error en respuesta: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error enviando mensaje '{texto}': {e}")
        return None

def evaluar_intenciones():
    """Evalúa la precisión de clasificación de intenciones"""
    print("\n🔍 EVALUANDO CLASIFICACIÓN DE INTENCIONES...")
    
    resultados = []
    predicciones = []
    verdaderos = []
    tiempos = []
    
    total_casos = sum(len(casos) for casos in CASOS_PRUEBA.values())
    procesados = 0
    
    for intent_real, casos in CASOS_PRUEBA.items():
        print(f"  Testing intent: {intent_real}")
        
        for caso in casos:
            inicio = time.time()
            respuesta = enviar_mensaje_nlu(caso)
            tiempo_resp = (time.time() - inicio) * 1000  # ms
            
            if respuesta:
                intent_predicho = respuesta.get('intent', {}).get('name', 'unknown')
                confianza = respuesta.get('intent', {}).get('confidence', 0)
                
                # Determinar si es correcto
                correcto = intent_predicho == intent_real
                
                resultado = {
                    'texto': caso,
                    'intent_real': intent_real,
                    'intent_predicho': intent_predicho,
                    'confianza': confianza,
                    'correcto': correcto,
                    'tiempo_ms': tiempo_resp
                }
                resultados.append(resultado)
                predicciones.append(intent_predicho)
                verdaderos.append(intent_real)
                tiempos.append(tiempo_resp)
                
            procesados += 1
            if procesados % 10 == 0:
                print(f"    Progreso: {procesados}/{total_casos}")
            
            # Pequeña pausa para no saturar el servidor
            time.sleep(0.1)
    
    return resultados, predicciones, verdaderos, tiempos

def evaluar_entidades():
    """Evalúa la extracción de entidades"""
    print("\n🏷️  EVALUANDO EXTRACCIÓN DE ENTIDADES...")
    
    resultados_entidades = []
    
    for texto, entidad_esperada, tipo_esperado in CASOS_CON_ENTIDADES:
        respuesta = enviar_mensaje_nlu(texto)
        
        if respuesta:
            entidades_extraidas = respuesta.get('entities', [])
            
            # Buscar si se extrajo la entidad esperada
            entidad_encontrada = False
            tipo_encontrado = None
            
            for ent in entidades_extraidas:
                if entidad_esperada.lower() in ent.get('value', '').lower():
                    entidad_encontrada = True
                    tipo_encontrado = ent.get('entity')
                    break
            
            resultado = {
                'texto': texto,
                'entidad_esperada': entidad_esperada,
                'tipo_esperado': tipo_esperado,
                'entidad_encontrada': entidad_encontrada,
                'tipo_encontrado': tipo_encontrado,
                'todas_entidades': entidades_extraidas
            }
            resultados_entidades.append(resultado)
    
    return resultados_entidades

def calcular_metricas(predicciones, verdaderos):
    """Calcula métricas de rendimiento"""
    print("\n📊 CALCULANDO MÉTRICAS...")
    
    # F1-score global
    f1_macro = f1_score(verdaderos, predicciones, average='macro')
    f1_micro = f1_score(verdaderos, predicciones, average='micro')
    
    # Reporte de clasificación
    reporte = classification_report(verdaderos, predicciones, output_dict=True)
    
    # Matriz de confusión
    intents_unicos = sorted(list(set(verdaderos + predicciones)))
    matriz_conf = confusion_matrix(verdaderos, predicciones, labels=intents_unicos)
    
    return {
        'f1_macro': f1_macro,
        'f1_micro': f1_micro,
        'reporte': reporte,
        'matriz_confusion': matriz_conf,
        'labels': intents_unicos
    }

def generar_graficos(resultados, metricas, tiempos):
    """Genera gráficos de resultados"""
    print("\n📈 GENERANDO GRÁFICOS...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Gráfico 1: Precisión por intent
    df_resultados = pd.DataFrame(resultados)
    precision_por_intent = df_resultados.groupby('intent_real')['correcto'].mean()
    
    ax1.bar(precision_por_intent.index, precision_por_intent.values)
    ax1.set_title('Precisión por Intent')
    ax1.set_ylabel('Precisión')
    ax1.tick_params(axis='x', rotation=45)
    
    # Gráfico 2: Distribución de confianza
    ax2.hist(df_resultados['confianza'], bins=20, alpha=0.7, color='skyblue')
    ax2.set_title('Distribución de Confianza')
    ax2.set_xlabel('Confianza')
    ax2.set_ylabel('Frecuencia')
    
    # Gráfico 3: Matriz de confusión
    sns.heatmap(metricas['matriz_confusion'], 
                xticklabels=metricas['labels'],
                yticklabels=metricas['labels'],
                annot=True, fmt='d', ax=ax3)
    ax3.set_title('Matriz de Confusión')
    
    # Gráfico 4: Tiempos de respuesta
    ax4.hist(tiempos, bins=20, alpha=0.7, color='lightgreen')
    ax4.set_title('Distribución de Tiempos de Respuesta')
    ax4.set_xlabel('Tiempo (ms)')
    ax4.set_ylabel('Frecuencia')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}graficos_nlu.png", dpi=300, bbox_inches='tight')
    print(f"✅ Gráficos guardados: {OUTPUT_DIR}graficos_nlu.png")

def generar_reporte(resultados, metricas, entidades, tiempos):
    """Genera un reporte en markdown"""
    print("\n📝 GENERANDO REPORTE...")
    
    df_resultados = pd.DataFrame(resultados)
    precision_global = df_resultados['correcto'].mean()
    tiempo_promedio = np.mean(tiempos)
    
    # Calcular métricas por intent
    precision_por_intent = df_resultados.groupby('intent_real').agg({
        'correcto': 'mean',
        'confianza': 'mean',
        'tiempo_ms': 'mean'
    }).round(3)
    
    reporte = f"""# REPORTE DE EVALUACIÓN NLU

## 📊 RESUMEN EJECUTIVO

- **Precisión Global**: {precision_global:.1%}
- **F1-Score Macro**: {metricas['f1_macro']:.3f}
- **F1-Score Micro**: {metricas['f1_micro']:.3f}
- **Tiempo Promedio**: {tiempo_promedio:.1f} ms
- **Total de Casos**: {len(resultados)}

## 📈 MÉTRICAS POR INTENT

| Intent | Precisión | Confianza Promedio | Tiempo (ms) |
|--------|-----------|-------------------|-------------|
"""

    for intent in precision_por_intent.index:
        precision = precision_por_intent.loc[intent, 'correcto']
        confianza = precision_por_intent.loc[intent, 'confianza']
        tiempo = precision_por_intent.loc[intent, 'tiempo_ms']
        reporte += f"| {intent} | {precision:.1%} | {confianza:.3f} | {tiempo:.1f} |\n"

    reporte += f"""
## 🏷️ EXTRACCIÓN DE ENTIDADES

- **Casos Evaluados**: {len(entidades)}
- **Entidades Extraídas Correctamente**: {sum(1 for e in entidades if e['entidad_encontrada'])}
- **Precisión de Entidades**: {sum(1 for e in entidades if e['entidad_encontrada'])/len(entidades):.1%}

## 🎯 CASOS PROBLEMÁTICOS

### Intents con Baja Precisión (<80%)
"""

    for intent in precision_por_intent.index:
        if precision_por_intent.loc[intent, 'correcto'] < 0.8:
            reporte += f"- **{intent}**: {precision_por_intent.loc[intent, 'correcto']:.1%}\n"

    reporte += f"""
### Casos de Baja Confianza (<0.7)

"""

    casos_baja_confianza = df_resultados[df_resultados['confianza'] < 0.7]
    for _, caso in casos_baja_confianza.head(5).iterrows():
        reporte += f"- \"{caso['texto']}\" → {caso['intent_predicho']} (conf: {caso['confianza']:.3f})\n"

    reporte += f"""
## 🔧 RECOMENDACIONES

1. **Mejorar datos de entrenamiento** para intents con precisión <80%
2. **Revisar casos de baja confianza** y agregar ejemplos similares
3. **Optimizar extracción de entidades** para tipos específicos
4. **Considerar reentrenamiento** si la precisión global <85%

---
*Generado automáticamente el {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""

    with open(f"{OUTPUT_DIR}reporte_nlu.md", 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(f"✅ Reporte guardado: {OUTPUT_DIR}reporte_nlu.md")

def main():
    """Función principal"""
    print("=" * 60)
    print("  🧠 TEST DEL MODELO NLU - RASA")
    print("=" * 60)
    
    # Verificar servidor
    if not test_servidor_activo():
        return
    
    # Evaluar intenciones
    resultados, predicciones, verdaderos, tiempos = evaluar_intenciones()
    
    # Evaluar entidades
    entidades = evaluar_entidades()
    
    # Calcular métricas
    metricas = calcular_metricas(predicciones, verdaderos)
    
    # Mostrar resumen en consola
    print("\n" + "="*60)
    print("  📊 RESULTADOS")
    print("="*60)
    print(f"✅ Precisión Global: {pd.DataFrame(resultados)['correcto'].mean():.1%}")
    print(f"✅ F1-Score Macro: {metricas['f1_macro']:.3f}")
    print(f"✅ Tiempo Promedio: {np.mean(tiempos):.1f} ms")
    print(f"✅ Entidades Correctas: {sum(1 for e in entidades if e['entidad_encontrada'])}/{len(entidades)}")
    
    # Generar archivos de salida
    pd.DataFrame(resultados).to_csv(f"{OUTPUT_DIR}resultados_nlu.csv", index=False)
    generar_graficos(resultados, metricas, tiempos)
    generar_reporte(resultados, metricas, entidades, tiempos)
    
    print("\n" + "="*60)
    print("  ✅ TESTING COMPLETADO")
    print("="*60)
    print("Archivos generados:")
    print(f"  📄 {OUTPUT_DIR}resultados_nlu.csv")
    print(f"  📝 {OUTPUT_DIR}reporte_nlu.md")
    print(f"  📊 {OUTPUT_DIR}graficos_nlu.png")
    print()

if __name__ == "__main__":
    main()
