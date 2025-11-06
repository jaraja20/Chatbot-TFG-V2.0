# 🔧 CORRECCIONES APLICADAS - Detección de Urgencia y Confirmación

## Fecha: 2025-11-04

---

## ✅ PROBLEMA 1: Frases de urgencia mal detectadas

**Síntoma**: Frases como "lo antes posible", "estoy apurado", "necesito turno rapido" se detectaban como `consultar_costo` o `agendar_turno` en lugar de `frase_ambigua`.

**Causa raíz**: 
1. LLM con threshold bajo (0.80) dominaba sobre fuzzy
2. Keywords de urgencia faltantes en motor difuso
3. Frases multi-palabra tenían el mismo peso que palabras individuales

**Soluciones aplicadas**:

### 1. Subir threshold del LLM (0.80 → 0.88)
**Archivo**: `orquestador_inteligente.py`
```python
# Antes:
elif confianza_llm > 0.80:
    intent_final = intent_llm
    
# Después:
elif confianza_llm > 0.88:  # threshold más estricto
    intent_final = intent_llm
```

### 2. Expandir keywords de urgencia en motor difuso
**Archivo**: `razonamiento_difuso.py`
```python
'frase_ambigua': {
    'alta': [
        'temprano', 'lo antes posible', 'el mejor', 'el que sea', 
        'cual seria', 'cualquiera', 'lo que tengan',
        'urgente', 'apurado', 'apurada', 'rapido', 'rápido',
        'necesito ya', 'ahora mismo', 'cuanto antes', 'estoy apurado',
        'cuanto antes mejor', 'lo mas pronto', 'lo más pronto',
        'turno rapido', 'turno rápido', 'turno urgente', 'cita urgente'
    ],
    'media': ['cual sea', 'da igual', 'lo que sea', 'ya', 'pronto', 'porfavor', 'mejor'],
    'baja': ['para', 'ahora']
}
```

### 3. Remover 'urgente' de agendar_turno
**Archivo**: `razonamiento_difuso.py`
```python
'agendar_turno': {
    'alta': ['quiero', 'necesito', 'kiero', 'nesecito', 'marcar', 
             'agendar', 'sacar', 'reservar', 'turno', 'cita'],  # SIN 'urgente'
    ...
}
```

### 4. Implementar multiplicador x2 para bigramas/trigramas
**Archivo**: `razonamiento_difuso.py`
```python
def calculate_fuzzy_membership(self, mensaje: str, intent: str) -> float:
    ...
    for keyword in keywords:
        if keyword in mensaje_lower:
            # Dar doble peso a frases multi-palabra (bigramas/trigramas)
            # Esto hace que "turno rapido" gane sobre "necesito" individual
            multiplicador = 2.0 if ' ' in keyword else 1.0
            total_score += peso * multiplicador
            total_weight += peso * multiplicador
```

**Resultados**:
```
TEST DE DETECCIÓN DE URGENCIA - 6/6 casos (100%)
✅ 'lo antes posible porfavor' → frase_ambigua (0.72)
✅ 'estoy apurado necesito ya' → frase_ambigua (0.85)
✅ 'urgente' → frase_ambigua (0.50)
✅ 'necesito turno rapido' → frase_ambigua (0.75)
✅ 'cuanto antes mejor' → frase_ambigua (0.82)
✅ 'ahora mismo' → frase_ambigua (0.70)
```

---

## ✅ PROBLEMA 2: Confirmaciones no detectadas

**Síntoma**: Usuario dice "confirmo" o "sí" pero el sistema responde "No estoy seguro de entender".

**Causa raíz**: Motor difuso tenía el intent `confirmar` pero el sistema espera `affirm`.

**Soluciones aplicadas**:

### 1. Renombrar intent de 'confirmar' → 'affirm'
**Archivo**: `razonamiento_difuso.py`
```python
# Antes:
'confirmar': {
    'alta': ['si', 'sí', 'confirmo', 'acepto', 'ok', 'vale'],
    ...
}

# Después:
'affirm': {
    'alta': ['si', 'sí', 'confirmo', 'acepto', 'ok', 'vale', 
             'afirmativo', 'correcto', 'exacto'],
    'media': ['esta bien', 'está bien', 'perfecto', 'de acuerdo', 'claro'],
    'baja': ['bien', 'bueno']
}
```

### 2. Resolver conflicto con consultar_costo
**Archivo**: `razonamiento_difuso.py`

"vale" estaba en ambos intents causando empate:
```python
# Antes:
'consultar_costo': {
    'alta': ['cuanto', 'cuánto', 'costo', 'precio', 'vale', 'bale', 'cuesta'],
    ...
}

# Después (vale solo en contexto de precio):
'consultar_costo': {
    'alta': ['cuanto', 'cuánto', 'costo', 'precio', 'cuanto vale', 'bale', 'cuesta'],
    ...
}
```

**Resultados**:
```
TEST DE DETECCIÓN DE CONFIRMACIÓN (Motor Difuso) - 10/10 casos (100%)
✅ 'si' → affirm (0.50)
✅ 'sí' → affirm (0.50)
✅ 'confirmo' → affirm (0.50)
✅ 'acepto' → affirm (0.50)
✅ 'ok' → affirm (0.50)
✅ 'vale' → affirm (0.50)
✅ 'está bien' → affirm (0.60)
✅ 'de acuerdo' → affirm (0.55)
✅ 'correcto' → affirm (0.50)
✅ 'exacto' → affirm (0.50)
```

### 3. **[FIX CRÍTICO]** Contexto devolvía "confirmar" en lugar de "affirm"
**Archivo**: `orquestador_inteligente.py` (líneas 654-662)

**Problema MUY GRAVE**: Cuando usuario tenía datos completos (nombre+cédula+fecha+hora+email) y escribía "confirmo" o "sí", el contexto detectaba con **alta confianza 0.97** que era intent `"confirmar"`, pero el sistema **NO TIENE** handler para ese intent (solo existe handler para `"affirm"` en línea 2180). Resultado: **fallback** ("No estoy seguro de entender").

**Antes**:
```python
if mensaje_limpio in ['esta bien', 'está bien', 'ok', 'vale', 'si', 'sí', ...]:
    logger.info(f"🎯 [CONTEXTO] Usuario confirma turno completo → confirmar")
    return ("confirmar", 0.97)  # ❌ Intent inexistente

if any(frase in mensaje_lower for frase in ['si confirmo', 'sí confirmo', ...]):
    logger.info(f"🎯 [CONTEXTO] Usuario confirma turno con frase → confirmar")
    return ("confirmar", 0.97)  # ❌ Intent inexistente
```

**Después**:
```python
if mensaje_limpio in ['esta bien', 'está bien', 'ok', 'vale', 'si', 'sí', ...]:
    logger.info(f"🎯 [CONTEXTO] Usuario confirma turno completo → affirm")
    return ("affirm", 0.97)  # ✅ Intent correcto con handler

if any(frase in mensaje_lower for frase in ['si confirmo', 'sí confirmo', ...]):
    logger.info(f"🎯 [CONTEXTO] Usuario confirma turno con frase → affirm")
    return ("affirm", 0.97)  # ✅ Intent correcto con handler
```

**Resultados**:
```
TEST DE CONFIRMACIÓN CON CONTEXTO COMPLETO - 10/10 casos (100%)
✅ 'confirmo' → affirm (0.97)  ⭐ Alta confianza (contexto)
✅ 'si' → affirm (0.97)
✅ 'sí' → affirm (0.97)
✅ 'ok' → affirm (0.97)
✅ 'vale' → affirm (0.97)
✅ 'acepto' → affirm (0.97)
✅ 'perfecto' → affirm (0.97)
✅ 'de acuerdo' → affirm (0.97)
✅ 'está bien' → affirm (0.97)
✅ 'si confirmo' → affirm (0.97)
```

**Impacto**: Este era el bug principal que impedía confirmar turnos en producción. Ahora con confianza 0.97 el contexto gana sobre fuzzy (0.50) y LLM, asegurando detección correcta.

---

## 📊 IMPACTO GENERAL

### Sistema antes:
- ❌ Frases de urgencia detectadas como `consultar_costo` (LLM dominaba con 0.85)
- ❌ Confirmaciones no funcionaban ("confirmo" → fallback)
- ❌ "necesito turno rapido" → `agendar_turno` (no detectaba urgencia)

### Sistema después:
- ✅ Todas las frases de urgencia detectadas correctamente (6/6 = 100%)
- ✅ Todas las confirmaciones funcionan (10/10 = 100%)
- ✅ Bigramas/trigramas priorizados correctamente (x2 peso)
- ✅ LLM solo gana con confianza >0.88 (más estricto)

### Archivos modificados:
1. `orquestador_inteligente.py` - Threshold LLM 0.80→0.88 + **FIX CRÍTICO contexto "confirmar"→"affirm"**
2. `razonamiento_difuso.py` - Keywords expandidas, multiplicador bigramas, affirm
3. `test_urgencia.py` - Test de validación (NUEVO)
4. `test_affirm.py` - Test de confirmaciones (NUEVO)
5. `test_confirmar_turno.py` - Test de confirmación con contexto completo (NUEVO)

---

## 🎯 PRÓXIMOS PASOS

1. ✅ **Urgencia y confirmación**: RESUELTO
2. ⏳ **Mega test completo**: Ejecutar para verificar que no hubo regresiones
3. ⏳ **Casos fallidos restantes**: Resolver los 4 casos del 94% → 98%

---

**Estado actual**: Sistema al **94.0%** con detección de urgencia y confirmación 100% funcional.
