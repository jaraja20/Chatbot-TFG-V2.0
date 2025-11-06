"""
Motor de Razonamiento Difuso para Clasificación de Intents
Implementa lógica difusa para interpretar ambigüedad en consultas
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# =====================================================
# FUNCIONES DE PERTENENCIA DIFUSAS
# =====================================================

class FuzzyMembershipFunctions:
    """
    Define funciones de pertenencia difusas para cada intent.
    Cada palabra clave tiene un grado de pertenencia (0-1) al intent.
    """
    
    @staticmethod
    def triangular(x: float, a: float, b: float, c: float) -> float:
        """Función triangular: sube de a a b, baja de b a c"""
        if x <= a or x >= c:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        else:  # b < x < c
            return (c - x) / (c - b)
    
    @staticmethod
    def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
        """Función trapezoidal: sube de a a b, plana b-c, baja c a d"""
        if x <= a or x >= d:
            return 0.0
        elif a < x <= b:
            return (x - a) / (b - a)
        elif b < x <= c:
            return 1.0
        else:  # c < x < d
            return (d - x) / (d - a)

# =====================================================
# CONJUNTOS DIFUSOS POR INTENT
# =====================================================

FUZZY_KEYWORDS = {
    'agendar_turno': {
        'alta': ['quiero', 'necesito', 'kiero', 'nesecito', 'marcar', 'agendar', 'sacar', 'reservar', 'turno', 'cita'],
        'media': ['para', 'dame', 'porfavor', 'porfa', 'hora'],
        'baja': ['podria', 'me gustaria', 'quisiera', 'che', 'vieja', 'bo', 'amigo']
    },
    
    'consultar_disponibilidad': {
        'alta': ['cuando', 'cuándo', 'que dia', 'que hora', 'disponible', 'horarios', 'turnos', 'hay', 'tienen', 'hueco', 'libre'],
        'media': ['puedo', 'para', 'hoy', 'mañana', 'tarde', 'temprano', 'intermedio', 'medio'],
        'baja': ['dia', 'semana', 'mejor', 'recomiendas']
    },
    
    'consultar_requisitos': {
        'alta': ['que documentos', 'requisitos', 'papeles', 'que necesito', 'que tengo que', 'documentos'],
        'media': ['llevar', 'presentar', 'traer', 'necesito traer'],
        'baja': ['para', 'sacar', 'tramite', 'primera vez']
    },
    
    'consultar_costo': {
        'alta': ['cuanto', 'cuánto', 'costo', 'precio', 'cuanto vale', 'bale', 'cuesta'],
        'media': ['sale', 'pagar', 'cobran', 'gratis', 'gratuito'],
        'baja': ['hay que', 'tengo que', 'sacar']
    },
    
    'consultar_ubicacion': {
        'alta': ['donde', 'dónde', 'ubicacion', 'ubicación', 'direccion', 'dirección', 'como llego', 'contacto', 'telefono', 'teléfono', 'numero', 'número'],
        'media': ['quedan', 'estan', 'están', 'llamar', 'puedo llamar', 'lejos', 'cerca', 'llegar'],
        'baja': ['oficina', 'lugar', 'hay', 'vivo']
    },
    
    'consultar_tramites': {
        'alta': ['tramites', 'trámites', 'servicios', 'que tramites', 'que servicios'],
        'media': ['hacen', 'ofrecen', 'pueden hacer', 'puedo hacer'],
        'baja': ['ahi', 'ahí', 'oficina']
    },
    
    'elegir_horario': {
        'alta': ['las', 'a las', 'para las', 'prefiero', 'hora'],
        'media': ['horario', 'cambiar', 'mejor para'],
        'baja': ['mejor', 'esa', 'ese']
    },
    
    'negacion': {
        'alta': ['no', 'no me sirve', 'no puedo', 'no quiero', 'mejor otro', 'cambiar'],
        'media': ['esta mal', 'está mal', 'no es', 'no me llamo'],
        'baja': ['incorrecto', 'erroneo', 'equivocado']
    },
    
    'cancelar': {
        'alta': ['cancelar', 'cancelo', 'anular', 'cancelarlo'],
        'media': ['no quiero', 'mejor no', 'dejarlo'],
        'baja': ['olvidar', 'dejar']
    },
    
    'affirm': {
        'alta': ['si', 'sí', 'confirmo', 'acepto', 'ok', 'vale', 'afirmativo', 'correcto', 'exacto', 'perfecto'],
        'media': ['esta bien', 'está bien', 'de acuerdo', 'claro', 'tambien', 'también'],
        'baja': ['bien', 'bueno']
    },
    
    'frase_ambigua': {
        'alta': ['temprano', 'lo antes posible', 'el mejor', 'el que sea', 
                 'cual seria', 'cualquiera', 'lo que tengan',
                 'urgente', 'apurado', 'apurada', 'rapido', 'rápido',
                 'necesito ya', 'ahora mismo', 'cuanto antes', 'estoy apurado',
                 'cuanto antes mejor', 'lo mas pronto', 'lo más pronto',
                 'turno rapido', 'turno rápido', 'turno urgente', 'cita urgente'],
        'media': ['cual sea', 'da igual', 'lo que sea', 'ya', 'pronto', 'porfavor', 'mejor'],
        'baja': ['para', 'ahora']
    },
}

# =====================================================
# PESOS DE PERTENENCIA
# =====================================================

FUZZY_WEIGHTS = {
    'alta': 1.0,
    'media': 0.6,
    'baja': 0.3
}

# =====================================================
# RAZONADOR DIFUSO
# =====================================================

class FuzzyIntentReasoner:
    """
    Clasificador de intents usando lógica difusa
    """
    
    def __init__(self):
        self.keywords = FUZZY_KEYWORDS
        self.weights = FUZZY_WEIGHTS
        logger.info("🌟 FuzzyIntentReasoner inicializado")
    
    def calculate_fuzzy_membership(self, mensaje: str, intent: str) -> float:
        """
        Calcula el grado de pertenencia difuso de un mensaje a un intent.
        
        Returns:
            float: Score difuso entre 0 y 1
        """
        mensaje_lower = mensaje.lower()
        palabras_mensaje = set(mensaje_lower.split())
        
        if intent not in self.keywords:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for nivel, keywords in self.keywords[intent].items():
            peso = self.weights[nivel]
            
            for keyword in keywords:
                # Buscar keyword en mensaje (puede ser parte de palabra o frase)
                if keyword in mensaje_lower:
                    # NUEVO: Dar doble peso a frases multi-palabra (bigramas/trigramas)
                    # Esto hace que "turno rapido" gane sobre "necesito" individual
                    multiplicador = 2.0 if ' ' in keyword else 1.0
                    total_score += peso * multiplicador
                    total_weight += peso * multiplicador
        
        # Normalizar por el número de keywords encontradas
        if total_weight > 0:
            normalized_score = min(total_score / (total_weight + 1), 1.0)
        else:
            normalized_score = 0.0
        
        return normalized_score
    
    def calculate_all_memberships(self, mensaje: str) -> Dict[str, float]:
        """
        Calcula membresías difusas para todos los intents.
        
        Returns:
            Dict con intent: score
        """
        memberships = {}
        
        for intent in self.keywords.keys():
            score = self.calculate_fuzzy_membership(mensaje, intent)
            if score > 0:
                memberships[intent] = score
        
        return memberships
    
    def classify_with_fuzzy_logic(self, mensaje: str, threshold: float = 0.3) -> Tuple[str, float]:
        """
        Clasifica mensaje usando lógica difusa.
        
        Args:
            mensaje: Texto a clasificar
            threshold: Umbral mínimo de confianza
        
        Returns:
            (intent, confianza)
        """
        memberships = self.calculate_all_memberships(mensaje)
        
        if not memberships:
            return ("nlu_fallback", 0.0)
        
        # Obtener intent con mayor membresía
        best_intent = max(memberships.items(), key=lambda x: x[1])
        
        if best_intent[1] >= threshold:
            logger.info(f"🌟 Fuzzy clasificó: {best_intent[0]} (score: {best_intent[1]:.2f})")
            return best_intent
        else:
            return ("nlu_fallback", best_intent[1])

# =====================================================
# AGREGADOR DE SCORES DIFUSOS
# =====================================================

class FuzzyScoreAggregator:
    """
    Agrega scores de diferentes fuentes (contexto, regex, LLM, fuzzy)
    usando operadores difusos.
    """
    
    @staticmethod
    def fuzzy_and(scores: List[float]) -> float:
        """Operador AND difuso (mínimo)"""
        return min(scores) if scores else 0.0
    
    @staticmethod
    def fuzzy_or(scores: List[float]) -> float:
        """Operador OR difuso (máximo)"""
        return max(scores) if scores else 0.0
    
    @staticmethod
    def fuzzy_weighted_average(scores: List[Tuple[float, float]]) -> float:
        """
        Promedio ponderado difuso.
        
        Args:
            scores: Lista de (score, peso)
        
        Returns:
            Score combinado
        """
        if not scores:
            return 0.0
        
        total_score = sum(s * w for s, w in scores)
        total_weight = sum(w for _, w in scores)
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def aggregate_classification(self, 
                                 contexto_score: float,
                                 regex_score: float,
                                 llm_score: float,
                                 fuzzy_score: float) -> float:
        """
        Agrega scores de diferentes clasificadores.
        
        Pesos:
        - Contexto: 0.35 (más importante, datos ya confirmados)
        - LLM: 0.30 (interpretación inteligente)
        - Fuzzy: 0.25 (razonamiento difuso)
        - Regex: 0.10 (patrones exactos pero rígidos)
        """
        scores_with_weights = [
            (contexto_score, 0.35),
            (llm_score, 0.30),
            (fuzzy_score, 0.25),
            (regex_score, 0.10)
        ]
        
        # Filtrar scores no válidos (0.0 significa no aplicado)
        valid_scores = [(s, w) for s, w in scores_with_weights if s > 0]
        
        if not valid_scores:
            return 0.0
        
        final_score = self.fuzzy_weighted_average(valid_scores)
        
        logger.info(f"🔀 Agregación difusa: contexto={contexto_score:.2f}, llm={llm_score:.2f}, "
                   f"fuzzy={fuzzy_score:.2f}, regex={regex_score:.2f} → final={final_score:.2f}")
        
        return final_score

# =====================================================
# INSTANCIA GLOBAL
# =====================================================

fuzzy_reasoner = FuzzyIntentReasoner()
score_aggregator = FuzzyScoreAggregator()

# =====================================================
# FUNCIONES PÚBLICAS
# =====================================================

def clasificar_con_logica_difusa(mensaje: str, threshold: float = 0.3) -> Tuple[str, float]:
    """
    Clasifica mensaje usando razonamiento difuso.
    
    Returns:
        (intent, confianza_difusa)
    """
    return fuzzy_reasoner.classify_with_fuzzy_logic(mensaje, threshold)

def agregar_scores_difusos(contexto: float, regex: float, llm: float, fuzzy: float) -> float:
    """
    Agrega scores de diferentes clasificadores usando lógica difusa.
    
    Returns:
        Score final combinado
    """
    return score_aggregator.aggregate_classification(contexto, regex, llm, fuzzy)

def obtener_membresias_difusas(mensaje: str) -> Dict[str, float]:
    """
    Obtiene todas las membresías difusas para debugging/logging.
    
    Returns:
        Dict con intent: score difuso
    """
    return fuzzy_reasoner.calculate_all_memberships(mensaje)

if __name__ == "__main__":
    # Test del razonador difuso
    print("🧪 Testing Fuzzy Intent Reasoner")
    print("=" * 60)
    
    test_cases = [
        "quiero agendar un turno",
        "cuando hay turnos disponibles?",
        "que documentos necesito?",
        "cuanto cuesta?",
        "donde quedan?",
        "para las 9",
        "si confirmo",
        "no quiero",
    ]
    
    for mensaje in test_cases:
        intent, score = clasificar_con_logica_difusa(mensaje)
        print(f"\n📝 '{mensaje}'")
        print(f"   → {intent} (score: {score:.2f})")
        
        # Mostrar todas las membresías
        memberships = obtener_membresias_difusas(mensaje)
        print(f"   Membresías: {memberships}")
    
    print("\n" + "=" * 60)
    print("✅ Test completado")
