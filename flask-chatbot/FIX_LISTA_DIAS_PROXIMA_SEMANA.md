"""
✅ FIX COMPLETADO: Bot muestra lista de días disponibles cuando usuario pregunta por "próxima semana"

═══════════════════════════════════════════════════════════════════════════════
🐛 PROBLEMA REPORTADO
═══════════════════════════════════════════════════════════════════════════════

Usuario: "que otros dias disponibles hay la proxima semana?"
Bot (ANTES): "Te recomiendo el lunes 10 de noviembre. ¿Te sirve ese día?"
              ❌ Solo recomendaba UN día (lunes)

═══════════════════════════════════════════════════════════════════════════════
🔧 SOLUCIÓN IMPLEMENTADA
═══════════════════════════════════════════════════════════════════════════════

Archivo: orquestador_inteligente.py
Líneas modificadas: 1007-1016 (detección), 2143-2166 (lógica de respuesta)

CAMBIO 1: Detección contextual mejorada (líneas 1007-1016)
───────────────────────────────────────────────────────────
Agregado reconocimiento de frases de consulta de disponibilidad:
- "que dias disponibles"
- "qué días disponibles"  
- "que otros dias"
- "cuales son los dias"
- "dame los dias"
- "ver disponibilidad"
- "mostrar disponibilidad"

Cuando detecta estas frases + "próxima semana" → Intent: consultar_disponibilidad (0.96)

CAMBIO 2: Lógica condicional para diferenciar casos (líneas 2143-2166)
───────────────────────────────────────────────────────────────────────
ANTES:
    if proxima_semana and fecha:
        → SIEMPRE recomendar lunes

AHORA:
    frases_consulta_disponibilidad = [
        'que dias disponibles', 'qué días disponibles', 'que otros dias',
        'cuales son los dias', 'dame los dias', 'ver disponibilidad',
        'mostrar disponibilidad', 'hay disponibilidad'
    ]
    pregunta_por_lista = any(frase in mensaje_lower for frase in frases_consulta_disponibilidad)
    
    if proxima_semana and fecha and not pregunta_por_lista:
        → Recomendar lunes (caso de solicitud simple)
    else:
        → Dejar que consultar_disponibilidad muestre la lista completa

═══════════════════════════════════════════════════════════════════════════════
✅ RESULTADO
═══════════════════════════════════════════════════════════════════════════════

CASO 1: "quiero turno para proxima semana"
Bot: "Te recomiendo el lunes 10 de noviembre. ¿Te sirve ese día?"
     ✅ Recomienda día específico (comportamiento deseado)

CASO 2: "que otros dias disponibles hay la proxima semana?"
Bot: 📅 **Disponibilidad para la próxima semana:**

     ✅ **Lunes 10/11**: 17 horarios disponibles
     ✅ **Martes 11/11**: 17 horarios disponibles
     ✅ **Miércoles 12/11**: 17 horarios disponibles
     ✅ **Jueves 13/11**: 17 horarios disponibles
     ✅ **Viernes 14/11**: 17 horarios disponibles

     ¿Para qué día prefieres agendar?
     
     ✅ Muestra lista completa (comportamiento solicitado)

═══════════════════════════════════════════════════════════════════════════════
🧪 VALIDACIÓN
═══════════════════════════════════════════════════════════════════════════════

Test ejecutado: test_disponibilidad_proxima_semana.py
Resultado: ✅ CASO 2 PASÓ - Bot muestra lista completa de 5 días

Logs de ejecución confirman:
1. ✅ Detecta intent: consultar_disponibilidad (0.96)
2. ✅ NO ejecuta recomendación de lunes
3. ✅ Muestra disponibilidad de cada día (Lunes-Viernes)
4. ✅ Pregunta qué día prefiere el usuario

═══════════════════════════════════════════════════════════════════════════════
📝 PRÓXIMOS PASOS
═══════════════════════════════════════════════════════════════════════════════

⚠️ IMPORTANTE: Para que este fix funcione en producción:

1. **Reiniciar servidor Flask**:
   cd "c:\\tfg funcional\\Chatbot-TFG-V2.0\\flask-chatbot"
   python app.py

2. **Probar en frontend**:
   Usuario: "que otros dias disponibles hay la proxima semana?"
   Resultado esperado: Lista completa de Lunes a Viernes

3. **Verificar también variaciones**:
   - "dame los dias disponibles de la proxima semana"
   - "cuales son los dias de la proxima semana?"
   - "mostrar disponibilidad para la proxima semana"
   
═══════════════════════════════════════════════════════════════════════════════
"""

print(__doc__)
