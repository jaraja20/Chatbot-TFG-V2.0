"""
Script para reemplazar lógica de fusión por priorización fuzzy
Maneja encoding correctamente
"""
import sys

# Leer archivo original
with open(r"c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot\orquestador_inteligente.py", 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Nueva lógica (líneas 827-849 aproximadamente)
nueva_logica = '''        # 5. DECISION CON PRIORIZACION FUZZY: Fuzzy > Regex > LLM
        logger.info(f"\\nDECISION CON PRIORIZACION FUZZY:")
        logger.info(f"   Contexto: {intent_contexto or 'N/A'} ({score_contexto:.2f})")
        logger.info(f"   Regex:    {intent_patron} ({confianza_patron:.2f})")
        logger.info(f"   LLM:      {intent_llm} ({confianza_llm:.2f})")
        logger.info(f"   Fuzzy:    {intent_fuzzy} ({confianza_fuzzy:.2f})")
        
        # Prioridad 1: Fuzzy + Regex en consenso
        if confianza_fuzzy > 0.65 and intent_fuzzy == intent_patron and confianza_patron > 0.7:
            intent_final = intent_fuzzy
            confianza_final = max(confianza_fuzzy, confianza_patron)
            fuente = "fuzzy+regex_consenso"
        
        # Prioridad 2: Fuzzy con buena confianza
        elif confianza_fuzzy > 0.60:
            intent_final = intent_fuzzy
            confianza_final = confianza_fuzzy
            fuente = "fuzzy_alta"
        
        # Prioridad 3: Regex con alta confianza
        elif confianza_patron > 0.85:
            intent_final = intent_patron
            confianza_final = confianza_patron
            fuente = "regex_alta"
        
        # Prioridad 4: Fuzzy + Regex coinciden (baja confianza pero consenso)
        elif intent_fuzzy == intent_patron and confianza_fuzzy > 0.4 and confianza_patron > 0.5:
            intent_final = intent_fuzzy
            confianza_final = (confianza_fuzzy + confianza_patron) / 2
            fuente = "fuzzy+regex_coinciden"
        
        # Prioridad 5: LLM con alta confianza
        elif confianza_llm > 0.80:
            intent_final = intent_llm
            confianza_final = confianza_llm
            fuente = "llm_alta"
        
        # Prioridad 6: Regex razonable
        elif confianza_patron > 0.70:
            intent_final = intent_patron
            confianza_final = confianza_patron
            fuente = "regex_razonable"
        
        # Prioridad 7: Fuzzy medio sobre LLM dudoso
        elif confianza_fuzzy > 0.45 and confianza_llm < 0.85:
            intent_final = intent_fuzzy
            confianza_final = confianza_fuzzy
            fuente = "fuzzy_medio"
        
        # Prioridad 8: Mejor score general
        else:
            mejor = max([
                (confianza_patron, intent_patron, "regex"),
                (confianza_llm, intent_llm, "llm"),
                (confianza_fuzzy, intent_fuzzy, "fuzzy")
            ], key=lambda x: x[0])
            intent_final = mejor[1]
            confianza_final = mejor[0]
            fuente = f"mejor_{mejor[2]}"
        
        logger.info(f"RESULTADO FINAL: {intent_final} ({confianza_final:.2f}) [fuente: {fuente}]")
'''

# Reemplazar líneas 826-841 (índices 826:842 en 0-based)
# La sección antigua va de "# 5. FUSIÓN DIFUSA" hasta "logger.info(f'✨ RESULTADO FINAL'"
nueva_lines = lines[:826] + [nueva_logica + '\n'] + lines[842:]

# Guardar archivo modificado
with open(r"c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot\orquestador_inteligente.py", 'w', encoding='utf-8') as f:
    f.writelines(nueva_lines)

print("✅ Reemplazo exitoso")
print(f"   - Líneas antes: {len(lines)}")
print(f"   - Líneas después: {len(nueva_lines)}")
print(f"   - Líneas reemplazadas: 826-841 (16 líneas por ~63 líneas)")
