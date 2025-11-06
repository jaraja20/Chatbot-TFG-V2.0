# FIX: Aceptación de Horario Alternativo cuando el Solicitado está Lleno

## 📅 Fecha: 2025-11-06

## 🐛 PROBLEMA REPORTADO

**Conversación fallida**:
```
Bot: ¿A qué hora prefieres?
Usuario: 13:30

Bot: ⚠️ Lo siento, el horario 13:30 ya está completo (2 personas agendadas).
     🌟 Te recomiendo el siguiente horario disponible: **14:00**
     Otros horarios disponibles: 14:00, 14:30, 15:00
     ¿Prefieres alguno de estos?

Usuario: está bien                    ← Acepta el horario recomendado (14:00)

Bot: [No responde o no reconoce la aceptación]  ❌
```

**Causa raíz**:
Cuando el sistema detecta que un horario está lleno y sugiere una alternativa:
1. ✅ Resetea `contexto.hora = None` (correcto)
2. ✅ Muestra el siguiente horario disponible (correcto)
3. ❌ **NO guarda** el horario sugerido en `contexto.hora_recomendada`
4. ❌ Cuando el usuario responde "está bien", el sistema no sabe qué horario está aceptando

**Impacto**:
- Usuario debe repetir el horario manualmente ("14:00")
- Conversación no fluida
- Confusión del usuario

---

## ✅ SOLUCIÓN IMPLEMENTADA

### Cambio 1: Guardar Horario Recomendado al Rechazar por Lleno

**Archivo**: `orquestador_inteligente.py` líneas ~2754-2757

**ANTES**:
```python
if horarios_disponibles:
    siguiente_horario = horarios_disponibles[0]
    return (
        f"⚠️ Lo siento, el horario {hora_obj.strftime('%H:%M')} ya está completo (2 personas agendadas).\n\n"
        f"🌟 Te recomiendo el siguiente horario disponible: **{siguiente_horario}**\n\n"
        f"Otros horarios disponibles: {', '.join(horarios_disponibles[:5])}\n\n"
        f"¿Prefieres alguno de estos?"
    )
# ❌ No guarda siguiente_horario en contexto.hora_recomendada
```

**DESPUÉS**:
```python
if horarios_disponibles:
    siguiente_horario = horarios_disponibles[0]
    # 🔥 NUEVO: Guardar horario recomendado para que el usuario pueda aceptarlo con "sí"
    contexto.hora_recomendada = siguiente_horario
    logger.info(f"💡 Horario recomendado guardado: {siguiente_horario}")
    return (
        f"⚠️ Lo siento, el horario {hora_obj.strftime('%H:%M')} ya está completo (2 personas agendadas).\n\n"
        f"🌟 Te recomiendo el siguiente horario disponible: **{siguiente_horario}**\n\n"
        f"Otros horarios disponibles: {', '.join(horarios_disponibles[:5])}\n\n"
        f"¿Prefieres alguno de estos?"
    )
```

**Efecto**: Ahora el horario sugerido se guarda en `contexto.hora_recomendada = "14:00"`.

---

### Cambio 2: Ampliar Frases de Aceptación

**Archivo**: `orquestador_inteligente.py` líneas ~675-693

**ANTES**:
```python
if any(frase in mensaje_lower for frase in [
    'esta bien', 'está bien', 'ok', 'vale', 'acepto', 'perfecto',
    'me parece bien', 'si esa', 'sí esa', 'esa hora',
    'la hora que recomiendas', 'la que recomiendas'
]):
```

**DESPUÉS**:
```python
if any(frase in mensaje_lower for frase in [
    'esta bien', 'está bien', 'ok', 'vale', 'acepto', 'perfecto',
    'me parece bien', 'si esa', 'sí esa', 'esa hora',
    'la hora que recomiendas', 'la que recomiendas',
    'ese horario', 'ese', 'esa', 'si', 'sí',  # 🔥 NUEVO
    'dale', 'bueno', 'bien', 'genial', 'excelente',  # 🔥 NUEVO
    'me sirve', 'me viene bien', 'prefiero ese'  # 🔥 NUEVO
]):
    logger.info(f"🎯 [CONTEXTO] Usuario acepta hora recomendada '{contexto.hora_recomendada}' → elegir_horario")
    return ("elegir_horario", 0.97)
```

**Efecto**: Ahora detecta muchas más formas de aceptación.

---

### Cambio 3: Mejorar Logging para Debugging

**Logging agregado**:
```python
logger.info(f"💡 Horario recomendado guardado: {siguiente_horario}")
logger.info(f"🎯 [CONTEXTO] Usuario acepta hora recomendada '{contexto.hora_recomendada}' → elegir_horario")
```

**Efecto**: Podemos rastrear en los logs qué horario se guardó y cuándo se aceptó.

---

## 🔄 FLUJO COMPLETO

### Escenario: Horario 13:30 está lleno

**1. Usuario intenta agendar horario lleno**:
```
Usuario: 13:30
```

**2. Sistema detecta ocupación >= 2**:
```python
# En elegir_horario intent
disponibilidad = obtener_disponibilidad_real(contexto.fecha)
ocupacion = disponibilidad.get('13:30', 0)  # ocupacion = 2

if ocupacion >= 2:
    # Buscar siguiente disponible
    horarios_disponibles = ['14:00', '14:30', '15:00']
    siguiente_horario = '14:00'
    
    contexto.hora = None  # Resetear hora llena
    contexto.hora_recomendada = '14:00'  # 🔥 NUEVO: Guardar recomendación
    
    return "⚠️ Lo siento, 13:30 está completo. 🌟 Te recomiendo: 14:00"
```

**3. Usuario acepta recomendación**:
```
Usuario: está bien
```

**4. Sistema detecta aceptación**:
```python
# En clasificar() - detección contextual
if contexto.hora_recomendada and not contexto.hora:
    if 'esta bien' in mensaje_lower:
        return ("elegir_horario", 0.97)  # 🔥 Fuerza intent elegir_horario
```

**5. Sistema asigna horario recomendado**:
```python
# En elegir_horario intent
if contexto.hora_recomendada:
    contexto.hora = contexto.hora_recomendada  # hora = '14:00'
    
    if not contexto.email:
        return "Perfecto! ¿Cuál es tu email?"
```

**6. Usuario completa el flujo**:
```
Usuario: user@example.com
Bot: 📋 Resumen:
     Hora: 14:00  ← ✅ Horario recomendado aceptado
     ¿Confirmas?
```

---

## 🧪 PRUEBAS DE VALIDACIÓN

### Test 1: Aceptación con "está bien"

**Setup**: Agendar 2 turnos para 13:30

**Conversación**:
```
Bot: ¿A qué hora prefieres?
Usuario: 13:30

Bot: ⚠️ Lo siento, el horario 13:30 ya está completo (2 personas agendadas).
     🌟 Te recomiendo el siguiente horario disponible: **14:00**
     Otros horarios disponibles: 14:00, 14:30, 15:00
     ¿Prefieres alguno de estos?

Usuario: está bien                    ← Acepta 14:00

Bot: Perfecto! Para enviarte la confirmación y el código QR, ¿cuál es tu email?
                                      ✅ Aceptó horario recomendado
```

**Verificación en logs**:
```
💡 Horario recomendado guardado: 14:00
🎯 [CONTEXTO] Usuario acepta hora recomendada '14:00' → elegir_horario
```

---

### Test 2: Variaciones de aceptación

**Todas estas respuestas deben funcionar**:
```
Usuario: está bien     → ✅ Acepta 14:00
Usuario: ok            → ✅ Acepta 14:00
Usuario: sí            → ✅ Acepta 14:00
Usuario: si            → ✅ Acepta 14:00
Usuario: perfecto      → ✅ Acepta 14:00
Usuario: dale          → ✅ Acepta 14:00
Usuario: bueno         → ✅ Acepta 14:00
Usuario: me sirve      → ✅ Acepta 14:00
Usuario: ese horario   → ✅ Acepta 14:00
Usuario: esa hora      → ✅ Acepta 14:00
```

---

### Test 3: Usuario elige otro horario de la lista

**Conversación**:
```
Bot: ⚠️ Lo siento, 13:30 está completo.
     🌟 Te recomiendo: 14:00
     Otros horarios: 14:00, 14:30, 15:00
     ¿Prefieres alguno de estos?

Usuario: 14:30                        ← Elige otro de la lista

Bot: Perfecto! ¿Cuál es tu email?    ✅ Acepta 14:30 (no 14:00)
```

**Resultado esperado**: Sistema acepta 14:30 (no fuerza 14:00).

---

### Test 4: Verificación final en resumen

```
Bot: 📋 Perfecto! Resumen de tu turno:
     Nombre: Juan Pérez
     Cédula: 1234567
     Fecha: 2025-11-13
     Hora: 14:00                      ← ✅ Horario alternativo aceptado (no 13:30)
     Email: user@example.com
     ¿Confirmas estos datos?
```

---

## 📊 FRASES DE ACEPTACIÓN SOPORTADAS

**Frases largas**:
- ✅ "está bien"
- ✅ "esta bien"
- ✅ "me parece bien"
- ✅ "me sirve"
- ✅ "me viene bien"
- ✅ "ese horario"
- ✅ "esa hora"
- ✅ "si esa"
- ✅ "sí esa"
- ✅ "la hora que recomiendas"
- ✅ "la que recomiendas"
- ✅ "prefiero ese"

**Palabras cortas**:
- ✅ "sí"
- ✅ "si"
- ✅ "ok"
- ✅ "vale"
- ✅ "acepto"
- ✅ "perfecto"
- ✅ "dale"
- ✅ "bueno"
- ✅ "bien"
- ✅ "genial"
- ✅ "excelente"
- ✅ "ese"
- ✅ "esa"

---

## 🎯 COMPARACIÓN ANTES/DESPUÉS

### Antes del Fix ❌

**Conversación**:
```
Usuario: 13:30
Bot: ⚠️ 13:30 está completo. Te recomiendo: 14:00

Usuario: está bien
Bot: [Sin respuesta / confusión]      ❌

Usuario: 14:00                         ← Usuario debe repetir manualmente
Bot: Perfecto! ¿Email?                ✅ (después de repetir)
```

**Problemas**:
- Usuario debe repetir el horario manualmente
- Conversación no fluida (2 mensajes extra)
- Experiencia confusa

---

### Después del Fix ✅

**Conversación**:
```
Usuario: 13:30
Bot: ⚠️ 13:30 está completo. Te recomiendo: 14:00

Usuario: está bien                     ← Acepta directamente
Bot: Perfecto! ¿Email?                ✅ Continúa flujo
```

**Mejoras**:
- Aceptación directa con "está bien"
- Conversación fluida (sin repetir)
- Experiencia natural

---

## 🔍 CASOS EDGE MANEJADOS

### Caso 1: Usuario dice "no" al horario sugerido

**Conversación**:
```
Bot: Te recomiendo: 14:00
Usuario: no

Bot: [Detecta negación]
     ¿A qué hora prefieres? Por ejemplo: 09:00, 14:30...
```

**Resultado**: Usuario puede elegir otro horario manualmente.

---

### Caso 2: Usuario elige horario específico de la lista

**Conversación**:
```
Bot: Te recomiendo: 14:00
     Otros: 14:00, 14:30, 15:00
Usuario: 14:30                         ← Elige específico

Bot: Perfecto! ¿Email?                ✅ Usa 14:30 (no 14:00)
```

**Resultado**: Sistema respeta elección específica.

---

### Caso 3: Usuario acepta con frase ambigua

**Conversación**:
```
Bot: Te recomiendo: 14:00
Usuario: ese                           ← Ambiguo pero válido

Bot: Perfecto! ¿Email?                ✅ Usa 14:00
```

**Resultado**: Sistema interpreta "ese" como aceptación del recomendado.

---

## 🚀 DESPLIEGUE

**Archivos modificados**:
- `orquestador_inteligente.py` (2 secciones):
  - Líneas ~2754-2757: Guardar hora_recomendada al rechazar por lleno
  - Líneas ~675-693: Ampliar frases de aceptación

**Comando para reiniciar**:
```bash
cd "c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot"
python app.py
```

**Watchdog**: Si está activo, cambios se aplican automáticamente.

---

## 📝 LOGGING PARA DEBUGGING

**Buscar en logs**:

```bash
# Cuando se guarda hora recomendada:
grep "Horario recomendado guardado" logs/app.log

# Cuando usuario acepta:
grep "Usuario acepta hora recomendada" logs/app.log

# Ver horario específico recomendado:
grep "hora_recomendada.*14:00" logs/app.log
```

**Ejemplo de logs esperados**:
```
[INFO] ⚠️ Horario 13:30 lleno (2/2) para 2025-11-13
[INFO] 💡 Horario recomendado guardado: 14:00
[INFO] 🎯 [CONTEXTO] Usuario acepta hora recomendada '14:00' → elegir_horario
```

---

## ✅ CHECKLIST DE VALIDACIÓN

- [ ] Reiniciar Flask server
- [ ] Agendar 2 turnos para 13:30
- [ ] Intentar 3er turno para 13:30 → debe recomendar 14:00
- [ ] Responder "está bien" → debe aceptar 14:00
- [ ] Verificar en resumen que hora = 14:00
- [ ] Confirmar y verificar en BD que se guardó 14:00
- [ ] Probar variaciones: "ok", "sí", "dale", "perfecto"
- [ ] Probar rechazar y elegir otro: "no, prefiero 14:30"
- [ ] Revisar logs para mensajes de hora_recomendada

---

## 🎉 RESUMEN EJECUTIVO

**Problema crítico resuelto**:
✅ Usuario puede aceptar horario alternativo con "está bien" cuando el solicitado está lleno

**Mejoras implementadas**:
1. ✅ Sistema guarda `hora_recomendada` al sugerir alternativa
2. ✅ Amplió frases de aceptación de 10 a 20+ variaciones
3. ✅ Logging mejorado para debugging
4. ✅ Conversación fluida sin repetir horarios

**Impacto en UX**:
- ⏱️ Reducción de mensajes: 4 mensajes → 2 mensajes
- 📈 Conversión más fluida
- 😊 Experiencia más natural

**Estado**: ✅ LISTO PARA PRUEBAS
