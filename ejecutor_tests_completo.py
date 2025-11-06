"""
EJECUTOR DE TESTS COMPLETO - VERSIÓN 2.0
Ejecuta TODOS los tests de la carpeta tests/ y genera reportes visuales completos

Genera:
- Reporte consolidado con todos los resultados
- Gráficos comparativos de rendimiento
- Análisis de éxito por categoría
- Métricas de tiempo de ejecución
- Comparativa V1.0 vs V2.0 (si aplica)
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

# Configurar paths
PROJECT_ROOT = Path(__file__).parent
TESTS_DIR = PROJECT_ROOT / "tests"
RESULTADOS_DIR = PROJECT_ROOT / "resultados"
GRAFICOS_DIR = RESULTADOS_DIR / "graficos"
LOGS_DIR = RESULTADOS_DIR / "logs"

# Crear directorios
GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

class TestResult:
    """Resultado de un test individual"""
    def __init__(self, archivo: str, exitoso: bool, tiempo: float, output: str = "", error: str = ""):
        self.archivo = archivo
        self.exitoso = exitoso
        self.tiempo = tiempo
        self.output = output
        self.error = error
        self.categoria = self._categorizar()
    
    def _categorizar(self) -> str:
        """Categoriza el test según su nombre"""
        nombre = self.archivo.lower()
        if 'nlu' in nombre or 'modelo' in nombre:
            return 'NLU/Modelo'
        elif 'conversacion' in nombre or 'flujo' in nombre:
            return 'Conversaciones'
        elif 'fuzzy' in nombre or 'difuso' in nombre:
            return 'Motor Difuso'
        elif 'email' in nombre:
            return 'Email'
        elif 'fecha' in nombre or 'temporal' in nombre or 'proxima' in nombre or 'semana' in nombre:
            return 'Referencias Temporales'
        elif 'urgencia' in nombre:
            return 'Urgencia'
        elif 'validacion' in nombre or 'cedula' in nombre or 'nombres' in nombre:
            return 'Validación'
        elif 'bd' in nombre or 'disponibilidad' in nombre or 'insert' in nombre:
            return 'Base de Datos'
        elif 'fix' in nombre or 'mejoras' in nombre or 'correcciones' in nombre:
            return 'Fixes/Mejoras'
        elif 'llm' in nombre or 'lm' in nombre:
            return 'LLM'
        else:
            return 'Otros'
    
    def to_dict(self):
        return {
            'archivo': self.archivo,
            'exitoso': self.exitoso,
            'tiempo': self.tiempo,
            'categoria': self.categoria,
            'output': self.output[:500] if self.output else "",  # Limitar output
            'error': self.error[:500] if self.error else ""
        }

class TestExecutor:
    """Ejecutor de tests con reporte completo"""
    
    def __init__(self):
        self.resultados: List[TestResult] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.tests_ignorados = [
            'test_stories.yml',  # No es un archivo Python
            'populate_turnos.py',  # Script de utilidad, no test
            'sync_calendar.py',   # Script de utilidad, no test
            '__pycache__',
            '__init__.py'
        ]
    
    def es_test_valido(self, archivo: str) -> bool:
        """Verifica si un archivo es un test válido"""
        if not archivo.endswith('.py'):
            return False
        if any(ignorar in archivo for ignorar in self.tests_ignorados):
            return False
        return True
    
    def ejecutar_test(self, archivo_path: Path) -> TestResult:
        """Ejecuta un test individual y retorna el resultado"""
        inicio = time.time()
        archivo = archivo_path.name
        
        print(f"  Ejecutando: {archivo:<50}...", end=" ", flush=True)
        
        try:
            # Preparar environment con PYTHONPATH correcto
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            # Agregar flask-chatbot al PYTHONPATH
            flask_chatbot_path = str(PROJECT_ROOT / 'flask-chatbot')
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{flask_chatbot_path}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = flask_chatbot_path
            
            # Ejecutar test con timeout de 30 segundos (más rápido)
            resultado = subprocess.run(
                [sys.executable, str(archivo_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT),  # Ejecutar desde la raíz del proyecto
                env=env
            )
            
            tiempo = time.time() - inicio
            exitoso = resultado.returncode == 0
            
            # Imprimir resultado
            if exitoso:
                print(f"[OK] PASS ({tiempo:.2f}s)")
            else:
                print(f"[FAIL] FAIL ({tiempo:.2f}s)")
            
            return TestResult(
                archivo=archivo,
                exitoso=exitoso,
                tiempo=tiempo,
                output=resultado.stdout,
                error=resultado.stderr
            )
            
        except subprocess.TimeoutExpired:
            tiempo = time.time() - inicio
            print(f"[TIMEOUT] ({tiempo:.2f}s)")
            return TestResult(
                archivo=archivo,
                exitoso=False,
                tiempo=tiempo,
                output="",
                error="Test excedió el tiempo límite de 30 segundos"
            )
        except Exception as e:
            tiempo = time.time() - inicio
            print(f"[ERROR] ({tiempo:.2f}s)")
            return TestResult(
                archivo=archivo,
                exitoso=False,
                tiempo=tiempo,
                output="",
                error=str(e)
            )
    
    def ejecutar_todos(self):
        """Ejecuta todos los tests en la carpeta tests/"""
        print("=" * 80)
        print("EJECUTANDO SUITE COMPLETA DE TESTS")
        print("=" * 80)
        print(f"Carpeta: {TESTS_DIR}")
        print()
        
        # Listar todos los archivos de test
        archivos_test = sorted([
            f for f in TESTS_DIR.iterdir() 
            if f.is_file() and self.es_test_valido(f.name)
        ])
        
        print(f"Total de tests a ejecutar: {len(archivos_test)}")
        print()
        
        # Ejecutar cada test
        for i, archivo_path in enumerate(archivos_test, 1):
            print(f"[{i}/{len(archivos_test)}]", end=" ")
            resultado = self.ejecutar_test(archivo_path)
            self.resultados.append(resultado)
        
        print()
        print("=" * 80)
        print("EJECUCION COMPLETADA")
        print("=" * 80)
    
    def generar_estadisticas(self) -> Dict:
        """Genera estadísticas globales"""
        total = len(self.resultados)
        exitosos = sum(1 for r in self.resultados if r.exitoso)
        fallidos = total - exitosos
        
        # Estadísticas por categoría
        por_categoria = defaultdict(lambda: {'total': 0, 'exitosos': 0, 'tiempo_total': 0})
        for r in self.resultados:
            por_categoria[r.categoria]['total'] += 1
            if r.exitoso:
                por_categoria[r.categoria]['exitosos'] += 1
            por_categoria[r.categoria]['tiempo_total'] += r.tiempo
        
        return {
            'total': total,
            'exitosos': exitosos,
            'fallidos': fallidos,
            'tasa_exito': (exitosos / total * 100) if total > 0 else 0,
            'tiempo_total': sum(r.tiempo for r in self.resultados),
            'tiempo_promedio': sum(r.tiempo for r in self.resultados) / total if total > 0 else 0,
            'por_categoria': dict(por_categoria)
        }
    
    def generar_reporte_texto(self) -> str:
        """Genera reporte en texto plano"""
        stats = self.generar_estadisticas()
        
        reporte = []
        reporte.append("=" * 80)
        reporte.append("REPORTE COMPLETO DE TESTS - VERSIÓN 2.0")
        reporte.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        reporte.append("=" * 80)
        reporte.append("")
        
        # Resumen global
        reporte.append("📊 RESUMEN GLOBAL")
        reporte.append("-" * 80)
        reporte.append(f"Total de tests ejecutados: {stats['total']}")
        reporte.append(f"✅ Exitosos: {stats['exitosos']} ({stats['tasa_exito']:.1f}%)")
        reporte.append(f"❌ Fallidos: {stats['fallidos']} ({100 - stats['tasa_exito']:.1f}%)")
        reporte.append(f"⏱️  Tiempo total: {stats['tiempo_total']:.2f}s")
        reporte.append(f"⏱️  Tiempo promedio: {stats['tiempo_promedio']:.2f}s")
        reporte.append("")
        
        # Resumen por categoría
        reporte.append("📋 RESUMEN POR CATEGORÍA")
        reporte.append("-" * 80)
        for categoria, datos in sorted(stats['por_categoria'].items()):
            tasa = (datos['exitosos'] / datos['total'] * 100) if datos['total'] > 0 else 0
            tiempo_prom = datos['tiempo_total'] / datos['total'] if datos['total'] > 0 else 0
            reporte.append(f"\n{categoria}:")
            reporte.append(f"  Tests: {datos['total']}")
            reporte.append(f"  Exitosos: {datos['exitosos']} ({tasa:.1f}%)")
            reporte.append(f"  Tiempo promedio: {tiempo_prom:.2f}s")
        
        reporte.append("")
        reporte.append("")
        
        # Detalle de tests fallidos
        fallidos = [r for r in self.resultados if not r.exitoso]
        if fallidos:
            reporte.append("❌ TESTS FALLIDOS")
            reporte.append("-" * 80)
            for i, resultado in enumerate(fallidos, 1):
                reporte.append(f"\n{i}. {resultado.archivo}")
                reporte.append(f"   Categoría: {resultado.categoria}")
                reporte.append(f"   Tiempo: {resultado.tiempo:.2f}s")
                if resultado.error:
                    error_lines = resultado.error.split('\n')[:5]  # Primeras 5 líneas
                    reporte.append(f"   Error: {chr(10).join(error_lines)}")
        
        reporte.append("")
        reporte.append("")
        
        # Lista completa de tests
        reporte.append("📝 LISTA COMPLETA DE TESTS")
        reporte.append("-" * 80)
        for i, resultado in enumerate(self.resultados, 1):
            estado = "✅ PASS" if resultado.exitoso else "❌ FAIL"
            reporte.append(f"{i:3}. {estado} | {resultado.tiempo:6.2f}s | {resultado.categoria:20} | {resultado.archivo}")
        
        reporte.append("")
        reporte.append("=" * 80)
        return "\n".join(reporte)
    
    def guardar_reporte(self):
        """Guarda reporte en archivo de texto"""
        filename = LOGS_DIR / f"reporte_completo_{self.timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.generar_reporte_texto())
        print(f"📄 Reporte guardado: {filename}")
        return filename
    
    def guardar_json(self):
        """Guarda resultados en JSON"""
        filename = LOGS_DIR / f"resultados_completos_{self.timestamp}.json"
        stats = self.generar_estadisticas()
        datos = {
            'timestamp': self.timestamp,
            'estadisticas': stats,
            'resultados': [r.to_dict() for r in self.resultados]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        print(f"💾 JSON guardado: {filename}")
        return filename
    
    def generar_graficos(self):
        """Genera gráficos completos de resultados"""
        if not self.resultados:
            print("⚠️ No hay resultados para graficar")
            return
        
        stats = self.generar_estadisticas()
        
        # Crear figura con 6 subplots
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Título principal
        fig.suptitle('Reporte Completo de Tests - Chatbot V2.0', fontsize=20, fontweight='bold')
        
        # 1. Pie chart - Éxito global
        ax1 = fig.add_subplot(gs[0, 0])
        colors = ['#4CAF50', '#F44336']
        explode = (0.1, 0)
        ax1.pie([stats['exitosos'], stats['fallidos']], 
                labels=['Exitosos', 'Fallidos'],
                autopct='%1.1f%%', 
                colors=colors, 
                explode=explode, 
                shadow=True,
                startangle=90)
        ax1.set_title(f"Tasa de Éxito Global: {stats['tasa_exito']:.1f}%", fontweight='bold')
        
        # 2. Bar chart - Tests por categoría
        ax2 = fig.add_subplot(gs[0, 1])
        categorias = sorted(stats['por_categoria'].keys())
        totales = [stats['por_categoria'][c]['total'] for c in categorias]
        exitosos_cat = [stats['por_categoria'][c]['exitosos'] for c in categorias]
        
        x = range(len(categorias))
        width = 0.35
        ax2.bar([i - width/2 for i in x], totales, width, label='Total', color='skyblue')
        ax2.bar([i + width/2 for i in x], exitosos_cat, width, label='Exitosos', color='lightgreen')
        ax2.set_xlabel('Categoría')
        ax2.set_ylabel('Cantidad de Tests')
        ax2.set_title('Tests por Categoría', fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(categorias, rotation=45, ha='right', fontsize=8)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. Bar chart - Tasa de éxito por categoría
        ax3 = fig.add_subplot(gs[0, 2])
        tasas = [(stats['por_categoria'][c]['exitosos'] / stats['por_categoria'][c]['total'] * 100) 
                 for c in categorias]
        colores_tasas = ['green' if t >= 80 else 'orange' if t >= 50 else 'red' for t in tasas]
        ax3.barh(categorias, tasas, color=colores_tasas)
        ax3.set_xlabel('Tasa de Éxito (%)')
        ax3.set_title('Tasa de Éxito por Categoría', fontweight='bold')
        ax3.set_xlim([0, 105])
        ax3.axvline(x=80, color='gray', linestyle='--', alpha=0.5, label='80% target')
        ax3.legend()
        ax3.grid(axis='x', alpha=0.3)
        
        # 4. Scatter plot - Tiempo vs Éxito
        ax4 = fig.add_subplot(gs[1, 0])
        colores_scatter = ['green' if r.exitoso else 'red' for r in self.resultados]
        tiempos = [r.tiempo for r in self.resultados]
        indices = range(len(self.resultados))
        ax4.scatter(indices, tiempos, c=colores_scatter, alpha=0.6, s=50)
        ax4.axhline(y=stats['tiempo_promedio'], color='blue', linestyle='--', 
                    label=f'Promedio: {stats["tiempo_promedio"]:.2f}s')
        ax4.set_xlabel('Test #')
        ax4.set_ylabel('Tiempo (s)')
        ax4.set_title('Tiempos de Ejecución', fontweight='bold')
        ax4.legend()
        ax4.grid(alpha=0.3)
        
        # 5. Box plot - Distribución de tiempos por categoría
        ax5 = fig.add_subplot(gs[1, 1])
        datos_box = []
        labels_box = []
        for cat in categorias:
            tiempos_cat = [r.tiempo for r in self.resultados if r.categoria == cat]
            if tiempos_cat:
                datos_box.append(tiempos_cat)
                labels_box.append(cat)
        
        bp = ax5.boxplot(datos_box, labels=labels_box, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        ax5.set_ylabel('Tiempo (s)')
        ax5.set_title('Distribución de Tiempos por Categoría', fontweight='bold')
        ax5.tick_params(axis='x', rotation=45)
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=8)
        ax5.grid(axis='y', alpha=0.3)
        
        # 6. Tabla resumen
        ax6 = fig.add_subplot(gs[1, 2])
        ax6.axis('off')
        tabla_data = [
            ['Métrica', 'Valor'],
            ['Total Tests', str(stats['total'])],
            ['Exitosos', f"{stats['exitosos']} ({stats['tasa_exito']:.1f}%)"],
            ['Fallidos', f"{stats['fallidos']} ({100 - stats['tasa_exito']:.1f}%)"],
            ['Tiempo Total', f"{stats['tiempo_total']:.2f}s"],
            ['Tiempo Promedio', f"{stats['tiempo_promedio']:.2f}s"],
            ['Categorías', str(len(categorias))]
        ]
        tabla = ax6.table(cellText=tabla_data, cellLoc='left', loc='center',
                         colWidths=[0.5, 0.5])
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(10)
        tabla.scale(1, 2)
        
        # Aplicar colores
        for i, cell in tabla.get_celld().items():
            if i[0] == 0:  # Header
                cell.set_facecolor('#4CAF50')
                cell.set_text_props(weight='bold', color='white')
            else:
                cell.set_facecolor('#f0f0f0')
        
        ax6.set_title('Resumen Ejecutivo', fontweight='bold', pad=20)
        
        # 7-9. Top 10 tests más lentos, más rápidos, y tests fallidos
        ax7 = fig.add_subplot(gs[2, :])
        ax7.axis('off')
        
        # Tests más lentos
        lentos = sorted(self.resultados, key=lambda r: r.tiempo, reverse=True)[:10]
        texto_lentos = "🐌 TOP 10 TESTS MÁS LENTOS:\n"
        for i, r in enumerate(lentos, 1):
            estado = "✅" if r.exitoso else "❌"
            texto_lentos += f"{i}. {estado} {r.archivo[:40]:40} | {r.tiempo:6.2f}s | {r.categoria}\n"
        
        # Tests fallidos
        fallidos_list = [r for r in self.resultados if not r.exitoso]
        if fallidos_list:
            texto_fallidos = f"\n❌ TESTS FALLIDOS ({len(fallidos_list)}):\n"
            for i, r in enumerate(fallidos_list[:10], 1):
                texto_fallidos += f"{i}. {r.archivo[:40]:40} | {r.tiempo:6.2f}s | {r.categoria}\n"
        else:
            texto_fallidos = "\n✅ ¡TODOS LOS TESTS PASARON!\n"
        
        ax7.text(0.05, 0.95, texto_lentos + texto_fallidos, 
                transform=ax7.transAxes,
                fontsize=9,
                verticalalignment='top',
                fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Guardar
        filename = GRAFICOS_DIR / f"reporte_completo_{self.timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"📊 Gráfico guardado: {filename}")
        
        return filename

def main():
    """Función principal"""
    # Configurar encoding para Windows
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    print("\n" + "=" * 80)
    print("INICIANDO EJECUCION COMPLETA DE TESTS")
    print("=" * 80)
    print()
    
    executor = TestExecutor()
    
    # Ejecutar todos los tests
    executor.ejecutar_todos()
    
    # Generar reportes
    print()
    print("=" * 80)
    print("GENERANDO REPORTES")
    print("=" * 80)
    print()
    
    executor.guardar_reporte()
    executor.guardar_json()
    executor.generar_graficos()
    
    # Mostrar resumen final
    stats = executor.generar_estadisticas()
    print()
    print("=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    print(f"Total: {stats['total']} tests")
    print(f"[OK] Exitosos: {stats['exitosos']} ({stats['tasa_exito']:.1f}%)")
    print(f"[FAIL] Fallidos: {stats['fallidos']} ({100 - stats['tasa_exito']:.1f}%)")
    print(f"Tiempo total: {stats['tiempo_total']:.2f}s")
    print(f"Tiempo promedio: {stats['tiempo_promedio']:.2f}s")
    print()
    print(f"Resultados guardados en: {RESULTADOS_DIR}")
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()
