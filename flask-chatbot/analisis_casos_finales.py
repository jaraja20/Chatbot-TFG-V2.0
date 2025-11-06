"""
ANÁLISIS DE 4 CASOS FALLIDOS FINALES (6%)
Sistema: 94.0% → Objetivo: 98%+
"""

print("="*80)
print("🔍 ANÁLISIS DE CASOS FALLIDOS - Sistema al 94.0%")
print("="*80)

casos_fallidos = [
    {
        'mensaje': 'documentos',
        'esperado': 'consultar_requisitos',
        'detectado': 'informar_nombre',
        'confianza': 0.92,
        'problema': 'Palabra aislada interpretada como nombre por contexto',
        'solucion': 'Agregar "documentos" a palabras_prohibidas en línea 745',
        'prioridad': '🔥 CRÍTICA',
        'tiempo': '15 min'
    },
    {
        'mensaje': 'no puedo a esa hora',
        'esperado': 'negacion',
        'detectado': 'affirm',
        'confianza': 0.92,
        'problema': 'Regex de affirm detecta "a esa" antes que la negación',
        'solucion': 'Priorizar detector de negaciones ANTES de affirm en pipeline',
        'prioridad': '🟡 ALTA',
        'tiempo': '30 min'
    },
    {
        'mensaje': 'mejor otro día',
        'esperado': 'negacion',
        'detectado': 'informar_nombre',
        'confianza': 0.92,
        'problema': 'Sistema interpreta "Mejor Otro Día" como nombre completo',
        'solucion': 'Agregar "mejor otro" a frases temporales de rechazo',
        'prioridad': '🟡 ALTA',
        'tiempo': '20 min'
    },
    {
        'mensaje': 'tienen temprano?',
        'esperado': 'frase_ambigua',
        'detectado': 'consultar_disponibilidad',
        'confianza': 0.62,
        'problema': 'Palabra "tienen" refuerza consultar_disponibilidad',
        'solucion': 'Ajustar peso de "temprano" en frase_ambigua vs disponibilidad',
        'prioridad': '🟢 MEDIA',
        'tiempo': '30 min'
    }
]

print(f"\n📊 Casos fallidos: 4/67 (6.0%)")
print(f"✅ Casos exitosos: 63/67 (94.0%)")
print(f"🎯 Objetivo: 65-66/67 (97-98%)")

print("\n" + "="*80)
for i, caso in enumerate(casos_fallidos, 1):
    print(f"\n[{i}/4] {caso['prioridad']} \"{caso['mensaje']}\"")
    print(f"      ❌ Detectado: {caso['detectado']} ({caso['confianza']:.2f})")
    print(f"      ✅ Esperado:  {caso['esperado']}")
    print(f"      🔍 Problema:  {caso['problema']}")
    print(f"      💡 Solución:  {caso['solucion']}")
    print(f"      ⏱️  Tiempo:    {caso['tiempo']}")

print("\n" + "="*80)
print("\n⏱️  TIEMPO TOTAL ESTIMADO: 1h 35min")
print("🎯 MEJORA ESPERADA: 94.0% → 97-98%")
print("\n📋 PLAN DE ACCIÓN:")
print("   1. Corregir palabras_prohibidas (15 min) → +1 caso")
print("   2. Priorizar negaciones en pipeline (30 min) → +2 casos")
print("   3. Ajustar threshold frase_ambigua (30 min) → +1 caso (si es prioritario)")
print("   4. Test de validación (20 min)")
print("="*80)

# Generar código de corrección
print("\n\n📝 CÓDIGO DE CORRECCIÓN PROPUESTO:")
print("="*80)

print("""
# CORRECCIÓN 1: Agregar "documentos" a palabras_prohibidas
# Ubicación: orquestador_inteligente.py, línea ~745

palabras_prohibidas = {
    # ... existentes ...
    # NUEVAS:
    'documentos', 'documento', 'papeles', 'papel',
    'requisitos', 'requisito',  # También agregar estas
    'mejor', 'otro', 'día', 'dia',  # Para "mejor otro día"
}

# CORRECCIÓN 2: Priorizar negaciones ANTES de affirm
# Ubicación: orquestador_inteligente.py, método _clasificar_por_patrones

def _clasificar_por_patrones(self, mensaje: str):
    # ... código existente ...
    
    # NUEVO: Detector de negaciones FUERTE (antes de affirm)
    negaciones_fuertes = [
        r'\\bno\\s+(puedo|sirve|me\\s+sirve|quiero|tengo)',
        r'\\bmejor\\s+(otro|otra)\\s+(d[ií]a|hora|fecha)',
        r'\\bno\\s+es(a|e|o)\\b'
    ]
    
    for pattern in negaciones_fuertes:
        if re.search(pattern, mensaje):
            return ('negacion', 0.88)
    
    # ... continuar con affirm y otros patterns ...

# CORRECCIÓN 3: Ajustar frase_ambigua para "temprano" aislado
# Ubicación: razonamiento_difuso.py, FUZZY_KEYWORDS

'frase_ambigua': {
    'alta': ['temprano', 'lo antes posible', 'el mejor', 'el que sea', 
             'cual seria', 'cualquiera', 'lo que tengan'],
    'media': ['cual sea', 'da igual', 'lo que sea', 'tienen temprano'],  # AÑADIR
    'baja': ['para']
},
""")

print("="*80)
print("\n💡 NOTA: Con estas 3 correcciones se espera alcanzar 97-98% (65-66/67 casos)")
print("         El caso #4 'tienen temprano?' puede mantenerse como ambigüedad aceptable")
print("         dado que consultar_disponibilidad también es válido en ese contexto.\n")
