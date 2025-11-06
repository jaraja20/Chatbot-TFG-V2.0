#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Análisis detallado de los 5 casos fallidos del mega test
Para entender patrones comunes y proponer solución estructural
"""

casos_fallidos = {
    'CONV #8': {
        'titulo': 'Consulta y agendamiento juntos',
        'problema': 'Oración compuesta con consulta + intención de agendar',
        'paso_critico': 'Hola, qué horarios tienen para mañana? Necesito sacar turno',
        'esperado': {
            'debe_detectar_fecha': 'mañana',
            'debe_responder': 'horarios disponibles',
            'debe_iniciar': 'flujo de agendamiento'
        },
        'categoria': 'multi_intent'
    },
    
    'CONV #9': {
        'titulo': 'Pregunta sobre requisitos y luego agenda',
        'problema': 'Consulta múltiple (requisitos + demora) seguida de agendamiento',
        'paso_critico_1': 'Qué documentos necesito para renovar mi cédula? Y cuánto demora?',
        'paso_critico_2': 'Ok perfecto, entonces quiero turno para el jueves',
        'esperado': {
            'paso_1': 'Responder requisitos + demora',
            'paso_2': 'Detectar informar_fecha + agendar_turno, extraer jueves'
        },
        'categoria': 'multi_consulta_seguida_agendamiento'
    },
    
    'CONV #11': {
        'titulo': 'Pregunta por mejor día disponible',
        'problema': 'Consulta disponibilidad general seguida de agendamiento',
        'paso_critico_1': 'Qué día tiene más disponibilidad esta semana?',
        'paso_critico_2': 'Perfecto, quiero para ese día a las 9, soy Lucía Benítez',
        'esperado': {
            'paso_1': 'consultar_disponibilidad + responder día con más huecos',
            'paso_2': 'Detectar hora + nombre en oración compuesta'
        },
        'categoria': 'consulta_disponibilidad_seguida_agendamiento'
    },
    
    'CONV #12': {
        'titulo': 'Consulta horarios de atención',
        'problema': 'Consulta horario de oficina seguida de agendamiento con "mediodía"',
        'paso_critico_1': 'Hasta qué hora atienden?',
        'paso_critico_2': 'Ok, quiero turno para mañana al mediodía',
        'esperado': {
            'paso_1': 'Responder horario 07:00-17:00',
            'paso_2': 'Detectar mañana + mediodía (12:00), iniciar agendamiento'
        },
        'categoria': 'consulta_horario_seguida_agendamiento'
    },
    
    'CONV #16': {
        'titulo': 'Conversación muy natural con dudas',
        'problema': 'Flujo natural: saludo → consulta requisitos → consulta costo → decide agendar',
        'paso_critico': 'Ok dale, entonces quiero turno para pasado mañana',
        'esperado': {
            'debe_detectar': 'pasado mañana como fecha',
            'debe_iniciar': 'agendamiento pidiendo nombre'
        },
        'categoria': 'flujo_conversacional_natural'
    }
}

# Análisis de patrones comunes
patrones_comunes = {
    'multi_intent_en_una_oracion': [
        'CONV #8: consulta + agendamiento',
        'CONV #9: requisitos + demora',
        'CONV #11: disponibilidad + confirmar'
    ],
    
    'consulta_seguida_de_agendamiento': [
        'CONV #8: horarios → sacar turno',
        'CONV #9: requisitos → quiero turno',
        'CONV #11: disponibilidad → quiero ese día',
        'CONV #12: horarios → turno mañana',
        'CONV #16: requisitos → costo → turno'
    ],
    
    'extraccion_temporal_compleja': [
        'CONV #8: "mañana" en consulta',
        'CONV #9: "jueves"',
        'CONV #11: "ese día" (referencia contextual)',
        'CONV #12: "mediodía" (hora implícita)',
        'CONV #16: "pasado mañana"'
    ],
    
    'oraciones_compuestas_datos': [
        'CONV #11: hora + nombre juntos',
        'CONV #12: fecha + hora juntos'
    ]
}

# Soluciones propuestas
soluciones = {
    'SOLUCION_1_MULTI_INTENT': {
        'nombre': 'Detector Multi-Intent',
        'descripcion': 'Sistema para detectar múltiples intenciones en una oración',
        'implementacion': '''
        1. Analizar oración con LLM para detectar TODOS los intents presentes
        2. Priorizar según contexto:
           - Si esperamos datos: priorizar informar_*
           - Si no hay contexto: priorizar consultas
           - Si hay "pero/entonces/y": dividir oración
        3. Responder consulta PRIMERO, luego continuar flujo
        ''',
        'ejemplo': '"qué horarios tienen mañana? necesito turno" → [consultar_disponibilidad, agendar_turno]',
        'complejidad': 'MEDIA',
        'impacto': 'ALTO (resuelve CONV #8, 9, 11, 12)'
    },
    
    'SOLUCION_2_EXTRACCION_TEMPORAL_AVANZADA': {
        'nombre': 'Extracción Temporal Inteligente',
        'descripcion': 'Mejorar detección de fechas/horas en contextos complejos',
        'implementacion': '''
        1. Extraer temporales ANTES de clasificar intent
        2. Agregar detección de:
           - "mediodía" → 12:00
           - "ese día" → usar fecha del mensaje anterior
           - "esta semana" → calcular días disponibles
        3. Pasar temporales extraídos al clasificador como contexto
        ''',
        'ejemplo': '"mañana al mediodía" → {fecha: 2025-11-05, hora: 12:00}',
        'complejidad': 'BAJA',
        'impacto': 'MEDIO (resuelve CONV #12, ayuda #8, #9)'
    },
    
    'SOLUCION_3_CONTEXTO_CONVERSACIONAL': {
        'nombre': 'Memoria Conversacional de Corto Plazo',
        'descripcion': 'Mantener últimas consultas para resolver referencias',
        'implementacion': '''
        1. Guardar en contexto:
           - ultimas_consultas = [intent_1, intent_2, intent_3]
           - ultimo_dia_mencionado = None
        2. Si usuario dice "ese día", buscar en último mensaje con fecha
        3. Si dice "entonces quiero turno", saber que viene de consulta
        ''',
        'ejemplo': 'Msg1: "qué día mejor?" → Msg2: "ese día" usa fecha de Msg1',
        'complejidad': 'MEDIA',
        'impacto': 'MEDIO (resuelve CONV #11, ayuda #16)'
    },
    
    'SOLUCION_4_REGEX_ADICIONALES': {
        'nombre': 'Regex Específicas para Casos Edge',
        'descripcion': 'Agregar patrones para palabras problemáticas',
        'implementacion': '''
        1. "mediodía"/"mediodia" → hora = 12:00
        2. "entonces (quiero|necesito) turno" → agendar_turno (0.92)
        3. "hasta qué hora" → consultar_horarios_atencion (nuevo intent?)
        4. "qué día (mejor|más disponible)" → consultar_disponibilidad_semanal
        ''',
        'complejidad': 'BAJA',
        'impacto': 'BAJO (fix específico, no escalable)'
    },
    
    'SOLUCION_5_PIPELINE_ORACIONES_COMPUESTAS': {
        'nombre': 'Pipeline de Procesamiento para Oraciones Complejas',
        'descripcion': 'Sistema de 3 fases para oraciones con múltiple info',
        'implementacion': '''
        FASE 1: Extracción global (actual, funciona bien)
        - Extraer TODAS las entidades: nombre, cedula, fecha, hora, email
        
        FASE 2: Análisis de intents (NUEVO)
        - Detectar TODOS los intents en la oración (no solo el principal)
        - Ordenar por prioridad: contexto > acción > consulta
        
        FASE 3: Ejecución secuencial (NUEVO)
        - Si hay consulta + acción: responder consulta, luego continuar acción
        - Si hay datos: almacenar TODOS, responder según intent principal
        ''',
        'ejemplo': '''
        Input: "qué horarios tienen mañana? necesito turno"
        Fase 1: {fecha: 2025-11-05}
        Fase 2: [consultar_disponibilidad(0.85), agendar_turno(0.80)]
        Fase 3: 
          - Respuesta: "Horarios disponibles: 07:00, 09:00, 11:00..."
          - Contexto: {fecha: 2025-11-05, flujo_activo: agendar_turno}
          - Siguiente: "¿Cuál es tu nombre?"
        ''',
        'complejidad': 'ALTA',
        'impacto': 'MUY ALTO (resuelve TODOS los casos)'
    }
}

# Análisis de impacto por solución
impacto_por_solucion = {
    'SOLUCION_1': {'resuelve': ['CONV #8', 'CONV #9', 'CONV #11', 'CONV #12'], 'mejora_esperada': '+4 (15→19, 95%)'},
    'SOLUCION_2': {'resuelve': ['CONV #12'], 'ayuda': ['CONV #8', 'CONV #9'], 'mejora_esperada': '+1-2 (15→16-17, 80-85%)'},
    'SOLUCION_3': {'resuelve': ['CONV #11'], 'ayuda': ['CONV #16'], 'mejora_esperada': '+1-2 (15→16-17, 80-85%)'},
    'SOLUCION_4': {'resuelve': ['CONV #12'], 'mejora_esperada': '+1 (15→16, 80%)'},
    'SOLUCION_5': {'resuelve': ['CONV #8', 'CONV #9', 'CONV #11', 'CONV #12', 'CONV #16'], 'mejora_esperada': '+5 (15→20, 100%)'}
}

# Recomendación de estrategia
estrategia_recomendada = """
╔════════════════════════════════════════════════════════════════════════════════╗
║                     ESTRATEGIA RECOMENDADA: PIPELINE 3 FASES                   ║
╚════════════════════════════════════════════════════════════════════════════════╝

🎯 OBJETIVO: Alcanzar 20/20 (100%) con arquitectura escalable

📋 PLAN DE IMPLEMENTACIÓN (3 pasos):

┌─ PASO 1: Quick Win - Regex Temporales (30 min) ─────────────────────────────┐
│ • Agregar "mediodía" → 12:00                                                 │
│ • Agregar "pasado mañana" → fecha + 2 días                                   │
│ • Mejora esperada: 15 → 16 (80%)                                             │
│ • Complejidad: BAJA, Riesgo: BAJO                                            │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ PASO 2: Detector Multi-Intent (2-3 horas) ──────────────────────────────────┐
│ MODIFICAR: clasificar_intent_hibrido()                                       │
│                                                                               │
│ 1. ANTES de retornar intent final, analizar si hay múltiples intents:        │
│    if '?' in mensaje and any(palabra in mensaje for palabra                  │
│        in ['turno', 'agendar', 'necesito', 'quiero']):                       │
│        # Detectar consulta + agendamiento                                    │
│        consulta_intent = detectar_consulta(mensaje)                          │
│        accion_intent = detectar_accion(mensaje)                              │
│        return multi_intent_response(consulta_intent, accion_intent, contexto)│
│                                                                               │
│ 2. CREAR: multi_intent_response()                                            │
│    - Responder consulta PRIMERO                                              │
│    - Agregar al final: "¿Quieres agendar turno? ¿Cuál es tu nombre?"        │
│    - Mantener flujo_activo = agendar_turno                                   │
│                                                                               │
│ • Mejora esperada: 16 → 19 (95%)                                             │
│ • Complejidad: MEDIA, Riesgo: BAJO-MEDIO                                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ PASO 3: Memoria Conversacional (1 hora) ────────────────────────────────────┐
│ MODIFICAR: clase ContextoTurno                                               │
│                                                                               │
│ Agregar campos:                                                              │
│   - ultimos_intents = []  # Últimos 3 intents                                │
│   - ultimo_dia_mencionado = None                                             │
│   - ultima_consulta = None                                                   │
│                                                                               │
│ Usar en resolver referencias:                                                │
│   - "ese día" → usar ultimo_dia_mencionado                                   │
│   - "entonces quiero turno" → saber que viene de consulta                    │
│                                                                               │
│ • Mejora esperada: 19 → 20 (100%)                                            │
│ • Complejidad: BAJA, Riesgo: BAJO                                            │
└──────────────────────────────────────────────────────────────────────────────┘

⏱️  TIEMPO TOTAL ESTIMADO: 4-5 horas
🎯 RESULTADO ESPERADO: 20/20 (100%)
🔧 MANTENIBILIDAD: ALTA (estructura clara, fácil de extender)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALTERNATIVA RÁPIDA (si tiempo limitado):
• Solo PASO 1 + PASO 2 → 19/20 (95%)
• Total: 3 horas
• Ya sería excelente resultado

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

print(estrategia_recomendada)

print("\n\n" + "="*80)
print("ANÁLISIS DETALLADO DE CASOS FALLIDOS")
print("="*80)

for conv_id, caso in casos_fallidos.items():
    print(f"\n📌 {conv_id}: {caso['titulo']}")
    print(f"   Categoría: {caso['categoria']}")
    print(f"   Problema: {caso['problema']}")
    
print("\n\n" + "="*80)
print("PATRONES COMUNES IDENTIFICADOS")
print("="*80)

for patron, ejemplos in patrones_comunes.items():
    print(f"\n🔍 {patron}:")
    for ejemplo in ejemplos:
        print(f"   • {ejemplo}")

print("\n\n" + "="*80)
print("SOLUCIONES PROPUESTAS (COMPARACIÓN)")
print("="*80)

for sol_id, solucion in soluciones.items():
    impacto = impacto_por_solucion.get(sol_id.split('_')[1], {})
    print(f"\n{'='*80}")
    print(f"🔧 {solucion['nombre']}")
    print(f"{'='*80}")
    print(f"Descripción: {solucion['descripcion']}")
    print(f"Complejidad: {solucion['complejidad']}")
    print(f"Impacto: {solucion['impacto']}")
    if impacto:
        print(f"Mejora esperada: {impacto.get('mejora_esperada', 'N/A')}")
    print(f"\nImplementación:\n{solucion['implementacion']}")
