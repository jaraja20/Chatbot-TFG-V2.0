import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import logging
import datetime
from typing import Tuple, Dict, List

# Configurar logging
logger = logging.getLogger(__name__)

# =====================================================
# VARIABLES DIFUSAS PRINCIPALES
# =====================================================

# Variables de entrada
ocupacion = ctrl.Antecedent(np.arange(0, 101, 1), 'ocupacion')
urgencia = ctrl.Antecedent(np.arange(0, 11, 1), 'urgencia')
hora_dia = ctrl.Antecedent(np.arange(7, 18, 1), 'hora_dia')  # 7:00 - 17:00

# Variables de salida
espera = ctrl.Consequent(np.arange(0, 121, 1), 'espera')  # 0-120 minutos
recomendacion = ctrl.Consequent(np.arange(0, 101, 1), 'recomendacion')  # 0-100 (score)

# =====================================================
# FUNCIONES DE PERTENENCIA - ENTRADA
# =====================================================

# Ocupación de la oficina
ocupacion['baja'] = fuzz.trimf(ocupacion.universe, [0, 0, 35])
ocupacion['media'] = fuzz.trimf(ocupacion.universe, [25, 50, 75])
ocupacion['alta'] = fuzz.trimf(ocupacion.universe, [65, 100, 100])

# Urgencia del usuario (1=no urgente, 10=muy urgente)
urgencia['baja'] = fuzz.trimf(urgencia.universe, [0, 0, 3])
urgencia['media'] = fuzz.trimf(urgencia.universe, [2, 5, 8])
urgencia['alta'] = fuzz.trimf(urgencia.universe, [7, 10, 10])

# Hora del día (factor de saturación por horario)
hora_dia['temprano'] = fuzz.trimf(hora_dia.universe, [7, 7, 9])    # 7:00-9:00
hora_dia['manana'] = fuzz.trimf(hora_dia.universe, [8, 10, 12])    # 8:00-12:00
hora_dia['mediodia'] = fuzz.trimf(hora_dia.universe, [11, 13, 15])  # 11:00-15:00
hora_dia['tarde'] = fuzz.trimf(hora_dia.universe, [14, 16, 17])     # 14:00-17:00

# =====================================================
# FUNCIONES DE PERTENENCIA - SALIDA
# =====================================================

# Tiempo de espera estimado
espera['muy_corta'] = fuzz.trimf(espera.universe, [0, 0, 15])      # 0-15 min
espera['corta'] = fuzz.trimf(espera.universe, [10, 25, 40])        # 10-40 min
espera['media'] = fuzz.trimf(espera.universe, [35, 50, 65])        # 35-65 min
espera['larga'] = fuzz.trimf(espera.universe, [60, 80, 100])       # 60-100 min
espera['muy_larga'] = fuzz.trimf(espera.universe, [95, 120, 120])  # 95-120 min

# Puntuación de recomendación (0=no recomendado, 100=altamente recomendado)
recomendacion['muy_baja'] = fuzz.trimf(recomendacion.universe, [0, 0, 20])
recomendacion['baja'] = fuzz.trimf(recomendacion.universe, [15, 35, 55])
recomendacion['media'] = fuzz.trimf(recomendacion.universe, [45, 65, 85])
recomendacion['alta'] = fuzz.trimf(recomendacion.universe, [75, 100, 100])

# =====================================================
# REGLAS DIFUSAS PARA TIEMPO DE ESPERA
# =====================================================

# Reglas básicas de ocupación y urgencia
regla1 = ctrl.Rule(ocupacion['baja'] & urgencia['alta'], espera['muy_corta'])
regla2 = ctrl.Rule(ocupacion['baja'] & urgencia['media'], espera['corta'])
regla3 = ctrl.Rule(ocupacion['baja'] & urgencia['baja'], espera['corta'])

regla4 = ctrl.Rule(ocupacion['media'] & urgencia['alta'], espera['corta'])
regla5 = ctrl.Rule(ocupacion['media'] & urgencia['media'], espera['media'])
regla6 = ctrl.Rule(ocupacion['media'] & urgencia['baja'], espera['media'])

regla7 = ctrl.Rule(ocupacion['alta'] & urgencia['alta'], espera['media'])
regla8 = ctrl.Rule(ocupacion['alta'] & urgencia['media'], espera['larga'])
regla9 = ctrl.Rule(ocupacion['alta'] & urgencia['baja'], espera['muy_larga'])

# Reglas considerando hora del día
regla10 = ctrl.Rule(hora_dia['temprano'] & ocupacion['baja'], espera['muy_corta'])
regla11 = ctrl.Rule(hora_dia['mediodia'] & ocupacion['alta'], espera['muy_larga'])
regla12 = ctrl.Rule(hora_dia['tarde'] & ocupacion['media'], espera['corta'])

# Reglas adicionales por horarios específicos
regla13 = ctrl.Rule(hora_dia['manana'] & ocupacion['media'], espera['corta'])
regla14 = ctrl.Rule(hora_dia['temprano'] & urgencia['alta'], espera['muy_corta'])
regla15 = ctrl.Rule(hora_dia['mediodia'] & urgencia['baja'], espera['muy_larga'])

# =====================================================
# REGLAS DIFUSAS PARA RECOMENDACIÓN
# =====================================================

# Mejores horarios (menos ocupación = mejor recomendación)
rec_regla1 = ctrl.Rule(ocupacion['baja'] & hora_dia['temprano'], recomendacion['alta'])
rec_regla2 = ctrl.Rule(ocupacion['baja'] & hora_dia['tarde'], recomendacion['alta'])
rec_regla3 = ctrl.Rule(ocupacion['media'] & hora_dia['manana'], recomendacion['media'])
rec_regla4 = ctrl.Rule(ocupacion['alta'] & hora_dia['mediodia'], recomendacion['muy_baja'])
rec_regla5 = ctrl.Rule(ocupacion['alta'], recomendacion['baja'])
rec_regla6 = ctrl.Rule(ocupacion['baja'], recomendacion['alta'])
rec_regla7 = ctrl.Rule(hora_dia['temprano'], recomendacion['alta'])
rec_regla8 = ctrl.Rule(hora_dia['mediodia'], recomendacion['muy_baja'])

# Sistemas de control
sistema_espera = ctrl.ControlSystem([
    regla1, regla2, regla3, regla4, regla5, regla6, regla7, regla8, regla9,
    regla10, regla11, regla12, regla13, regla14, regla15
])

sistema_recomendacion = ctrl.ControlSystem([
    rec_regla1, rec_regla2, rec_regla3, rec_regla4, 
    rec_regla5, rec_regla6, rec_regla7, rec_regla8
])

# =====================================================
# FUNCIONES PRINCIPALES
# =====================================================

def calcular_espera(ocupacion_valor: float, urgencia_valor: float, hora_valor: float = 12) -> float:
    """
    Calcula el tiempo de espera estimado usando lógica difusa
    
    Args:
        ocupacion_valor: Porcentaje de ocupación (0-100)
        urgencia_valor: Nivel de urgencia (0-10)
        hora_valor: Hora del día (7-17, opcional)
    
    Returns:
        float: Tiempo de espera en minutos
    """
    try:
        simulacion = ctrl.ControlSystemSimulation(sistema_espera)
        
        # Validar rangos de entrada
        ocupacion_valor = max(0, min(100, ocupacion_valor))
        urgencia_valor = max(0, min(10, urgencia_valor))
        hora_valor = max(7, min(17, hora_valor))
        
        simulacion.input['ocupacion'] = ocupacion_valor
        simulacion.input['urgencia'] = urgencia_valor
        simulacion.input['hora_dia'] = hora_valor
        
        simulacion.compute()
        
        resultado = simulacion.output['espera']
        return round(resultado, 1)
        
    except Exception as e:
        logger.error(f"Error en cálculo difuso de espera: {e}")
        # Fallback a cálculo simple
        base = ocupacion_valor * 0.8 + urgencia_valor * 3
        return round(min(120, max(5, base)), 1)

def evaluar_recomendacion(ocupacion_valor: float, hora_valor: float = 12) -> float:
    """
    Evalúa qué tan recomendable es un horario específico
    
    Args:
        ocupacion_valor: Porcentaje de ocupación (0-100)
        hora_valor: Hora del día (7-17)
    
    Returns:
        float: Puntuación de recomendación (0-100)
    """
    try:
        simulacion = ctrl.ControlSystemSimulation(sistema_recomendacion)
        
        # Validar rangos
        ocupacion_valor = max(0, min(100, ocupacion_valor))
        hora_valor = max(7, min(17, hora_valor))
        
        simulacion.input['ocupacion'] = ocupacion_valor
        simulacion.input['hora_dia'] = hora_valor
        
        simulacion.compute()
        
        resultado = simulacion.output['recomendacion']
        return round(resultado, 1)
        
    except Exception as e:
        logger.error(f"Error en evaluación difusa de recomendación: {e}")
        # Fallback simple: mejor puntuación = menor ocupación
        return round(100 - ocupacion_valor, 1)

def analizar_disponibilidad_dia(fecha: datetime.date) -> Dict[str, Dict]:
    """
    Analiza la disponibilidad completa de un día usando lógica difusa
    
    Args:
        fecha: Fecha a analizar
    
    Returns:
        Dict con análisis por franjas horarias
    """
    franjas = {
        'temprano': {'rango': '07:00-09:00', 'horas': [7, 7.5, 8, 8.5, 9]},
        'manana': {'rango': '09:30-11:30', 'horas': [9.5, 10, 10.5, 11, 11.5]},
        'mediodia': {'rango': '12:00-14:00', 'horas': [12, 12.5, 13, 13.5, 14]},
        'tarde': {'rango': '14:30-16:30', 'horas': [14.5, 15, 15.5, 16, 16.5]}
    }
    
    resultados = {}
    
    for nombre_franja, datos in franjas.items():
        ocupacion_promedio = 0
        recomendacion_promedio = 0
        espera_promedio = 0
        
        for hora_decimal in datos['horas']:
            # Simular ocupación basada en patrones reales
            ocupacion = simular_ocupacion(fecha, hora_decimal)
            urgencia = 5  # Nivel medio por defecto
            
            espera_tiempo = calcular_espera(ocupacion, urgencia, hora_decimal)
            recomendacion_score = evaluar_recomendacion(ocupacion, hora_decimal)
            
            ocupacion_promedio += ocupacion
            espera_promedio += espera_tiempo
            recomendacion_promedio += recomendacion_score
        
        # Promediar resultados
        ocupacion_promedio /= len(datos['horas'])
        espera_promedio /= len(datos['horas'])
        recomendacion_promedio /= len(datos['horas'])
        
        resultados[nombre_franja] = {
            'rango': datos['rango'],
            'ocupacion': round(ocupacion_promedio, 1),
            'espera_estimada': round(espera_promedio, 1),
            'recomendacion': round(recomendacion_promedio, 1),
            'horarios_sugeridos': generar_horarios_especificos(datos['horas'][:3])
        }
    
    return resultados

def simular_ocupacion(fecha: datetime.date, hora_decimal: float) -> float:
    """
    Simula ocupación realista basada en patrones de oficinas públicas
    """
    hora = int(hora_decimal)
    dia_semana = fecha.weekday()  # 0=lunes, 6=domingo
    
    # Factores base por hora
    factores_hora = {
        7: 25, 8: 45, 9: 70, 10: 85, 11: 90,
        12: 95, 13: 100, 14: 95, 15: 80, 16: 60, 17: 40
    }
    
    factor_hora = factores_hora.get(hora, 50)
    
    # Ajustes por día de la semana
    if dia_semana == 0:  # Lunes
        factor_hora *= 1.2
    elif dia_semana == 4:  # Viernes
        factor_hora *= 1.1
    elif dia_semana in [1, 2, 3]:  # Martes a jueves
        factor_hora *= 0.9
    
    # Variación aleatoria pequeña
    import random
    variacion = random.uniform(-10, 10)
    
    ocupacion_final = factor_hora + variacion
    return max(0, min(100, ocupacion_final))

def generar_horarios_especificos(horas_decimales: List[float]) -> List[str]:
    """
    Convierte horas decimales a formato HH:MM
    """
    horarios = []
    for hora_decimal in horas_decimales:
        hora = int(hora_decimal)
        minuto = int((hora_decimal % 1) * 60)
        horarios.append(f"{hora:02d}:{minuto:02d}")
    return horarios

def obtener_mejor_recomendacion(fecha: datetime.date, preferencia_usuario: str = None) -> Tuple[str, Dict]:
    """
    Obtiene la mejor recomendación para una fecha específica
    
    Args:
        fecha: Fecha objetivo
        preferencia_usuario: 'temprano', 'tarde', etc. (opcional)
    
    Returns:
        Tupla con (nombre_mejor_franja, datos_completos)
    """
    analisis = analizar_disponibilidad_dia(fecha)
    
    # Si hay preferencia específica, priorizarla
    if preferencia_usuario and preferencia_usuario in analisis:
        return preferencia_usuario, analisis[preferencia_usuario]
    
    # Ordenar por mejor recomendación
    franjas_ordenadas = sorted(
        analisis.items(), 
        key=lambda x: x[1]['recomendacion'], 
        reverse=True
    )
    
    mejor_franja = franjas_ordenadas[0]
    return mejor_franja[0], mejor_franja[1]

# =====================================================
# FUNCIONES DE UTILIDAD PARA RASA
# =====================================================

def interpretar_frase_ambigua(frase: str) -> str:
    """
    Interpreta frases ambiguas del usuario para determinar preferencias
    """
    frase_lower = frase.lower()
    
    if any(palabra in frase_lower for palabra in ['temprano', 'mañana', 'primera hora']):
        return 'temprano'
    elif any(palabra in frase_lower for palabra in ['tarde', 'después', 'último']):
        return 'tarde'
    elif any(palabra in frase_lower for palabra in ['menos gente', 'tranquilo', 'vacío']):
        return 'menor_ocupacion'
    elif any(palabra in frase_lower for palabra in ['rápido', 'urgente', 'pronto']):
        return 'menor_espera'
    else:
        return 'general'

def generar_respuesta_recomendacion(fecha: datetime.date, frase_usuario: str) -> str:
    """
    Genera respuesta personalizada basada en lógica difusa
    """
    preferencia = interpretar_frase_ambigua(frase_usuario)
    
    if preferencia == 'menor_ocupacion':
        analisis = analizar_disponibilidad_dia(fecha)
        franja_menos_ocupada = min(analisis.items(), key=lambda x: x[1]['ocupacion'])
        nombre_franja, datos = franja_menos_ocupada
        
        return f"Para menor ocupación te recomiendo {nombre_franja} ({datos['rango']}). " \
               f"Ocupación estimada: {datos['ocupacion']:.0f}%. " \
               f"Horarios disponibles: {', '.join(datos['horarios_sugeridos'])}"
    
    elif preferencia == 'menor_espera':
        analisis = analizar_disponibilidad_dia(fecha)
        franja_menor_espera = min(analisis.items(), key=lambda x: x[1]['espera_estimada'])
        nombre_franja, datos = franja_menor_espera
        
        return f"Para menor tiempo de espera te recomiendo {nombre_franja} ({datos['rango']}). " \
               f"Espera estimada: {datos['espera_estimada']:.0f} minutos. " \
               f"Horarios disponibles: {', '.join(datos['horarios_sugeridos'])}"
    
    else:
        mejor_franja, datos = obtener_mejor_recomendacion(fecha, preferencia)
        
        return f"Según el análisis, te recomiendo {mejor_franja} ({datos['rango']}). " \
               f"Puntuación de recomendación: {datos['recomendacion']:.0f}/100. " \
               f"Horarios sugeridos: {', '.join(datos['horarios_sugeridos'])}"

# =====================================================
# FUNCIONES DE TESTING Y DEBUG
# =====================================================

def test_motor_difuso():
    """Función para probar el motor difuso"""
    print("=== Test del Motor Difuso ===")
    
    casos_test = [
        (20, 8, 8),   # Ocupación baja, urgencia alta, hora temprana
        (80, 3, 13),  # Ocupación alta, urgencia baja, mediodía
        (50, 5, 15),  # Ocupación media, urgencia media, tarde
    ]
    
    for ocupacion_val, urgencia_val, hora_val in casos_test:
        espera_resultado = calcular_espera(ocupacion_val, urgencia_val, hora_val)
        rec_resultado = evaluar_recomendacion(ocupacion_val, hora_val)
        
        print(f"Ocupación: {ocupacion_val}%, Urgencia: {urgencia_val}, Hora: {hora_val}:00")
        print(f"  -> Espera: {espera_resultado} min, Recomendación: {rec_resultado}/100")
        print()

if __name__ == "__main__":
    test_motor_difuso()