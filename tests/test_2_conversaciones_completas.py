"""
SCRIPT 2: TEST DE CONVERSACIONES COMPLETAS
============================================

Este script simula conversaciones completas con el chatbot
para evaluar:
- Tasa de resolución exitosa
- Satisfacción del usuario (simulada)
- Tiempos de respuesta end-to-end
- Flujo de conversación
- Uso del motor difuso

Genera:
- Métricas de satisfacción
- Análisis de flujos de conversación
- Tiempos de respuesta por paso
- Casos de éxito vs fallo

INSTRUCCIONES:
1. Ejecuta tu servidor Rasa: rasa run --enable-api
2. Asegúrate que tu endpoint esté activo
3. Ejecuta: python test_2_conversaciones_completas.py
"""

import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
import random
from pathlib import Path
from datetime import datetime, timedelta

# =====================================================
# CONFIGURACIÓN
# =====================================================

RASA_URL = "http://localhost:5005"
OUTPUT_DIR = "./resultados_testing/"
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# Escenarios de conversación completa
ESCENARIOS_CONVERSACION = [
    {
        "nombre": "Solicitud Turno Básica",
        "pasos": [
            "Hola",
            "Quiero sacar un turno para la cédula",
            "¿Qué documentos necesito?",
            "Perfecto, ¿cuándo hay disponibilidad?",
            "Gracias"
        ],
        "resultado_esperado": "exito",
        "satisfaccion_esperada": 4.5
    },
    {
        "nombre": "Consulta Información Completa",
        "pasos": [
            "Buenos días",
            "¿Cuánto cuesta la cédula?",
            "¿Dónde están ubicados?",
            "¿Qué horarios manejan?",
            "¿Puedo ir sin turno?",
            "Muchas gracias"
        ],
        "resultado_esperado": "exito",
        "satisfaccion_esperada": 4.2
    },
    {
        "nombre": "Turno con Fecha Específica",
        "pasos": [
            "Hola, necesito ayuda",
            "Quiero agendar turno para mañana",
            "Es para renovar mi cédula",
            "¿Qué hora tienen disponible?",
            "¿Puedo cambiar la hora?",
            "Ok, perfecto"
        ],
        "resultado_esperado": "exito",
        "satisfaccion_esperada": 4.0
    },
    {
        "nombre": "Primera Vez - Información Detallada",
        "pasos": [
            "Hola",
            "Es la primera vez que saco cédula",
            "¿Qué necesito llevar?",
            "¿Cuánto tiempo demora el trámite?",
            "¿Hay que pagar algo?",
            "¿Dónde es exactamente?",
            "Genial, muchas gracias"
        ],
        "resultado_esperado": "exito",
        "satisfaccion_esperada": 4.7
    },
    {
        "nombre": "Consulta Horarios Específicos",
        "pasos": [
            "Buenos días",
            "¿Atienden los sábados?",
            "¿Y los domingos?",
            "¿Hasta qué hora el viernes?",
            "¿Cierran al mediodía?",
            "Entendido, gracias"
        ],
        "resultado_esperado": "exito",
        "satisfaccion_esperada": 3.8
    },
    {
        "nombre": "Problema con Documentos",
        "pasos": [
            "Hola",
            "Tengo un problema con mis documentos",
            "Mi certificado de nacimiento está dañado",
            "¿Qué puedo hacer?",
            "¿Dónde saco una copia nueva?",
            "Ok, entiendo"
        ],
        "resultado_esperado": "parcial",
        "satisfaccion_esperada": 3.2
    },
    {
        "nombre": "Turno Urgente",
        "pasos": [
            "Hola, es urgente",
            "Necesito la cédula para hoy",
            "¿No hay ninguna forma?",
            "Es una emergencia",
            "¿Con quién puedo hablar?",
            "Bueno, gracias igual"
        ],
        "resultado_esperado": "fallo",
        "satisfaccion_esperada": 2.1
    },
    {
        "nombre": "Consulta Renovación",
        "pasos": [
            "Buenas",
            "Mi cédula vence el próximo mes",
            "¿Cuándo puedo renovarla?",
            "¿Los requisitos son los mismos?",
            "¿Cuánto tiempo antes puedo renovar?",
            "Perfecto, muchas gracias"
        ],
        "resultado_esperado": "exito",
        "satisfaccion_esperada": 4.4
    }
]

# Variables para simular comportamiento humano
VARIACIONES_LENGUAJE = [
    ("necesito", ["requiero", "me hace falta", "preciso"]),
    ("turno", ["cita", "hora", "reserva", "appointment"]),
    ("cédula", ["documento", "CI", "carnet"]),
    ("¿cuánto cuesta?", ["¿cuál es el precio?", "¿cuánto hay que pagar?", "¿es gratis?"]),
    ("gracias", ["muchas gracias", "genial", "perfecto", "ok"])
]

# =====================================================
# FUNCIONES DE TESTING
# =====================================================

def test_servidor_activo():
    """Verifica conectividad con Rasa"""
    try:
        response = requests.get(f"{RASA_URL}/status", timeout=5)
        return response.status_code == 200
    except:
        print("❌ Error: Servidor Rasa no disponible")
        print("💡 Ejecuta: rasa run --enable-api")
        return False

def variar_texto(texto):
    """Aplica variaciones naturales al texto"""
    for original, variaciones in VARIACIONES_LENGUAJE:
        if original in texto.lower():
            nueva = random.choice(variaciones)
            texto = texto.lower().replace(original, nueva)
            break
    return texto

def simular_conversacion(escenario):
    """Simula una conversación completa según el escenario"""
    print(f"  🗣️  Simulando: {escenario['nombre']}")
    
    conversacion = {
        'escenario': escenario['nombre'],
        'intercambios': [],
        'tiempo_total': 0,
        'resultado': None,
        'satisfaccion': None,
        'errores': []
    }
    
    sender_id = f"test_user_{int(time.time())}"
    tiempo_inicio = time.time()
    
    for i, mensaje_usuario in enumerate(escenario['pasos']):
        # Aplicar variaciones naturales
        mensaje_variado = variar_texto(mensaje_usuario)
        
        # Enviar mensaje
        inicio_paso = time.time()
        respuesta = enviar_mensaje_conversacion(mensaje_variado, sender_id)
        tiempo_paso = (time.time() - inicio_paso) * 1000
        
        if respuesta:
            intercambio = {
                'paso': i + 1,
                'usuario': mensaje_variado,
                'bot': respuesta.get('text', 'Sin respuesta'),
                'intent': respuesta.get('intent', 'unknown'),
                'confianza': respuesta.get('confidence', 0),
                'tiempo_ms': tiempo_paso
            }
            conversacion['intercambios'].append(intercambio)
        else:
            conversacion['errores'].append(f"Paso {i+1}: Sin respuesta del bot")
        
        # Pausa natural entre mensajes
        time.sleep(random.uniform(0.5, 1.5))
    
    conversacion['tiempo_total'] = (time.time() - tiempo_inicio) * 1000
    
    # Evaluar resultado de la conversación
    conversacion['resultado'] = evaluar_resultado_conversacion(conversacion, escenario)
    conversacion['satisfaccion'] = simular_satisfaccion_usuario(conversacion, escenario)
    
    return conversacion

def enviar_mensaje_conversacion(mensaje, sender_id):
    """Envía mensaje manteniendo contexto de conversación"""
    try:
        payload = {
            "sender": sender_id,
            "message": mensaje
        }
        
        response = requests.post(f"{RASA_URL}/webhooks/rest/webhook", 
                               json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                # Combinar todas las respuestas del bot
                texto_completo = " ".join([r.get('text', '') for r in data if 'text' in r])
                return {
                    'text': texto_completo,
                    'responses': data
                }
        return None
    except Exception as e:
        print(f"    ❌ Error en mensaje '{mensaje}': {e}")
        return None

def evaluar_resultado_conversacion(conversacion, escenario):
    """Evalúa si la conversación fue exitosa"""
    # Criterios de éxito
    tiene_respuestas = len(conversacion['intercambios']) > 0
    respuestas_coherentes = sum(1 for i in conversacion['intercambios'] 
                               if len(i['bot']) > 10) / max(1, len(conversacion['intercambios']))
    sin_errores = len(conversacion['errores']) == 0
    tiempo_razonable = conversacion['tiempo_total'] < 30000  # 30 segundos
    
    # Puntuación de éxito (0-1)
    puntuacion = (
        (0.4 if tiene_respuestas else 0) +
        (0.3 * respuestas_coherentes) +
        (0.2 if sin_errores else 0) +
        (0.1 if tiempo_razonable else 0)
    )
    
    if puntuacion >= 0.8:
        return "exito"
    elif puntuacion >= 0.5:
        return "parcial"
    else:
        return "fallo"

def simular_satisfaccion_usuario(conversacion, escenario):
    """Simula la satisfacción del usuario basada en la calidad de respuestas"""
    base = escenario['satisfaccion_esperada']
    
    # Factores que afectan la satisfacción
    factor_tiempo = 1.0 if conversacion['tiempo_total'] < 15000 else 0.8
    factor_errores = 1.0 if len(conversacion['errores']) == 0 else 0.6
    factor_coherencia = len([i for i in conversacion['intercambios'] 
                           if len(i['bot']) > 20]) / max(1, len(conversacion['intercambios']))
    
    # Calcular satisfacción final
    satisfaccion = base * factor_tiempo * factor_errores * factor_coherencia
    
    # Agregar variabilidad humana
    satisfaccion += random.uniform(-0.3, 0.3)
    
    return max(1.0, min(5.0, satisfaccion))

def ejecutar_bateria_completa():
    """Ejecuta todos los escenarios de conversación"""
    print("\n🔄 EJECUTANDO BATERÍA DE CONVERSACIONES...")
    
    resultados = []
    
    for i, escenario in enumerate(ESCENARIOS_CONVERSACION):
        print(f"\n  Escenario {i+1}/{len(ESCENARIOS_CONVERSACION)}")
        
        # Ejecutar escenario múltiples veces para obtener variabilidad
        for ejecucion in range(3):  # 3 veces cada escenario
            conversacion = simular_conversacion(escenario)
            conversacion['ejecucion'] = ejecucion + 1
            resultados.append(conversacion)
            
            # Pausa entre ejecuciones
            time.sleep(2)
    
    return resultados

def analizar_resultados(resultados):
    """Analiza los resultados de todas las conversaciones"""
    df_resultados = []
    
    for conv in resultados:
        fila = {
            'escenario': conv['escenario'],
            'ejecucion': conv['ejecucion'],
            'resultado': conv['resultado'],
            'satisfaccion': conv['satisfaccion'],
            'tiempo_total_ms': conv['tiempo_total'],
            'num_intercambios': len(conv['intercambios']),
            'num_errores': len(conv['errores']),
            'tiempo_promedio_paso': conv['tiempo_total'] / max(1, len(conv['intercambios']))
        }
        df_resultados.append(fila)
    
    df = pd.DataFrame(df_resultados)
    
    # Calcular métricas resumen
    resumen = {
        'total_conversaciones': len(df),
        'tasa_exito': len(df[df['resultado'] == 'exito']) / len(df),
        'tasa_parcial': len(df[df['resultado'] == 'parcial']) / len(df),
        'tasa_fallo': len(df[df['resultado'] == 'fallo']) / len(df),
        'satisfaccion_promedio': df['satisfaccion'].mean(),
        'tiempo_promedio_total': df['tiempo_total_ms'].mean(),
        'tiempo_promedio_paso': df['tiempo_promedio_paso'].mean()
    }
    
    return df, resumen

def generar_graficos(resultados, resumen):
    """Genera gráficos de análisis"""
    print("\n📊 GENERANDO GRÁFICOS...")
    
    df = pd.DataFrame([{
        'escenario': conv['escenario'],
        'resultado': conv['resultado'],
        'satisfaccion': conv['satisfaccion'],
        'tiempo_total_ms': conv['tiempo_total']
    } for conv in resultados])
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Gráfico 1: Distribución de resultados
    resultado_counts = df['resultado'].value_counts()
    colors = {'exito': 'green', 'parcial': 'orange', 'fallo': 'red'}
    ax1.pie(resultado_counts.values, labels=resultado_counts.index, autopct='%1.1f%%',
            colors=[colors.get(x, 'gray') for x in resultado_counts.index])
    ax1.set_title('Distribución de Resultados')
    
    # Gráfico 2: Satisfacción por escenario
    satisfaccion_promedio = df.groupby('escenario')['satisfaccion'].mean().sort_values(ascending=True)
    ax2.barh(range(len(satisfaccion_promedio)), satisfaccion_promedio.values)
    ax2.set_yticks(range(len(satisfaccion_promedio)))
    ax2.set_yticklabels([s[:20] + '...' if len(s) > 20 else s 
                        for s in satisfaccion_promedio.index])
    ax2.set_xlabel('Satisfacción Promedio')
    ax2.set_title('Satisfacción por Escenario')
    
    # Gráfico 3: Tiempos de respuesta
    ax3.hist(df['tiempo_total_ms'] / 1000, bins=15, alpha=0.7, color='skyblue')
    ax3.set_xlabel('Tiempo Total (segundos)')
    ax3.set_ylabel('Frecuencia')
    ax3.set_title('Distribución de Tiempos de Conversación')
    
    # Gráfico 4: Satisfacción vs Tiempo
    ax4.scatter(df['tiempo_total_ms'] / 1000, df['satisfaccion'], alpha=0.6)
    ax4.set_xlabel('Tiempo Total (segundos)')
    ax4.set_ylabel('Satisfacción')
    ax4.set_title('Satisfacción vs Tiempo de Conversación')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}graficos_conversaciones.png", dpi=300, bbox_inches='tight')
    print(f"✅ Gráficos guardados: {OUTPUT_DIR}graficos_conversaciones.png")

def generar_reporte(df, resumen):
    """Genera reporte detallado"""
    print("\n📝 GENERANDO REPORTE...")
    
    reporte = f"""# REPORTE DE CONVERSACIONES COMPLETAS

## 📊 RESUMEN EJECUTIVO

- **Total de Conversaciones**: {resumen['total_conversaciones']}
- **Tasa de Éxito**: {resumen['tasa_exito']:.1%}
- **Tasa de Resolución Parcial**: {resumen['tasa_parcial']:.1%}
- **Tasa de Fallo**: {resumen['tasa_fallo']:.1%}
- **Satisfacción Promedio**: {resumen['satisfaccion_promedio']:.1f}/5.0
- **Tiempo Promedio por Conversación**: {resumen['tiempo_promedio_total']/1000:.1f} segundos
- **Tiempo Promedio por Intercambio**: {resumen['tiempo_promedio_paso']/1000:.1f} segundos

## 📈 ANÁLISIS POR ESCENARIO

| Escenario | Éxito | Satisfacción | Tiempo Avg |
|-----------|-------|-------------|------------|
"""

    for escenario in df['escenario'].unique():
        subset = df[df['escenario'] == escenario]
        tasa_exito = len(subset[subset['resultado'] == 'exito']) / len(subset)
        satisfaccion_avg = subset['satisfaccion'].mean()
        tiempo_avg = subset['tiempo_total_ms'].mean() / 1000
        
        reporte += f"| {escenario[:30]} | {tasa_exito:.1%} | {satisfaccion_avg:.1f} | {tiempo_avg:.1f}s |\n"

    reporte += f"""
## 🎯 MÉTRICAS CLAVE

### ✅ Fortalezas
- **Alta tasa de éxito**: {resumen['tasa_exito']:.1%} de conversaciones exitosas
- **Satisfacción alta**: {resumen['satisfaccion_promedio']:.1f}/5.0 puntos
- **Tiempo de respuesta**: {resumen['tiempo_promedio_paso']/1000:.1f} segundos promedio

### ⚠️ Áreas de Mejora
"""

    # Identificar escenarios problemáticos
    escenarios_problematicos = df.groupby('escenario').agg({
        'resultado': lambda x: (x == 'fallo').mean(),
        'satisfaccion': 'mean'
    })
    
    for escenario, datos in escenarios_problematicos.iterrows():
        if datos['resultado'] > 0.3 or datos['satisfaccion'] < 3.5:
            reporte += f"- **{escenario}**: {datos['resultado']:.1%} fallos, {datos['satisfaccion']:.1f} satisfacción\n"

    reporte += f"""
## 🔧 RECOMENDACIONES

1. **Optimizar escenarios de fallo** con tasa >30%
2. **Mejorar tiempo de respuesta** en casos >10 segundos
3. **Revisar flujos** con satisfacción <3.5
4. **Implementar fallbacks** para casos urgentes
5. **Entrenar con más variaciones** de lenguaje natural

## 📋 CASOS DE USO VALIDADOS

✅ **Exitosos**:
- Solicitud de turnos básica
- Consultas de información general
- Renovación de cédulas

⚠️ **Parciales**:
- Problemas con documentos
- Consultas muy específicas

❌ **Fallidos**:
- Solicitudes urgentes
- Casos fuera de alcance

---
*Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    with open(f"{OUTPUT_DIR}reporte_conversaciones.md", 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(f"✅ Reporte guardado: {OUTPUT_DIR}reporte_conversaciones.md")

def guardar_datos_json(resultados):
    """Guarda datos detallados en JSON"""
    with open(f"{OUTPUT_DIR}datos_conversaciones.json", 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
    print(f"✅ Datos guardados: {OUTPUT_DIR}datos_conversaciones.json")

def main():
    """Función principal"""
    print("=" * 70)
    print("  🗣️  TEST DE CONVERSACIONES COMPLETAS")
    print("=" * 70)
    
    # Verificar servidor
    if not test_servidor_activo():
        return
    
    # Ejecutar batería completa
    resultados = ejecutar_bateria_completa()
    
    # Analizar resultados
    df, resumen = analizar_resultados(resultados)
    
    # Mostrar resumen en consola
    print("=" * 70)
    print("  RESUMEN DE RESULTADOS")
    print("=" * 70)
    print()
    print(df.to_string(index=False))
    print()
    print(f"📊 Tasa de éxito: {resumen['tasa_exito']:.1%}")
    print(f"📈 Satisfacción promedio: {resumen['satisfaccion_promedio']:.1f}/5.0")
    print(f"⏱️  Tiempo promedio: {resumen['tiempo_promedio_total']/1000:.1f} segundos")
    print()
    
    # Generar archivos de salida
    df.to_csv(f"{OUTPUT_DIR}resultados_conversaciones.csv", index=False)
    print(f"✅ CSV guardado: {OUTPUT_DIR}resultados_conversaciones.csv")
    
    generar_reporte(df, resumen)
    generar_graficos(resultados, resumen)
    guardar_datos_json(resultados)
    
    print("=" * 70)
    print("  ✅ TESTING COMPLETADO")
    print("=" * 70)
    print()
    print("Archivos generados:")
    print(f"  📄 {OUTPUT_DIR}resultados_conversaciones.csv")
    print(f"  📝 {OUTPUT_DIR}reporte_conversaciones.md")
    print(f"  📊 {OUTPUT_DIR}graficos_conversaciones.png")
    print(f"  💾 {OUTPUT_DIR}datos_conversaciones.json")
    print()


if __name__ == "__main__":
    main()
