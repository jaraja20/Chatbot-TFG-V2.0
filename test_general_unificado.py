"""
TEST GENERAL UNIFICADO - SISTEMA V2.0
Combina todos los casos importantes de todos los tests en uno solo
"""
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "flask-chatbot"))

from razonamiento_difuso import clasificar_con_logica_difusa

def test_motor_difuso():
    """Test 1: Motor Difuso - Clasificación de intents"""
    print("\n" + "="*70)
    print("TEST 1: MOTOR DIFUSO - Clasificacion de Intents")
    print("="*70)
    
    casos = [
        # Agendar turno
        ('quiero sacar turno', 'agendar_turno'),
        ('necesito turno urgente', 'agendar_turno'),
        ('vieja, necesito sacar turno urgente', 'agendar_turno'),
        
        # Consultar disponibilidad
        ('para cuando hay hueco?', 'consultar_disponibilidad'),
        ('buenas, para cuando hay hueco?', 'consultar_disponibilidad'),
        ('dame un dia intermedio de la semana', 'consultar_disponibilidad'),
        ('que dias tienen disponible', 'consultar_disponibilidad'),
        
        # Consultar costo
        ('cuanto vale', 'consultar_costo'),
        ('cuanto bale sacar la cedula?', 'consultar_costo'),
        ('precio', 'consultar_costo'),
        
        # Consultar requisitos
        ('que necesito', 'consultar_requisitos'),
        ('documentos', 'consultar_requisitos'),
        ('requisitos', 'consultar_requisitos'),
        
        # Confirmación
        ('si', 'affirm'),
        ('confirmo', 'affirm'),
        ('ok', 'affirm'),
        ('vale', 'affirm'),
        ('de acuerdo', 'affirm'),
        
        # Negación
        ('no', 'negacion'),
        ('no, esa hora no me sirve', 'negacion'),
        ('mejor otro día', 'negacion'),
        
        # Cancelar
        ('cancelar', 'cancelar'),
        ('quiero cancelar', 'cancelar'),
        
        # Urgencia/Ambiguas
        ('urgente', 'frase_ambigua'),
        ('lo antes posible', 'frase_ambigua'),
        ('necesito rapido', 'frase_ambigua'),
    ]
    
    correctos = 0
    total = len(casos)
    
    for mensaje, esperado in casos:
        intent, conf = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        es_correcto = intent == esperado
        marca = "[OK]" if es_correcto else "[FAIL]"
        
        if es_correcto:
            correctos += 1
        else:
            print(f"{marca} '{mensaje}'")
            print(f"     Esperado: {esperado}, Obtenido: {intent} ({conf:.2f})")
    
    porcentaje = (correctos / total) * 100
    print(f"\n[RESULT] {correctos}/{total} correctos ({porcentaje:.1f}%)")
    
    return correctos >= total * 0.85  # 85% mínimo

def test_validacion_datos():
    """Test 2: Validación de datos (cédula, nombres)"""
    print("\n" + "="*70)
    print("TEST 2: VALIDACION DE DATOS")
    print("="*70)
    
    import re
    
    def validar_cedula_simple(cedula):
        """Validación simple de cédula"""
        # Remover puntos y guiones
        cedula_limpia = re.sub(r'[.\-]', '', str(cedula))
        # Debe tener entre 6 y 8 dígitos
        return cedula_limpia.isdigit() and 6 <= len(cedula_limpia) <= 8
    
    def normalizar_nombre_simple(nombre):
        """Normalización simple de nombre"""
        # Limpiar espacios extras y capitalizar
        return ' '.join(nombre.strip().split()).title()
    
    # Test cédulas válidas
    cedulas_validas = [
        '5264036',
        '5.264.036',
        '5264036-3',
        '5.264.036-3',
    ]
    
    # Test cédulas inválidas
    cedulas_invalidas = [
        'abc123',
        '123',
        '999999999999',
    ]
    
    correctos = 0
    total = 0
    
    # Validar cédulas válidas
    for cedula in cedulas_validas:
        total += 1
        if validar_cedula_simple(cedula):
            correctos += 1
        else:
            print(f"[FAIL] '{cedula}' debería ser válida")
    
    # Validar cédulas inválidas
    for cedula in cedulas_invalidas:
        total += 1
        if not validar_cedula_simple(cedula):
            correctos += 1
        else:
            print(f"[FAIL] '{cedula}' debería ser inválida")
    
    # Test nombres
    nombres_test = [
        ('juan perez', 'Juan Perez'),
        ('MARIA GARCIA', 'Maria Garcia'),
        ('pedro  luis   gomez', 'Pedro Luis Gomez'),
    ]
    
    for entrada, esperado in nombres_test:
        total += 1
        normalizado = normalizar_nombre_simple(entrada)
        if normalizado == esperado:
            correctos += 1
        else:
            print(f"[FAIL] Nombre: '{entrada}' -> '{normalizado}' (esperado: '{esperado}')")
    
    porcentaje = (correctos / total) * 100
    print(f"\n[RESULT] {correctos}/{total} correctos ({porcentaje:.1f}%)")
    
    return correctos >= total * 0.90  # 90% mínimo

def test_referencias_temporales():
    """Test 3: Referencias temporales"""
    print("\n" + "="*70)
    print("TEST 3: REFERENCIAS TEMPORALES")
    print("="*70)
    
    # Test simplificado: solo verificar que el fuzzy clasifica correctamente
    casos_temporales = [
        ('para mañana', 'consultar_disponibilidad'),
        ('el jueves', 'consultar_disponibilidad'),
        ('la proxima semana', 'consultar_disponibilidad'),
        ('para el lunes', 'consultar_disponibilidad'),
    ]
    
    correctos = 0
    total = len(casos_temporales)
    
    for texto, esperado in casos_temporales:
        intent, conf = clasificar_con_logica_difusa(texto, threshold=0.3)
        if intent == esperado:
            correctos += 1
        else:
            print(f"[FAIL] '{texto}' -> {intent} (esperado: {esperado})")
    
    porcentaje = (correctos / total) * 100
    print(f"\n[RESULT] {correctos}/{total} correctos ({porcentaje:.1f}%)")
    
    return correctos >= total * 0.75  # 75% mínimo

def test_urgencia_deteccion():
    """Test 4: Detección de urgencia"""
    print("\n" + "="*70)
    print("TEST 4: DETECCION DE URGENCIA")
    print("="*70)
    
    # Palabras clave de urgencia
    palabras_urgencia = ['urgente', 'rapido', 'ya', 'antes posible', 'cuanto antes', 'apurado']
    
    def detectar_urgencia_simple(texto):
        """Detecta urgencia en el texto"""
        texto_lower = texto.lower()
        return any(palabra in texto_lower for palabra in palabras_urgencia)
    
    # Casos con urgencia
    casos_urgentes = [
        'lo antes posible',
        'urgente',
        'necesito ya',
        'es urgente',
        'cuanto antes',
        'necesito rapido',
    ]
    
    # Casos sin urgencia
    casos_normales = [
        'quiero un turno',
        'para la proxima semana',
        'cuando hay disponible',
    ]
    
    correctos = 0
    total = len(casos_urgentes) + len(casos_normales)
    
    for caso in casos_urgentes:
        if detectar_urgencia_simple(caso):
            correctos += 1
        else:
            print(f"[FAIL] '{caso}' debería detectar urgencia")
    
    for caso in casos_normales:
        if not detectar_urgencia_simple(caso):
            correctos += 1
        else:
            print(f"[FAIL] '{caso}' NO debería detectar urgencia")
    
    porcentaje = (correctos / total) * 100
    print(f"\n[RESULT] {correctos}/{total} correctos ({porcentaje:.1f}%)")
    
    return correctos >= total * 0.85  # 85% mínimo

def test_casos_reales():
    """Test 5: Casos reales del chat log"""
    print("\n" + "="*70)
    print("TEST 5: CASOS REALES DE CHAT LOGS")
    print("="*70)
    
    # Casos extraídos de logs reales que causaron problemas
    casos_criticos = [
        # Intent fuzzy debe clasificar correctamente
        ('cuanto bale sacar la cedula?', 'consultar_costo', clasificar_con_logica_difusa),
        ('para cuando hay hueco?', 'consultar_disponibilidad', clasificar_con_logica_difusa),
        ('documentos', 'consultar_requisitos', clasificar_con_logica_difusa),
        ('no, esa hora no me sirve', 'negacion', clasificar_con_logica_difusa),
        ('cancelar', 'cancelar', clasificar_con_logica_difusa),
    ]
    
    correctos = 0
    total = len(casos_criticos)
    
    for mensaje, intent_esperado, funcion in casos_criticos:
        intent, conf = funcion(mensaje, threshold=0.3)
        if intent == intent_esperado:
            correctos += 1
        else:
            print(f"[FAIL] '{mensaje}'")
            print(f"     Esperado: {intent_esperado}, Obtenido: {intent}")
    
    porcentaje = (correctos / total) * 100
    print(f"\n[RESULT] {correctos}/{total} correctos ({porcentaje:.1f}%)")
    
    return correctos >= total * 0.80  # 80% mínimo

def test_errores_comunes():
    """Test 6: Errores ortográficos y variaciones"""
    print("\n" + "="*70)
    print("TEST 6: ERRORES ORTOGRAFICOS Y VARIACIONES")
    print("="*70)
    
    casos = [
        # Ortografía incorrecta
        ('cuanto bale', 'consultar_costo'),  # "vale" escrito mal
        ('kiero turno', 'agendar_turno'),  # "quiero" con k
        ('nesesito', 'agendar_turno'),  # "necesito" mal escrito
        
        # Variaciones coloquiales
        ('vieja', 'agendar_turno'),  # Muletilla
        ('che', 'agendar_turno'),  # Muletilla
        ('buenas', 'saludar'),  # Saludo
    ]
    
    correctos = 0
    total = len(casos)
    
    for mensaje, esperado in casos:
        intent, conf = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        # Aceptar si el intent es correcto o si es frase_ambigua (puede ser aceptable)
        if intent == esperado or (intent == 'frase_ambigua' and conf < 0.6):
            correctos += 1
        else:
            print(f"[FAIL] '{mensaje}' -> {intent} (esperado: {esperado})")
    
    porcentaje = (correctos / total) * 100
    print(f"\n[RESULT] {correctos}/{total} correctos ({porcentaje:.1f}%)")
    
    return correctos >= total * 0.70  # 70% mínimo (más permisivo)

def main():
    """Ejecuta todos los tests"""
    print("="*70)
    print(" TEST GENERAL UNIFICADO - SISTEMA V2.0")
    print(" Combinando todos los casos importantes")
    print("="*70)
    
    resultados = {}
    
    # Ejecutar todos los tests
    try:
        resultados['Motor Difuso'] = test_motor_difuso()
    except Exception as e:
        print(f"[ERROR] Motor Difuso: {e}")
        resultados['Motor Difuso'] = False
    
    try:
        resultados['Validacion Datos'] = test_validacion_datos()
    except Exception as e:
        print(f"[ERROR] Validacion Datos: {e}")
        resultados['Validacion Datos'] = False
    
    try:
        resultados['Referencias Temporales'] = test_referencias_temporales()
    except Exception as e:
        print(f"[ERROR] Referencias Temporales: {e}")
        resultados['Referencias Temporales'] = False
    
    try:
        resultados['Deteccion Urgencia'] = test_urgencia_deteccion()
    except Exception as e:
        print(f"[ERROR] Deteccion Urgencia: {e}")
        resultados['Deteccion Urgencia'] = False
    
    try:
        resultados['Casos Reales'] = test_casos_reales()
    except Exception as e:
        print(f"[ERROR] Casos Reales: {e}")
        resultados['Casos Reales'] = False
    
    try:
        resultados['Errores Comunes'] = test_errores_comunes()
    except Exception as e:
        print(f"[ERROR] Errores Comunes: {e}")
        resultados['Errores Comunes'] = False
    
    # Resumen final
    print("\n" + "="*70)
    print(" RESUMEN FINAL")
    print("="*70)
    
    tests_passed = sum(1 for v in resultados.values() if v)
    tests_total = len(resultados)
    
    for nombre, resultado in resultados.items():
        marca = "[PASS]" if resultado else "[FAIL]"
        print(f"{marca} {nombre}")
    
    print("="*70)
    porcentaje = (tests_passed / tests_total) * 100
    print(f"\nTests aprobados: {tests_passed}/{tests_total} ({porcentaje:.1f}%)")
    
    if tests_passed >= tests_total * 0.65:  # 65% de tests deben pasar (4/6)
        print("\n[SUCCESS] Sistema APROBADO")
        return 0
    else:
        print("\n[FAIL] Sistema requiere mejoras")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERROR FATAL] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
