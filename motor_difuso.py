# motor_difuso.py
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# === VARIABLES ===
ocupacion = ctrl.Antecedent(np.arange(0, 101, 1), 'ocupacion')  # 0% - 100%
urgencia = ctrl.Antecedent(np.arange(0, 11, 1), 'urgencia')     # escala 0 - 10
espera = ctrl.Consequent(np.arange(0, 61, 1), 'espera')         # 0 - 60 minutos

# === FUNCIONES DE PERTENENCIA ===
ocupacion['baja'] = fuzz.trimf(ocupacion.universe, [0, 0, 40])
ocupacion['media'] = fuzz.trimf(ocupacion.universe, [20, 50, 80])
ocupacion['alta'] = fuzz.trimf(ocupacion.universe, [60, 100, 100])

urgencia['baja'] = fuzz.trimf(urgencia.universe, [0, 0, 4])
urgencia['media'] = fuzz.trimf(urgencia.universe, [3, 5, 7])
urgencia['alta'] = fuzz.trimf(urgencia.universe, [6, 10, 10])

espera['corta'] = fuzz.trimf(espera.universe, [0, 0, 20])
espera['media'] = fuzz.trimf(espera.universe, [15, 30, 45])
espera['larga'] = fuzz.trimf(espera.universe, [40, 60, 60])

# === REGLAS ===
regla1 = ctrl.Rule(ocupacion['baja'] & urgencia['alta'], espera['corta'])
regla2 = ctrl.Rule(ocupacion['media'] & urgencia['baja'], espera['media'])
regla3 = ctrl.Rule(ocupacion['alta'] & urgencia['baja'], espera['larga'])
regla4 = ctrl.Rule(ocupacion['alta'] & urgencia['alta'], espera['media'])
regla5 = ctrl.Rule(ocupacion['media'] & urgencia['media'], espera['media'])
regla6 = ctrl.Rule(ocupacion['baja'] & urgencia['baja'], espera['corta'])

# === SISTEMA ===
sistema_ctrl = ctrl.ControlSystem([regla1, regla2, regla3, regla4, regla5, regla6])
sistema = ctrl.ControlSystemSimulation(sistema_ctrl)

# === FUNCIÓN UTILITARIA ===
def calcular_espera(ocupacion_valor, urgencia_valor):
    sistema_sim = ctrl.ControlSystemSimulation(sistema_ctrl)
    sistema_sim.input['ocupacion'] = ocupacion_valor
    sistema_sim.input['urgencia'] = urgencia_valor
    sistema_sim.compute()
    return round(sistema_sim.output['espera'], 1)  # 1 decimal


