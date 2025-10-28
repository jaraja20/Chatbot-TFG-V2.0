"""
SCRIPT 3: TEST DEL MOTOR DIFUSO Y TIEMPOS DE RESPUESTA
========================================================

Este script evalúa:
- Precisión del motor difuso en interpretar frases ambiguas
- Tiempos de respuesta de cada componente del sistema
- Comparación entre interpretación difusa vs humana
- Distribución de tiempos por operación

Genera:
- Métricas de precisión del motor difuso
- Tablas de tiempos de respuesta
- Gráficos de rendimiento
- Análisis de casos ambiguos

INSTRUCCIONES:
1. Asegúrate que tu motor_difuso.py esté disponible
2. Ejecuta: python test_3_motor_difuso_tiempos.py
"""

import time
import psycopg2
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, timedelta
import json

# Importar motor difuso (ajusta la ruta según tu proyecto)
try:
    import sys
    sys.path.append('.')  # Ajusta esta ruta
    from motor_difuso import MotorDifuso
    MOTOR_DISPONIBLE = True
except ImportError:
    print("⚠️  No se pudo importar motor_difuso.py")
    print("   Asegúrate que el archivo esté en la misma carpeta")
    MOTOR_DISPONIBLE = False

# =====================================================
# CONFIGURACIÓN
# =====================================================

RASA_URL = "http://localhost:5005"
OUTPUT_DIR = "./resultados_testing/"
Path(OUTPUT_DIR).mkdir(exist_ok=True)

# Base de datos (ajusta según tu configuración)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# Casos de prueba para el motor difuso
CASOS_MOTOR_DIFUSO = [
    {
        "texto": "quizás mañana pueda ir",
        "interpretacion_humana": {"urgencia": 0.3, "certeza": 0.4},
        "descripcion": "Expresión de baja urgencia y certeza"
    },
    {
        "texto": "necesito urgentemente la cédula",
        "interpretacion_humana": {"urgencia": 0.9, "certeza": 0.8},
        "descripcion": "Alta urgencia explícita"
    },
    {
        "texto": "tal vez podría necesitar un turno",
        "interpretacion_humana": {"urgencia": 0.2, "certeza": 0.3},
        "descripcion": "Muy baja certeza y urgencia"
    },
    {
        "texto": "definitivamente quiero agendar",
        "interpretacion_humana": {"urgencia": 0.7, "certeza": 0.9},
        "descripcion": "Alta certeza, urgencia media"
    },
    {
        "texto": "creo que me gustaría hacer el trámite",
        "interpretacion_humana": {"urgencia": 0.4, "certeza": 0.5},
        "descripcion": "Indecisión moderada"
    },
    {
        "texto": "es probable que vaya la próxima semana",
        "interpretacion_humana": {"urgencia": 0.3, "certeza": 0.6},
        "descripcion": "Certeza media, baja urgencia"
    },
    {
        "texto": "absolutamente tengo que ir hoy",
        "interpretacion_humana": {"urgencia": 1.0, "certeza": 1.0},
        "descripcion": "Máxima urgencia y certeza"
    },
    {
        "texto": "no estoy muy seguro si necesito turno",
        "interpretacion_humana": {"urgencia": 0.2, "certeza": 0.2},
        "descripcion": "Mínima certeza y urgencia"
    },
    {
        "texto": "seguramente iré en unos días",
        "interpretacion_humana": {"urgencia": 0.5, "certeza": 0.7},
        "descripcion": "Certeza alta, urgencia moderada"
    },
    {
        "texto": "posiblemente necesite ayuda con esto",
        "interpretacion_humana": {"urgencia": 0.4, "certeza": 0.4},
        "descripcion": "Incertidumbre general"
    }
]

# Operaciones a medir en tiempos
OPERACIONES_TIEMPO = [
    "consulta_bd_simple",
    "consulta_bd_compleja", 
    "motor_difuso",
    "rasa_nlu",
    "rasa_core",
    "generacion_respuesta"
]

# =====================================================
# FUNCIONES DE TESTING
# =====================================================

def test_conexion_bd():
    """Verifica conexión a la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        print("✅ Conexión BD activa")
        return True
    except Exception as e:
        print(f"❌ Error BD: {e}")
        return False

def test_motor_difuso():
    """Evalúa la precisión del motor difuso"""
    print("\n🧠 EVALUANDO MOTOR DIFUSO...")
    
    if not MOTOR_DISPONIBLE:
        print("⚠️  Motor difuso no disponible para testing")
        return []
    
    resultados = []
    motor = MotorDifuso()
    
    for caso in CASOS_MOTOR_DIFUSO:
        print(f"  Testing: {caso['descripcion']}")
        
        # Medir tiempo de procesamiento
        inicio = time.time()
        try:
            resultado_motor = motor.evaluar_texto(caso['texto'])
            tiempo_ms = (time.time() - inicio) * 1000
            
            # Comparar con interpretación humana
            diff_urgencia = abs(resultado_motor.get('urgencia', 0) - 
                               caso['interpretacion_humana']['urgencia'])
            diff_certeza = abs(resultado_motor.get('certeza', 0) - 
                              caso['interpretacion_humana']['certeza'])
            
            precision = 1 - (diff_urgencia + diff_certeza) / 2
            
            resultado = {
                'texto': caso['texto'],
                'descripcion': caso['descripcion'],
                'urgencia_humana': caso['interpretacion_humana']['urgencia'],
                'certeza_humana': caso['interpretacion_humana']['certeza'],
                'urgencia_motor': resultado_motor.get('urgencia', 0),
                'certeza_motor': resultado_motor.get('certeza', 0),
                'precision_urgencia': 1 - diff_urgencia,
                'precision_certeza': 1 - diff_certeza,
                'precision_general': precision,
                'tiempo_ms': tiempo_ms
            }
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            resultado = {
                'texto': caso['texto'],
                'descripcion': caso['descripcion'],
                'error': str(e),
                'precision_general': 0,
                'tiempo_ms': 0
            }
        
        resultados.append(resultado)
        time.sleep(0.1)  # Pausa pequeña
    
    return resultados

def medir_tiempos_componentes():
    """Mide tiempos de respuesta de diferentes componentes"""
    print("\n⏱️  MIDIENDO TIEMPOS DE COMPONENTES...")
    
    tiempos = {operacion: [] for operacion in OPERACIONES_TIEMPO}
    
    # Medir consultas BD simples
    print("  📊 Consultas BD simples...")
    for _ in range(10):
        tiempo = medir_tiempo_bd_simple()
        if tiempo > 0:
            tiempos['consulta_bd_simple'].append(tiempo)
    
    # Medir consultas BD complejas
    print("  📊 Consultas BD complejas...")
    for _ in range(5):
        tiempo = medir_tiempo_bd_compleja()
        if tiempo > 0:
            tiempos['consulta_bd_compleja'].append(tiempo)
    
    # Medir motor difuso
    if MOTOR_DISPONIBLE:
        print("  🧠 Motor difuso...")
        motor = MotorDifuso()
        for texto in ["quiero un turno", "tal vez necesite ayuda", "urgente por favor"]:
            inicio = time.time()
            try:
                motor.evaluar_texto(texto)
                tiempo = (time.time() - inicio) * 1000
                tiempos['motor_difuso'].append(tiempo)
            except:
                pass
    
    # Medir Rasa NLU
    print("  🔍 Rasa NLU...")
    for texto in ["hola", "quiero turno", "gracias", "adiós"]:
        tiempo = medir_tiempo_rasa_nlu(texto)
        if tiempo > 0:
            tiempos['rasa_nlu'].append(tiempo)
    
    # Medir conversación completa (NLU + Core + Response)
    print("  💬 Conversación completa...")
    for texto in ["hola", "necesito un turno", "cuánto cuesta"]:
        tiempo = medir_tiempo_conversacion_completa(texto)
        if tiempo > 0:
            tiempos['generacion_respuesta'].append(tiempo)
    
    return tiempos

def medir_tiempo_bd_simple():
    """Mide tiempo de consulta simple a BD"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        inicio = time.time()
        cursor.execute("SELECT COUNT(*) FROM conversation_logs")
        resultado = cursor.fetchone()
        tiempo = (time.time() - inicio) * 1000
        
        cursor.close()
        conn.close()
        return tiempo
    except:
        return 0

def medir_tiempo_bd_compleja():
    """Mide tiempo de consulta compleja a BD"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        inicio = time.time()
        cursor.execute("""
            SELECT intent, COUNT(*) as total,
                   AVG(CASE WHEN feedback_thumbs = 1 THEN 1.0 ELSE 0.0 END) as satisfaccion
            FROM conversation_logs 
            WHERE timestamp > NOW() - INTERVAL '30 days'
            GROUP BY intent
            ORDER BY total DESC
            LIMIT 10
        """)
        resultado = cursor.fetchall()
        tiempo = (time.time() - inicio) * 1000
        
        cursor.close()
        conn.close()
        return tiempo
    except:
        return 0

def medir_tiempo_rasa_nlu(texto):
    """Mide tiempo de procesamiento NLU"""
    try:
        payload = {"text": texto}
        inicio = time.time()
        response = requests.post(f"{RASA_URL}/model/parse", 
                               json=payload, timeout=10)
        tiempo = (time.time() - inicio) * 1000
        
        if response.status_code == 200:
            return tiempo
    except:
        pass
    return 0

def medir_tiempo_conversacion_completa(texto):
    """Mide tiempo de conversación completa"""
    try:
        payload = {
            "sender": f"test_timer_{int(time.time())}",
            "message": texto
        }
        
        inicio = time.time()
        response = requests.post(f"{RASA_URL}/webhooks/rest/webhook", 
                               json=payload, timeout=15)
        tiempo = (time.time() - inicio) * 1000
        
        if response.status_code == 200:
            return tiempo
    except:
        pass
    return 0

def analizar_datos_historicos():
    """Analiza datos históricos de rendimiento"""
    print("\n📈 ANALIZANDO DATOS HISTÓRICOS...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Consulta de métricas históricas
        query = """
            SELECT 
                DATE(timestamp) as fecha,
                intent,
                COUNT(*) as total_mensajes,
                AVG(CASE WHEN feedback_thumbs = 1 THEN 1.0 ELSE 0.0 END) * 100 as satisfaccion_pct,
                AVG(EXTRACT(EPOCH FROM (response_time - timestamp)) * 1000) as tiempo_promedio_ms
            FROM conversation_logs 
            WHERE timestamp > NOW() - INTERVAL '7 days'
              AND response_time IS NOT NULL
            GROUP BY DATE(timestamp), intent
            ORDER BY fecha DESC, total_mensajes DESC
        """
        
        df_historico = pd.read_sql(query, conn)
        conn.close()
        
        return df_historico
        
    except Exception as e:
        print(f"  ⚠️  Error accediendo datos históricos: {e}")
        return pd.DataFrame()

def generar_graficos_tiempos(tiempos_componentes, resultados_motor, df_historico):
    """Genera gráficos de análisis de tiempos"""
    print("\n📊 GENERANDO GRÁFICOS DE TIEMPOS...")
    
    fig = plt.figure(figsize=(16, 12))
    
    # Gráfico 1: Tiempos por componente (boxplot)
    ax1 = plt.subplot(2, 3, 1)
    datos_tiempos = [tiempos for tiempos in tiempos_componentes.values() if tiempos]
    labels_tiempos = [op for op, tiempos in tiempos_componentes.items() if tiempos]
    
    if datos_tiempos:
        ax1.boxplot(datos_tiempos, labels=labels_tiempos)
        ax1.set_title('Distribución de Tiempos por Componente')
        ax1.set_ylabel('Tiempo (ms)')
        plt.setp(ax1.get_xticklabels(), rotation=45)
    
    # Gráfico 2: Precisión del motor difuso
    ax2 = plt.subplot(2, 3, 2)
    if resultados_motor:
        precisiones = [r.get('precision_general', 0) for r in resultados_motor 
                      if 'precision_general' in r]
        if precisiones:
            ax2.hist(precisiones, bins=10, alpha=0.7, color='lightblue')
            ax2.set_title('Distribución de Precisión - Motor Difuso')
            ax2.set_xlabel('Precisión')
            ax2.set_ylabel('Frecuencia')
            ax2.axvline(np.mean(precisiones), color='red', linestyle='--', 
                       label=f'Media: {np.mean(precisiones):.2f}')
            ax2.legend()
    
    # Gráfico 3: Comparación Urgencia (Humano vs Motor)
    ax3 = plt.subplot(2, 3, 3)
    if resultados_motor:
        urgencia_humana = [r.get('urgencia_humana', 0) for r in resultados_motor 
                          if 'urgencia_humana' in r]
        urgencia_motor = [r.get('urgencia_motor', 0) for r in resultados_motor 
                         if 'urgencia_motor' in r]
        
        if urgencia_humana and urgencia_motor:
            ax3.scatter(urgencia_humana, urgencia_motor, alpha=0.7)
            ax3.plot([0, 1], [0, 1], 'r--', alpha=0.8)  # Línea perfecta
            ax3.set_xlabel('Urgencia Humana')
            ax3.set_ylabel('Urgencia Motor')
            ax3.set_title('Urgencia: Humano vs Motor Difuso')
    
    # Gráfico 4: Comparación Certeza (Humano vs Motor)
    ax4 = plt.subplot(2, 3, 4)
    if resultados_motor:
        certeza_humana = [r.get('certeza_humana', 0) for r in resultados_motor 
                         if 'certeza_humana' in r]
        certeza_motor = [r.get('certeza_motor', 0) for r in resultados_motor 
                        if 'certeza_motor' in r]
        
        if certeza_humana and certeza_motor:
            ax4.scatter(certeza_humana, certeza_motor, alpha=0.7, color='orange')
            ax4.plot([0, 1], [0, 1], 'r--', alpha=0.8)  # Línea perfecta
            ax4.set_xlabel('Certeza Humana')
            ax4.set_ylabel('Certeza Motor')
            ax4.set_title('Certeza: Humano vs Motor Difuso')
    
    # Gráfico 5: Tendencia histórica de satisfacción
    ax5 = plt.subplot(2, 3, 5)
    if not df_historico.empty and 'satisfaccion_pct' in df_historico.columns:
        satisfaccion_diaria = df_historico.groupby('fecha')['satisfaccion_pct'].mean()
        ax5.plot(satisfaccion_diaria.index, satisfaccion_diaria.values, marker='o')
        ax5.set_title('Satisfacción Histórica (7 días)')
        ax5.set_ylabel('Satisfacción (%)')
        plt.setp(ax5.get_xticklabels(), rotation=45)
    
    # Gráfico 6: Distribución de tiempos históricos
    ax6 = plt.subplot(2, 3, 6)
    if not df_historico.empty and 'tiempo_promedio_ms' in df_historico.columns:
        tiempos_hist = df_historico['tiempo_promedio_ms'].dropna()
        if len(tiempos_hist) > 0:
            ax6.hist(tiempos_hist, bins=15, alpha=0.7, color='lightgreen')
            ax6.set_title('Distribución Tiempos Históricos')
            ax6.set_xlabel('Tiempo (ms)')
            ax6.set_ylabel('Frecuencia')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}graficos_motor_tiempos.png", dpi=300, bbox_inches='tight')
    print(f"✅ Gráficos guardados: {OUTPUT_DIR}graficos_motor_tiempos.png")

def generar_reporte_completo(resultados_motor, tiempos_componentes, df_historico):
    """Genera reporte completo de análisis"""
    print("\n📝 GENERANDO REPORTE COMPLETO...")
    
    # Calcular estadísticas
    if resultados_motor:
        precision_promedio = np.mean([r.get('precision_general', 0) 
                                    for r in resultados_motor 
                                    if 'precision_general' in r])
        casos_exitosos = len([r for r in resultados_motor 
                            if r.get('precision_general', 0) > 0.7])
    else:
        precision_promedio = 0
        casos_exitosos = 0
    
    # Estadísticas de tiempos
    estadisticas_tiempos = {}
    for operacion, tiempos in tiempos_componentes.items():
        if tiempos:
            estadisticas_tiempos[operacion] = {
                'promedio': np.mean(tiempos),
                'mediana': np.median(tiempos),
                'std': np.std(tiempos),
                'min': np.min(tiempos),
                'max': np.max(tiempos)
            }
    
    reporte = f"""# REPORTE DE MOTOR DIFUSO Y TIEMPOS DE RESPUESTA

## 📊 RESUMEN EJECUTIVO

### 🧠 Motor Difuso
- **Casos Evaluados**: {len(resultados_motor)}
- **Precisión Promedio**: {precision_promedio:.1%}
- **Casos Exitosos (>70%)**: {casos_exitosos}/{len(resultados_motor)}
- **Tasa de Éxito**: {casos_exitosos/max(1,len(resultados_motor)):.1%}

### ⏱️ Tiempos de Respuesta
- **Componentes Medidos**: {len([k for k, v in tiempos_componentes.items() if v])}
- **Tiempo Total Promedio**: {np.mean(tiempos_componentes.get('generacion_respuesta', [0])):.1f} ms
- **Motor Difuso Promedio**: {np.mean(tiempos_componentes.get('motor_difuso', [0])):.1f} ms

## 📈 ANÁLISIS DETALLADO DEL MOTOR DIFUSO

| Caso | Urgencia H | Urgencia M | Certeza H | Certeza M | Precisión |
|------|-----------|-----------|----------|----------|-----------|
"""

    for resultado in resultados_motor[:10]:  # Primeros 10 casos
        if 'precision_general' in resultado:
            reporte += f"| {resultado['descripcion'][:20]}... | "
            reporte += f"{resultado.get('urgencia_humana', 0):.2f} | "
            reporte += f"{resultado.get('urgencia_motor', 0):.2f} | "
            reporte += f"{resultado.get('certeza_humana', 0):.2f} | "
            reporte += f"{resultado.get('certeza_motor', 0):.2f} | "
            reporte += f"{resultado.get('precision_general', 0):.1%} |\n"

    reporte += "\n## ⏱️ ESTADÍSTICAS DE TIEMPOS\n\n"
    reporte += "| Componente | Promedio (ms) | Mediana (ms) | Mín (ms) | Máx (ms) |\n"
    reporte += "|------------|---------------|--------------|----------|----------|\n"

    for operacion, stats in estadisticas_tiempos.items():
        reporte += f"| {operacion} | {stats['promedio']:.1f} | {stats['mediana']:.1f} | "
        reporte += f"{stats['min']:.1f} | {stats['max']:.1f} |\n"

    # Análisis histórico si está disponible
    if not df_historico.empty:
        satisfaccion_promedio = df_historico['satisfaccion_pct'].mean()
        tiempo_historico_promedio = df_historico['tiempo_promedio_ms'].mean()
        
        reporte += f"""
## 📊 ANÁLISIS HISTÓRICO (7 días)

- **Satisfacción Promedio**: {satisfaccion_promedio:.1f}%
- **Tiempo de Respuesta Histórico**: {tiempo_historico_promedio:.1f} ms
- **Total de Interacciones**: {df_historico['total_mensajes'].sum()}
- **Intents Más Usados**: {', '.join(df_historico.groupby('intent')['total_mensajes'].sum().nlargest(3).index.tolist())}
"""

    reporte += f"""
## 🎯 INTERPRETACIÓN DE RESULTADOS

### ✅ Fortalezas Identificadas
- **Precisión del motor difuso**: {"Excelente (>80%)" if precision_promedio > 0.8 else "Buena (60-80%)" if precision_promedio > 0.6 else "Necesita mejora (<60%)"}
- **Tiempos de respuesta**: {"Óptimos (<500ms)" if np.mean(tiempos_componentes.get('generacion_respuesta', [1000])) < 500 else "Aceptables"}
- **Consistencia**: {"Alta" if len(estadisticas_tiempos) > 0 and np.mean([s['std'] for s in estadisticas_tiempos.values()]) < 100 else "Media"}

### ⚠️ Áreas de Mejora
"""

    if precision_promedio < 0.7:
        reporte += "- **Motor difuso**: Precisión inferior al 70%, revisar lógica fuzzy\n"
    
    tiempo_promedio_respuesta = np.mean(tiempos_componentes.get('generacion_respuesta', [0]))
    if tiempo_promedio_respuesta > 1000:
        reporte += "- **Tiempos de respuesta**: >1 segundo, optimizar pipeline\n"
    
    if len([r for r in resultados_motor if r.get('precision_general', 1) < 0.5]) > len(resultados_motor) * 0.3:
        reporte += "- **Casos difíciles**: >30% de casos con baja precisión\n"

    reporte += f"""
## 🔧 RECOMENDACIONES TÉCNICAS

1. **Motor Difuso**:
   - {"Mantener configuración actual" if precision_promedio > 0.8 else "Ajustar funciones de membresía"}
   - {"" if precision_promedio > 0.7 else "Ampliar conjunto de reglas fuzzy"}
   - {"" if precision_promedio > 0.6 else "Reentrenar con más datos de validación"}

2. **Optimización de Tiempos**:
   - {"Sistema óptimo" if tiempo_promedio_respuesta < 500 else "Implementar caché para consultas frecuentes"}
   - {"" if tiempo_promedio_respuesta < 1000 else "Optimizar consultas a base de datos"}
   - {"" if tiempo_promedio_respuesta < 2000 else "Considerar procesamiento asíncrono"}

3. **Monitoreo Continuo**:
   - Implementar métricas en tiempo real
   - Establecer alertas por degradación de rendimiento
   - Realizar evaluaciones semanales automáticas

---
*Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    with open(f"{OUTPUT_DIR}reporte_motor_tiempos.md", 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(f"✅ Reporte guardado: {OUTPUT_DIR}reporte_motor_tiempos.md")

def main():
    """Función principal"""
    print("=" * 70)
    print("  🧠⏱️  TEST MOTOR DIFUSO Y TIEMPOS")
    print("=" * 70)
    
    # Verificar conexiones
    bd_activa = test_conexion_bd()
    
    # Test del motor difuso
    resultados_motor = test_motor_difuso()
    
    # Medir tiempos de componentes
    tiempos_componentes = medir_tiempos_componentes()
    
    # Analizar datos históricos
    df_historico = analizar_datos_historicos()
    
    # Mostrar resumen en consola
    print("\n" + "="*70)
    print("  📊 RESULTADOS")
    print("="*70)
    
    if resultados_motor:
        precision_promedio = np.mean([r.get('precision_general', 0) 
                                    for r in resultados_motor 
                                    if 'precision_general' in r])
        print(f"🧠 Precisión Motor Difuso: {precision_promedio:.1%}")
    
    for operacion, tiempos in tiempos_componentes.items():
        if tiempos:
            print(f"⏱️  {operacion}: {np.mean(tiempos):.1f} ms promedio")
    
    if not df_historico.empty:
        print(f"📈 Satisfacción Histórica: {df_historico['satisfaccion_pct'].mean():.1f}%")
        print(f"📊 Total Interacciones (7d): {df_historico['total_mensajes'].sum()}")
    
    # Generar archivos de salida
    print("\n" + "="*70)
    print("  📁 GENERANDO ARCHIVOS")
    print("="*70)
    
    # Guardar datos en CSV
    if resultados_motor:
        pd.DataFrame(resultados_motor).to_csv(f"{OUTPUT_DIR}resultados_motor_difuso.csv", index=False)
        print(f"✅ CSV motor difuso: {OUTPUT_DIR}resultados_motor_difuso.csv")
    
    # Guardar tiempos
    tiempos_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in tiempos_componentes.items()]))
    tiempos_df.to_csv(f"{OUTPUT_DIR}tiempos_componentes.csv", index=False)
    print(f"✅ CSV tiempos: {OUTPUT_DIR}tiempos_componentes.csv")
    
    # Guardar datos históricos
    if not df_historico.empty:
        df_historico.to_csv(f"{OUTPUT_DIR}datos_historicos.csv", index=False)
        print(f"✅ CSV históricos: {OUTPUT_DIR}datos_historicos.csv")
    
    # Generar gráficos y reporte
    generar_graficos_tiempos(tiempos_componentes, resultados_motor, df_historico)
    generar_reporte_completo(resultados_motor, tiempos_componentes, df_historico)
    
    print("\n" + "="*70)
    print("  ✅ TESTING COMPLETADO")
    print("="*70)
    print("Archivos generados:")
    print(f"  📄 {OUTPUT_DIR}resultados_motor_difuso.csv")
    print(f"  📄 {OUTPUT_DIR}tiempos_componentes.csv")
    print(f"  📄 {OUTPUT_DIR}datos_historicos.csv")
    print(f"  📝 {OUTPUT_DIR}reporte_motor_tiempos.md")
    print(f"  📊 {OUTPUT_DIR}graficos_motor_tiempos.png")
    print()

if __name__ == "__main__":
    main()
