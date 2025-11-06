"""
Sistema de Decisión Mejorado - Prioriza Fuzzy sobre LLM
Reemplazar en orquestador_inteligente.py después de línea 825
"""

def decidir_intent_con_logica_difusa(confianza_fuzzy, intent_fuzzy, 
                                     confianza_patron, intent_patron,
                                     confianza_llm, intent_llm):
    """
    Sistema de decisión que prioriza lógica difusa sobre LLM.
    
    Prioridad:
    1. Fuzzy + Regex en consenso (>65% y coinciden)
    2. Fuzzy con buena confianza (>60%)
    3. Regex con alta confianza (>85%)
    4. Fuzzy + Regex coinciden (aunque baja confianza)
    5. LLM con alta confianza (>80%)
    6. Regex razonable (>70%)
    7. Fuzzy medio (>45%) sobre LLM dudoso
    8. Mejor score general
    """
    
    # 1. Fuzzy + Regex en consenso → MUY CONFIABLE
    if confianza_fuzzy > 0.65 and intent_fuzzy == intent_patron and confianza_patron > 0.7:
        return intent_fuzzy, max(confianza_fuzzy, confianza_patron), "fuzzy+regex_consenso"
    
    # 2. Fuzzy con buena confianza
    if confianza_fuzzy > 0.60:
        return intent_fuzzy, confianza_fuzzy, "fuzzy_alta"
    
    # 3. Regex con alta confianza
    if confianza_patron > 0.85:
        return intent_patron, confianza_patron, "regex_alta"
    
    # 4. Fuzzy + Regex coinciden (aunque baja confianza)
    if intent_fuzzy == intent_patron and confianza_fuzzy > 0.4 and confianza_patron > 0.5:
        return intent_fuzzy, (confianza_fuzzy + confianza_patron) / 2, "fuzzy+regex_coinciden"
    
    # 5. LLM con alta confianza
    if confianza_llm > 0.80:
        return intent_llm, confianza_llm, "llm_alta"
    
    # 6. Regex razonable
    if confianza_patron > 0.70:
        return intent_patron, confianza_patron, "regex_razonable"
    
    # 7. Fuzzy medio sobre LLM dudoso
    if confianza_fuzzy > 0.45 and confianza_llm < 0.85:
        return intent_fuzzy, confianza_fuzzy, "fuzzy_medio"
    
    # 8. Mejor score general
    mejor = max([
        (confianza_patron, intent_patron, "regex"),
        (confianza_llm, intent_llm, "llm"),
        (confianza_fuzzy, intent_fuzzy, "fuzzy")
    ], key=lambda x: x[0])
    
    return mejor[1], mejor[0], f"mejor_{mejor[2]}"
