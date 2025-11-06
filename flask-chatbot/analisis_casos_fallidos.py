"""
Análisis de casos fallidos del mega test para mejorar motor difuso
Objetivo: Extraer keywords que faltan y agregarlas al motor fuzzy
"""

casos_fallidos = {
    # CASO 1: "cuanto bale sacar la cedula?"
    # Esperado: consultar_costo
    # Detectado: informar_nombre (❌)
    # Análisis: Tiene "cuanto" + "bale" (vale mal escrito) → COSTO
    'consultar_costo': {
        'alta': ['cuanto', 'cuánto', 'bale', 'vale', 'cuesta', 'precio', 'costo'],
        'media': ['sacar', 'pagar', 'tengo que pagar'],
        'baja': ['cedula', 'cédula']
    },
    
    # CASO 2: "documentos"
    # Esperado: consultar_requisitos
    # Detectado: informar_nombre (❌)
    # Análisis: Palabra sola "documentos" → REQUISITOS
    'consultar_requisitos': {
        'alta': ['documentos', 'requisitos', 'papeles', 'que necesito', 'que tengo que'],
        'media': ['llevar', 'traer', 'presentar'],
        'baja': ['para', 'sacar']
    },
    
    # CASO 3: "buenas, para cuando hay hueco?"
    # Esperado: consultar_disponibilidad
    # Detectado: consultar_costo (❌)
    # Análisis: "cuando" + "hueco" → DISPONIBILIDAD
    'consultar_disponibilidad': {
        'alta': ['cuando', 'cuándo', 'hueco', 'hay', 'tienen', 'horarios', 'disponibilidad'],
        'media': ['para', 'puedo', 'libre'],
        'baja': ['dia', 'día']
    },
    
    # CASO 4: "vieja, necesito sacar turno urgente"
    # Esperado: agendar_turno
    # Detectado: consultar_disponibilidad (❌)
    # Análisis: "necesito" + "sacar" + "turno" → AGENDAR
    'agendar_turno': {
        'alta': ['necesito', 'quiero', 'kiero', 'sacar', 'agendar', 'turno', 'urgente'],
        'media': ['vieja', 'che', 'bo', 'amigo'],  # Coloquialismos paraguayos
        'baja': ['para', 'un', 'una']
    },
    
    # CASO 5: "necesito agendar un turno pero no se que documentos llevar ni cuanto cuesta"
    # Esperado: agendar_turno (primera pregunta tiene prioridad)
    # Detectado: consultar_costo (❌)
    # Análisis: Múltiples intents → Priorizar PRIMER intent mencionado
    # Este es un caso especial de priorización
    
    # CASO 6: "hola buen día quisiera saber como hago para sacar la cédula por primera vez y que necesito traer"
    # Esperado: consultar_requisitos (lo más específico)
    # Detectado: informar_cedula (❌)
    # Análisis: "que necesito" + "traer" → REQUISITOS
    
    # CASO 7: "dame un dia intermedio de la semana"
    # Esperado: consultar_disponibilidad
    # Detectado: consultar_costo (❌)
    # Análisis: "dia" + "intermedio" + "semana" → DISPONIBILIDAD
    'consultar_disponibilidad_especial': {
        'alta': ['intermedio', 'medio', 'dia libre', 'día libre'],
        'media': ['semana', 'mejor', 'recomiendas'],
        'baja': ['dame', 'un', 'el']
    },
    
    # CASO 8-10: Negaciones
    # "no, esa hora no me sirve"
    # "no puedo a esa hora"
    # "mejor otro día"
    'negacion': {
        'alta': ['no', 'no me sirve', 'no puedo', 'no quiero'],
        'media': ['esa hora', 'ese dia', 'mejor otro', 'cambiar'],
        'baja': ['prefiero', 'otro']
    },
    
    # CASO 11-12: Correcciones
    # "no me llamo así"
    # "no ese no es mi email"
    'negacion_correccion': {
        'alta': ['no me llamo', 'no es mi', 'esta mal', 'está mal'],
        'media': ['incorrecto', 'equivocado', 'erroneo'],
        'baja': ['asi', 'así']
    },
    
    # CASO 13: "cancelar"
    'cancelar': {
        'alta': ['cancelar', 'cancelo', 'anular'],
        'media': ['no quiero', 'mejor no'],
        'baja': ['dejar', 'olvidar']
    },
    
    # CASO 14: "tienen temprano?"
    # Esperado: frase_ambigua
    # Detectado: consultar_costo (❌)
    'frase_ambigua': {
        'alta': ['temprano', 'lo antes posible', 'el mejor', 'el que sea'],
        'media': ['cual seria', 'cualquiera', 'lo que tengan'],
        'baja': ['tienen', 'hay']
    }
}

# Palabras de ALTO nivel que son MUY específicas de cada intent
# Estas deben tener peso MÁXIMO (1.0)
keywords_especificos = {
    'consultar_costo': {
        'alta': ['cuanto', 'cuánto', 'cuesta', 'precio', 'costo', 'vale', 'bale', 'pagar', 'cobran'],
    },
    'consultar_requisitos': {
        'alta': ['requisitos', 'documentos', 'papeles', 'que necesito', 'que tengo que', 'llevar', 'traer'],
    },
    'consultar_disponibilidad': {
        'alta': ['cuando', 'cuándo', 'disponible', 'horarios', 'hay', 'tienen', 'libre', 'hueco'],
    },
    'agendar_turno': {
        'alta': ['quiero', 'necesito', 'sacar', 'agendar', 'reservar', 'turno', 'cita', 'urgente'],
    },
    'consultar_ubicacion': {
        'alta': ['donde', 'dónde', 'ubicacion', 'ubicación', 'direccion', 'dirección', 'como llego'],
    },
    'negacion': {
        'alta': ['no', 'no me sirve', 'no puedo', 'mejor otro', 'cambiar'],
    },
    'cancelar': {
        'alta': ['cancelar', 'cancelo', 'anular'],
    }
}

# Análisis de casos que funcionaron BIEN
casos_exitosos_patron = {
    # Estos son ejemplos de lo que SÍ funciona
    'agendar_turno': [
        'quiero agendar un turno',
        'necesito para mañana',
        'dame uno',
        'turno',
        'porfa urgente!!!'
    ],
    'consultar_disponibilidad': [
        'cuando es posible?',
        'tienen algo libre?',
        'para hoy',
        'hoy',
        'que dia me recomendas?'
    ],
    'consultar_requisitos': [
        'k documentos nececito llevar',
        'para sacar cedula que necesita?',
        'requisitos'
    ],
    'consultar_costo': [
        'cuanto es costo?',
        'costo'
    ],
    'consultar_ubicacion': [
        'donde keda la oficina?',
        'ubicacion'
    ]
}

print("=" * 80)
print("ANÁLISIS DE CASOS FALLIDOS - MEGA TEST")
print("=" * 80)

print("\n📊 Resumen:")
print(f"   - Total casos probados: 67")
print(f"   - Casos exitosos: 53 (79.1%)")
print(f"   - Casos fallidos: 14 (20.9%)")

print("\n🔍 Patrones identificados en casos fallidos:")
print("\n1. PALABRAS ESPECÍFICAS FALTANTES:")
print("   - 'bale' (vale mal escrito) → consultar_costo")
print("   - 'hueco' → consultar_disponibilidad")
print("   - 'intermedio' → consultar_disponibilidad")
print("   - 'vieja/che/bo' (coloquialismos) → contextual")

print("\n2. NEGACIONES MAL DETECTADAS:")
print("   - 'no me sirve' → negacion (no consultar_costo)")
print("   - 'mejor otro día' → negacion (no informar_nombre)")
print("   - 'cancelar' → cancelar (no error)")

print("\n3. PRIORIZACIÓN EN CONSULTAS MÚLTIPLES:")
print("   - 'necesito turno pero no sé documentos' → agendar_turno (primera intent)")
print("   - Actualmente: Última intent detectada gana ❌")
print("   - Debería: Primera intent (más importante) gana ✅")

print("\n4. PALABRAS AISLADAS:")
print("   - 'documentos' → consultar_requisitos (no informar_nombre)")
print("   - 'cancelar' → cancelar (no error)")
print("   - Problema: LLM confunde palabra sola con nombre")

print("\n💡 Soluciones propuestas:")
print("\n   A. Expandir keywords fuzzy con casos fallidos")
print("   B. Agregar detector de prioridad para múltiples intents")
print("   C. Mejorar detección de negaciones con contexto")
print("   D. Reducir peso del LLM cuando fuzzy+regex coinciden")

print("\n" + "=" * 80)
print("✅ Análisis completado")
print("=" * 80)
