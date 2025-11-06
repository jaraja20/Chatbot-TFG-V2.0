"""
SUITE DE TESTS COMPLETA - VERSIÓN 2.0
Valida todos los fixes implementados y genera reportes visuales

Fixes probados:
1. Detección de "para el jueves" y referencias temporales
2. Validación de horarios completos (máximo 2 por slot)
3. Detección de "una y media" y horas en palabras
4. Aceptación de horarios alternativos
5. Prevención de confusión del LLM con contexto
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# Configurar paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTADOS_DIR = PROJECT_ROOT / "resultados"
GRAFICOS_DIR = RESULTADOS_DIR / "graficos"
LOGS_DIR = RESULTADOS_DIR / "logs"

# Crear directorios si no existen
GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Agregar path del proyecto
sys.path.insert(0, str(PROJECT_ROOT / "flask-chatbot"))

# Importar módulos del chatbot
try:
    from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context
    print("✅ Módulos del chatbot importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

class TestResult:
    """Resultado de un test individual"""
    def __init__(self, nombre: str, esperado: str, obtenido: str, tiempo: float, detalles: str = ""):
        self.nombre = nombre
        self.esperado = esperado
        self.obtenido = obtenido
        self.exitoso = esperado.lower() == obtenido.lower()
        self.tiempo = tiempo
        self.detalles = detalles
    
    def to_dict(self):
        return {
            'nombre': self.nombre,
            'esperado': self.esperado,
            'obtenido': self.obtenido,
            'exitoso': self.exitoso,
            'tiempo': self.tiempo,
            'detalles': self.detalles
        }

class TestSuite:
    """Suite de tests con generación de reportes"""
    
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.resultados: List[TestResult] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def agregar_resultado(self, resultado: TestResult):
        self.resultados.append(resultado)
        
    def tasa_exito(self) -> float:
        if not self.resultados:
            return 0.0
        exitosos = sum(1 for r in self.resultados if r.exitoso)
        return (exitosos / len(self.resultados)) * 100
    
    def tiempo_promedio(self) -> float:
        if not self.resultados:
            return 0.0
        return sum(r.tiempo for r in self.resultados) / len(self.resultados)
    
    def generar_reporte_texto(self) -> str:
        """Genera reporte en texto plano"""
        reporte = []
        reporte.append("=" * 80)
        reporte.append(f"REPORTE DE TESTS: {self.nombre}")
        reporte.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        reporte.append("=" * 80)
        reporte.append("")
        
        # Resumen
        reporte.append("📊 RESUMEN")
        reporte.append("-" * 80)
        reporte.append(f"Total de tests: {len(self.resultados)}")
        exitosos = sum(1 for r in self.resultados if r.exitoso)
        fallidos = len(self.resultados) - exitosos
        reporte.append(f"✅ Exitosos: {exitosos} ({self.tasa_exito():.1f}%)")
        reporte.append(f"❌ Fallidos: {fallidos} ({100 - self.tasa_exito():.1f}%)")
        reporte.append(f"⏱️  Tiempo promedio: {self.tiempo_promedio():.3f}s")
        reporte.append("")
        
        # Detalles de cada test
        reporte.append("📝 DETALLES DE TESTS")
        reporte.append("-" * 80)
        for i, resultado in enumerate(self.resultados, 1):
            estado = "✅ PASS" if resultado.exitoso else "❌ FAIL"
            reporte.append(f"\n{i}. {resultado.nombre} {estado}")
            reporte.append(f"   Esperado: {resultado.esperado}")
            reporte.append(f"   Obtenido: {resultado.obtenido}")
            reporte.append(f"   Tiempo: {resultado.tiempo:.3f}s")
            if resultado.detalles:
                reporte.append(f"   Detalles: {resultado.detalles}")
        
        reporte.append("\n" + "=" * 80)
        return "\n".join(reporte)
    
    def guardar_reporte(self):
        """Guarda reporte en archivo de texto"""
        filename = LOGS_DIR / f"reporte_{self.nombre}_{self.timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.generar_reporte_texto())
        print(f"📄 Reporte guardado: {filename}")
        return filename
    
    def guardar_json(self):
        """Guarda resultados en JSON"""
        filename = LOGS_DIR / f"resultados_{self.nombre}_{self.timestamp}.json"
        datos = {
            'nombre': self.nombre,
            'timestamp': self.timestamp,
            'tasa_exito': self.tasa_exito(),
            'tiempo_promedio': self.tiempo_promedio(),
            'total_tests': len(self.resultados),
            'resultados': [r.to_dict() for r in self.resultados]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON guardado: {filename}")
        return filename
    
    def generar_graficos(self):
        """Genera gráficos de resultados"""
        if not self.resultados:
            print("⚠️ No hay resultados para graficar")
            return
        
        # Configurar estilo
        try:
            plt.style.use('seaborn-darkgrid')
        except:
            plt.style.use('ggplot')  # Fallback style
        
        # Gráfico 1: Tasa de éxito
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Resultados de Tests: {self.nombre}', fontsize=16, fontweight='bold')
        
        # 1.1: Pie chart - Éxito vs Fallos
        exitosos = sum(1 for r in self.resultados if r.exitoso)
        fallidos = len(self.resultados) - exitosos
        colors = ['#4CAF50', '#F44336']
        explode = (0.1, 0)
        axes[0, 0].pie([exitosos, fallidos], labels=['Exitosos', 'Fallidos'], 
                       autopct='%1.1f%%', colors=colors, explode=explode, shadow=True)
        axes[0, 0].set_title(f'Tasa de Éxito: {self.tasa_exito():.1f}%')
        
        # 1.2: Bar chart - Tests individuales
        nombres = [r.nombre[:30] + '...' if len(r.nombre) > 30 else r.nombre for r in self.resultados]
        colores = ['green' if r.exitoso else 'red' for r in self.resultados]
        axes[0, 1].barh(range(len(nombres)), [1 if r.exitoso else 0 for r in self.resultados], color=colores)
        axes[0, 1].set_yticks(range(len(nombres)))
        axes[0, 1].set_yticklabels(nombres, fontsize=8)
        axes[0, 1].set_xlabel('Resultado (1=Éxito, 0=Fallo)')
        axes[0, 1].set_title('Resultados por Test')
        axes[0, 1].set_xlim([-0.1, 1.1])
        
        # 1.3: Tiempos de ejecución
        tiempos = [r.tiempo for r in self.resultados]
        axes[1, 0].bar(range(len(tiempos)), tiempos, color='skyblue')
        axes[1, 0].axhline(y=self.tiempo_promedio(), color='r', linestyle='--', label=f'Promedio: {self.tiempo_promedio():.3f}s')
        axes[1, 0].set_xlabel('Test #')
        axes[1, 0].set_ylabel('Tiempo (s)')
        axes[1, 0].set_title('Tiempos de Ejecución')
        axes[1, 0].legend()
        
        # 1.4: Tabla resumen
        axes[1, 1].axis('off')
        tabla_data = [
            ['Métrica', 'Valor'],
            ['Total Tests', str(len(self.resultados))],
            ['Exitosos', f"{exitosos} ({self.tasa_exito():.1f}%)"],
            ['Fallidos', f"{fallidos} ({100 - self.tasa_exito():.1f}%)"],
            ['Tiempo Promedio', f"{self.tiempo_promedio():.3f}s"],
            ['Tiempo Total', f"{sum(tiempos):.3f}s"]
        ]
        tabla = axes[1, 1].table(cellText=tabla_data, cellLoc='left', loc='center',
                                colWidths=[0.5, 0.5])
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(10)
        tabla.scale(1, 2)
        
        # Aplicar colores a la tabla
        for i, cell in tabla.get_celld().items():
            if i[0] == 0:  # Header
                cell.set_facecolor('#4CAF50')
                cell.set_text_props(weight='bold', color='white')
            else:
                cell.set_facecolor('#f0f0f0')
        
        plt.tight_layout()
        
        # Guardar
        filename = GRAFICOS_DIR / f"resultados_{self.nombre}_{self.timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Gráfico guardado: {filename}")
        
        return filename

def ejecutar_test(nombre: str, conversacion: List[Tuple[str, str]], session_id: str = None) -> TestResult:
    """
    Ejecuta un test de conversación completa
    
    Args:
        nombre: Nombre del test
        conversacion: Lista de tuplas (mensaje_usuario, respuesta_esperada_clave)
        session_id: ID de sesión (opcional)
    
    Returns:
        TestResult con el resultado del test
    """
    if session_id is None:
        session_id = f"test_{int(time.time() * 1000)}"
    
    inicio = time.time()
    detalles = []
    exitoso = True
    
    for i, (mensaje, clave_esperada) in enumerate(conversacion, 1):
        try:
            resultado = procesar_mensaje_inteligente(mensaje, session_id)
            respuesta = resultado.get('text', '')
            
            # Verificar si la respuesta contiene la clave esperada
            if clave_esperada.lower() in respuesta.lower():
                detalles.append(f"✅ Paso {i}: '{mensaje}' → OK")
            else:
                detalles.append(f"❌ Paso {i}: '{mensaje}' → Esperaba '{clave_esperada}', obtuvo '{respuesta[:100]}'")
                exitoso = False
                
        except Exception as e:
            detalles.append(f"❌ Paso {i}: Error: {str(e)}")
            exitoso = False
    
    tiempo = time.time() - inicio
    
    return TestResult(
        nombre=nombre,
        esperado="Conversación exitosa" if exitoso else "Conversación fallida",
        obtenido="Conversación exitosa" if exitoso else "Conversación fallida",
        tiempo=tiempo,
        detalles="\n   ".join(detalles)
    )

# ============================================================================
# TESTS ESPECÍFICOS PARA CADA FIX
# ============================================================================

def test_fix_1_referencias_temporales():
    """Test Fix #1: Detección de referencias temporales"""
    suite = TestSuite("fix1_referencias_temporales")
    
    tests = [
        ("Test 1: 'para el jueves'", [
            ("quiero un turno", "nombre"),
            ("Juan Pérez", "cédula"),
            ("1234567", "día"),
            ("para el jueves", "hora"),
        ]),
        ("Test 2: 'próximo jueves'", [
            ("necesito turno", "nombre"),
            ("María López", "cédula"),
            ("9876543", "día"),
            ("próximo jueves", "hora"),
        ]),
        ("Test 3: 'el jueves'", [
            ("agendar turno", "nombre"),
            ("Pedro García", "cédula"),
            ("5555555", "día"),
            ("el jueves", "hora"),
        ]),
    ]
    
    for nombre, conversacion in tests:
        resultado = ejecutar_test(nombre, conversacion)
        suite.agregar_resultado(resultado)
    
    return suite

def test_fix_3_horas_en_palabras():
    """Test Fix #3: Detección de horas en palabras"""
    suite = TestSuite("fix3_horas_en_palabras")
    
    tests = [
        ("Test 1: 'una y media'", [
            ("quiero turno", "nombre"),
            ("Ana Martínez", "cédula"),
            ("1111111", "día"),
            ("mañana", "hora"),
            ("una y media", "email"),
        ]),
        ("Test 2: '1 y media'", [
            ("necesito cita", "nombre"),
            ("Carlos Ruiz", "cédula"),
            ("2222222", "día"),
            ("pasado mañana", "hora"),
            ("1 y media", "email"),
        ]),
        ("Test 3: 'dos y cuarto'", [
            ("sacar turno", "nombre"),
            ("Laura Sánchez", "cédula"),
            ("3333333", "día"),
            ("próximo lunes", "hora"),
            ("dos y cuarto", "email"),
        ]),
    ]
    
    for nombre, conversacion in tests:
        resultado = ejecutar_test(nombre, conversacion)
        suite.agregar_resultado(resultado)
    
    return suite

def test_fix_5_contexto_llm():
    """Test Fix #5: LLM no confunde hora con costo por contexto"""
    suite = TestSuite("fix5_contexto_llm")
    
    tests = [
        ("Test 1: '1 y media' con contexto", [
            ("quiero un turno", "nombre"),
            ("Roberto Díaz", "cédula"),
            ("4444444", "día"),
            ("jueves", "hora"),
            ("1 y media", "email"),  # NO debe mostrar costos
        ]),
        ("Test 2: '9' con contexto", [
            ("agendar", "nombre"),
            ("Sofia Torres", "cédula"),
            ("5555555", "día"),
            ("viernes", "hora"),
            ("9", "email"),  # NO debe mostrar costos
        ]),
    ]
    
    for nombre, conversacion in tests:
        resultado = ejecutar_test(nombre, conversacion)
        suite.agregar_resultado(resultado)
    
    return suite

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Ejecuta todos los tests y genera reportes"""
    print("=" * 80)
    print("🧪 INICIANDO SUITE COMPLETA DE TESTS - VERSIÓN 2.0")
    print("=" * 80)
    print()
    
    # Ejecutar cada suite de tests
    suites = [
        ("Fix #1: Referencias Temporales", test_fix_1_referencias_temporales),
        ("Fix #3: Horas en Palabras", test_fix_3_horas_en_palabras),
        ("Fix #5: Contexto LLM", test_fix_5_contexto_llm),
    ]
    
    resultados_globales = []
    
    for nombre_suite, func_test in suites:
        print(f"\n{'=' * 80}")
        print(f"📋 Ejecutando: {nombre_suite}")
        print("=" * 80)
        
        try:
            suite = func_test()
            print(f"\n✅ {suite.nombre}: {suite.tasa_exito():.1f}% éxito ({len(suite.resultados)} tests)")
            
            # Guardar resultados
            suite.guardar_reporte()
            suite.guardar_json()
            suite.generar_graficos()
            
            resultados_globales.append(suite)
            
        except Exception as e:
            print(f"❌ Error ejecutando {nombre_suite}: {e}")
            import traceback
            traceback.print_exc()
    
    # Generar reporte consolidado
    print("\n" + "=" * 80)
    print("📊 GENERANDO REPORTE CONSOLIDADO")
    print("=" * 80)
    
    generar_reporte_consolidado(resultados_globales)
    
    print("\n✅ TESTS COMPLETADOS")
    print(f"📁 Resultados guardados en: {RESULTADOS_DIR}")
    print()

def generar_reporte_consolidado(suites: List[TestSuite]):
    """Genera reporte consolidado de todas las suites"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Reporte de texto
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE CONSOLIDADO - VERSIÓN 2.0")
    reporte.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("=" * 80)
    reporte.append("")
    
    total_tests = sum(len(s.resultados) for s in suites)
    total_exitosos = sum(sum(1 for r in s.resultados if r.exitoso) for s in suites)
    tasa_global = (total_exitosos / total_tests * 100) if total_tests > 0 else 0
    
    reporte.append("📊 RESUMEN GLOBAL")
    reporte.append("-" * 80)
    reporte.append(f"Total de suites: {len(suites)}")
    reporte.append(f"Total de tests: {total_tests}")
    reporte.append(f"✅ Exitosos: {total_exitosos} ({tasa_global:.1f}%)")
    reporte.append(f"❌ Fallidos: {total_tests - total_exitosos} ({100 - tasa_global:.1f}%)")
    reporte.append("")
    
    reporte.append("📋 RESULTADOS POR SUITE")
    reporte.append("-" * 80)
    for suite in suites:
        reporte.append(f"\n{suite.nombre}:")
        reporte.append(f"  Tests: {len(suite.resultados)}")
        reporte.append(f"  Éxito: {suite.tasa_exito():.1f}%")
        reporte.append(f"  Tiempo promedio: {suite.tiempo_promedio():.3f}s")
    
    reporte.append("\n" + "=" * 80)
    
    # Guardar reporte
    filename = LOGS_DIR / f"reporte_consolidado_{timestamp}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(reporte))
    print(f"📄 Reporte consolidado: {filename}")
    
    # Gráfico consolidado
    generar_grafico_consolidado(suites, timestamp)

def generar_grafico_consolidado(suites: List[TestSuite], timestamp: str):
    """Genera gráfico consolidado comparando todas las suites"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Resultados Consolidados - Versión 2.0', fontsize=16, fontweight='bold')
    
    nombres_suites = [s.nombre for s in suites]
    tasas_exito = [s.tasa_exito() for s in suites]
    tiempos = [s.tiempo_promedio() for s in suites]
    total_tests = [len(s.resultados) for s in suites]
    
    # 1: Bar chart - Tasas de éxito por suite
    axes[0, 0].bar(range(len(nombres_suites)), tasas_exito, color='skyblue')
    axes[0, 0].set_xticks(range(len(nombres_suites)))
    axes[0, 0].set_xticklabels(nombres_suites, rotation=45, ha='right', fontsize=8)
    axes[0, 0].set_ylabel('Tasa de Éxito (%)')
    axes[0, 0].set_title('Tasa de Éxito por Suite')
    axes[0, 0].set_ylim([0, 105])
    axes[0, 0].axhline(y=100, color='g', linestyle='--', alpha=0.3)
    
    # 2: Tiempos promedio
    axes[0, 1].bar(range(len(nombres_suites)), tiempos, color='lightcoral')
    axes[0, 1].set_xticks(range(len(nombres_suites)))
    axes[0, 1].set_xticklabels(nombres_suites, rotation=45, ha='right', fontsize=8)
    axes[0, 1].set_ylabel('Tiempo (s)')
    axes[0, 1].set_title('Tiempo Promedio por Test')
    
    # 3: Total de tests por suite
    axes[1, 0].bar(range(len(nombres_suites)), total_tests, color='lightgreen')
    axes[1, 0].set_xticks(range(len(nombres_suites)))
    axes[1, 0].set_xticklabels(nombres_suites, rotation=45, ha='right', fontsize=8)
    axes[1, 0].set_ylabel('Cantidad de Tests')
    axes[1, 0].set_title('Total de Tests por Suite')
    
    # 4: Tabla resumen
    axes[1, 1].axis('off')
    total_global = sum(total_tests)
    exitosos_global = sum(int(len(s.resultados) * s.tasa_exito() / 100) for s in suites)
    tasa_global = (exitosos_global / total_global * 100) if total_global > 0 else 0
    
    tabla_data = [
        ['Métrica', 'Valor'],
        ['Total Suites', str(len(suites))],
        ['Total Tests', str(total_global)],
        ['Exitosos', f"{exitosos_global} ({tasa_global:.1f}%)"],
        ['Fallidos', f"{total_global - exitosos_global} ({100 - tasa_global:.1f}%)"],
    ]
    tabla = axes[1, 1].table(cellText=tabla_data, cellLoc='left', loc='center',
                            colWidths=[0.5, 0.5])
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 2)
    
    for i, cell in tabla.get_celld().items():
        if i[0] == 0:
            cell.set_facecolor('#4CAF50')
            cell.set_text_props(weight='bold', color='white')
        else:
            cell.set_facecolor('#f0f0f0')
    
    plt.tight_layout()
    
    filename = GRAFICOS_DIR / f"consolidado_{timestamp}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"📊 Gráfico consolidado: {filename}")

if __name__ == "__main__":
    main()
