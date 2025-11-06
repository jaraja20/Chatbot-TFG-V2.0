"""
Clasificador Híbrido con Lógica Difusa
Combina: Contexto + Regex + LLM Fine-tuned + Razonamiento Difuso
"""

import logging
from typing import Tuple, Dict
import requests
from razonamiento_difuso import clasificar_con_logica_difusa, agregar_scores_difusos

logger = logging.getLogger(__name__)

class ClasificadorHibrido:
    """
    Clasificador que integra múltiples fuentes con lógica difusa
    """
    
    def __init__(self, llm_endpoint: str = "http://localhost:1234/v1/chat/completions"):
        self.llm_endpoint = llm_endpoint
        self.use_finetuned = False  # Flag para usar modelo fine-tuned cuando esté listo
        self.finetuned_model_path = "./tinyllama-intent-classifier-final"
        logger.info("🔥 ClasificadorHibrido inicializado")
    
    def activar_modelo_finetuned(self):
        """
        Activa el uso del modelo fine-tuned si está disponible.
        NOTA: Requiere que LM Studio apunte al modelo fine-tuned.
        """
        self.use_finetuned = True
        logger.info(f"✅ Modelo fine-tuned activado: {self.finetuned_model_path}")
    
    def clasificar_hibrido(self,
                          mensaje: str,
                          score_contexto: float,
                          intent_contexto: str,
                          score_regex: float,
                          intent_regex: str,
                          score_llm: float,
                          intent_llm: str) -> Tuple[str, float, Dict]:
        """
        Clasificación híbrida con agregación difusa.
        
        Args:
            mensaje: Texto del usuario
            score_contexto: Confianza de detección contextual
            intent_contexto: Intent detectado por contexto
            score_regex: Confianza de patrones regex
            intent_regex: Intent detectado por regex
            score_llm: Confianza del LLM
            intent_llm: Intent detectado por LLM
        
        Returns:
            (intent_final, confianza_final, detalles)
        """
        
        # PASO 1: Clasificación difusa
        intent_fuzzy, score_fuzzy = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        
        logger.info(f"📊 Scores individuales:")
        logger.info(f"   Contexto: {intent_contexto} ({score_contexto:.2f})")
        logger.info(f"   Regex:    {intent_regex} ({score_regex:.2f})")
        logger.info(f"   LLM:      {intent_llm} ({score_llm:.2f})")
        logger.info(f"   Fuzzy:    {intent_fuzzy} ({score_fuzzy:.2f})")
        
        # PASO 2: Determinar intent ganador por fuente
        # Prioridad: Contexto > Regex > Fuzzy > LLM (LLM como apoyo, no como principal)
        
        candidates = []
        
        # Contexto tiene máxima prioridad
        if score_contexto >= 0.96:
            logger.info("✨ Contexto gana por alta confianza")
            return (intent_contexto, score_contexto, {
                'source': 'contexto',
                'scores': {
                    'contexto': score_contexto,
                    'regex': score_regex,
                    'llm': score_llm,
                    'fuzzy': score_fuzzy
                }
            })
        
        # Regex con alta confianza tiene prioridad sobre LLM
        if score_regex >= 0.90:
            logger.info("✨ Regex gana por alta confianza")
            return (intent_regex, score_regex, {
                'source': 'regex',
                'scores': {
                    'contexto': score_contexto,
                    'regex': score_regex,
                    'llm': score_llm,
                    'fuzzy': score_fuzzy
                }
            })
        
        # Agregar candidatos si superan threshold
        if score_contexto > 0:
            candidates.append(('contexto', intent_contexto, score_contexto))
        if score_regex >= 0.7:
            candidates.append(('regex', intent_regex, score_regex))
        if score_fuzzy >= 0.5:
            candidates.append(('fuzzy', intent_fuzzy, score_fuzzy))
        # LLM con threshold MÁS ALTO para evitar que domine
        if score_llm >= 0.85 and intent_llm != 'nlu_fallback':
            candidates.append(('llm', intent_llm, score_llm))
        
        # PASO 3: Verificar consenso
        intents_count = {}
        for source, intent, score in candidates:
            if intent != 'nlu_fallback':
                intents_count[intent] = intents_count.get(intent, 0) + 1
        
        # Si hay consenso (2+ fuentes acuerdan)
        if intents_count:
            most_common = max(intents_count.items(), key=lambda x: x[1])
            if most_common[1] >= 2:
                # Calcular score agregado para el intent con consenso
                scores_for_intent = [
                    (score if intent == most_common[0] else 0)
                    for _, intent, score in candidates
                ]
                
                # Usar solo scores > 0
                valid_scores = [s for s in scores_for_intent if s > 0]
                if valid_scores:
                    avg_score = sum(valid_scores) / len(valid_scores)
                    logger.info(f"🤝 Consenso detectado: {most_common[0]} ({most_common[1]} fuentes, score={avg_score:.2f})")
                    
                    return (most_common[0], avg_score, {
                        'source': 'consensus',
                        'agreement': most_common[1],
                        'scores': {
                            'contexto': score_contexto,
                            'regex': score_regex,
                            'llm': score_llm,
                            'fuzzy': score_fuzzy
                        }
                    })
        
        # PASO 4: Sin consenso, usar agregación difusa
        # Obtener scores para el intent más común de cada fuente
        
        # Encontrar el intent con mayor score individual
        all_intents = []
        if score_contexto > 0:
            all_intents.append((intent_contexto, score_contexto))
        if score_llm > 0:
            all_intents.append((intent_llm, score_llm))
        if score_fuzzy > 0:
            all_intents.append((intent_fuzzy, score_fuzzy))
        if score_regex > 0:
            all_intents.append((intent_regex, score_regex))
        
        if not all_intents:
            logger.info("❌ Ninguna fuente tiene confianza, fallback")
            return ("nlu_fallback", 0.0, {'source': 'none'})
        
        # Tomar el intent con mayor score individual
        best_intent, best_score = max(all_intents, key=lambda x: x[1])
        
        # Calcular score agregado para ese intent específico
        score_ctx = score_contexto if intent_contexto == best_intent else 0
        score_reg = score_regex if intent_regex == best_intent else 0
        score_lm = score_llm if intent_llm == best_intent else 0
        score_fz = score_fuzzy if intent_fuzzy == best_intent else 0
        
        score_final = agregar_scores_difusos(score_ctx, score_reg, score_lm, score_fz)
        
        logger.info(f"🔀 Agregación difusa: {best_intent} (score final: {score_final:.2f})")
        
        return (best_intent, score_final, {
            'source': 'fuzzy_aggregation',
            'scores': {
                'contexto': score_contexto,
                'regex': score_regex,
                'llm': score_llm,
                'fuzzy': score_fuzzy
            }
        })


# =====================================================
# INSTANCIA GLOBAL
# =====================================================

clasificador_hibrido = ClasificadorHibrido()

# =====================================================
# FUNCIÓN PÚBLICA
# =====================================================

def clasificar_con_fusion_difusa(
    mensaje: str,
    score_contexto: float,
    intent_contexto: str,
    score_regex: float,
    intent_regex: str,
    score_llm: float,
    intent_llm: str
) -> Tuple[str, float, Dict]:
    """
    Wrapper para clasificación híbrida con fusión difusa.
    
    Returns:
        (intent, confianza, detalles)
    """
    return clasificador_hibrido.clasificar_hibrido(
        mensaje,
        score_contexto, intent_contexto,
        score_regex, intent_regex,
        score_llm, intent_llm
    )


if __name__ == "__main__":
    print("🧪 Testing Clasificador Híbrido")
    print("=" * 60)
    
    test_cases = [
        {
            'mensaje': 'quiero agendar un turno',
            'ctx': (0.98, 'agendar_turno'),
            'regex': (0.9, 'agendar_turno'),
            'llm': (0.85, 'agendar_turno'),
        },
        {
            'mensaje': 'cuando hay turnos?',
            'ctx': (0.0, ''),
            'regex': (0.7, 'consultar_disponibilidad'),
            'llm': (0.8, 'consultar_disponibilidad'),
        },
        {
            'mensaje': 'perfecto',
            'ctx': (0.97, 'elegir_horario'),
            'regex': (0.0, ''),
            'llm': (0.3, 'nlu_fallback'),
        },
    ]
    
    for i, caso in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test {i}: {caso['mensaje']}")
        print("-" * 60)
        
        intent, score, detalles = clasificar_con_fusion_difusa(
            caso['mensaje'],
            caso['ctx'][0], caso['ctx'][1],
            caso['regex'][0], caso['regex'][1],
            caso['llm'][0], caso['llm'][1]
        )
        
        print(f"✅ Resultado: {intent} (score: {score:.2f})")
        print(f"   Fuente: {detalles.get('source', 'unknown')}")
        print(f"   Scores: {detalles.get('scores', {})}")
    
    print("\n" + "=" * 60)
    print("✅ Test completado")
