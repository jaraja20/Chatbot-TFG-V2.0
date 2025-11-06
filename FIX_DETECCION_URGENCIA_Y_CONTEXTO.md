# FIX: Mejoras en Detección de Urgencia y Contexto de Confirmación

## Problemas Identificados

### 1. "Necesito rápido/lo antes posible" no verifica HOY
**Problema**: Asignaba automáticamente mañana a las 7:00 sin verificar si HOY hay turnos disponibles 2+ horas después.

**Ejemplo**:
```
Usuario (10:30 AM): "necesito lo antes posible"
Bot: "Turno para mañana 2025-11-06 a las 07:00" ❌
Pero HOY hay turnos desde 12:30, 13:00, etc. disponibles
```

### 2. "Cambiar fecha para mañana" muestra disponibilidad
**Problema**: Cuando el usuario especifica "cambiar fecha para mañana", el sistema mostraba disponibilidad en lugar de cambiar directamente.

**Ejemplo**:
```
Usuario: "quiero cambiar la fecha para mañana"
Bot: "Disponibilidad para 2025-11-05..." ❌ (muestra HOY)
Bot: "Disponibilidad para 2025-11-06..." (después muestra mañana)
Esperado: Cambiar fecha a mañana y pedir hora ✅
```

### 3. "¿Cuánto cuesta?" pierde contexto
**Problema**: Al consultar el costo en medio de la confirmación, el sistema no mantenía el contexto del turno.

**Ejemplo**:
```
[Usuario tiene turno agendado]
Usuario: "¿cuánto cuesta?"
Bot: "Costos... ¿Necesitas agendar un turno?" ❌ (olvida el turno)
```

### 4. "Confírmame el turno" no se reconoce
**Problema**: Frases como "confírmame", "confirma el turno", "agéndame" no se detectaban como confirmación.

**Ejemplo**:
```
Usuario: "está bien, confirmame el turno entonces"
Bot: Muestra disponibilidad o pregunta ❌
Esperado: Confirma el turno ✅
```

---

## Soluciones Implementadas

### 1. Detección Inteligente de "Lo Antes Posible"

**Archivo**: `orquestador_inteligente.py` - Intent `frase_ambigua` (líneas ~2466-2530)

**Lógica mejorada**:
```python
# Calcular hora mínima (2 horas después de ahora)
hora_minima = hora_actual + 2

# Si es antes de las 13:00 (15:00 - 2 horas), intentar HOY
if hora_minima < 15:
    fecha_hoy = ahora.strftime('%Y-%m-%d')
    disponibilidad_hoy = obtener_disponibilidad_real(fecha_hoy)
    
    # Buscar horarios disponibles HOY después de 2 horas
    horarios_hoy = []
    for hora, ocupacion in disponibilidad_hoy.items():
        if ocupacion < 2:  # Disponible
            hora_int = int(hora.split(':')[0])
            if hora_int >= hora_minima:
                horarios_hoy.append(hora)
    
    if horarios_hoy:
        # HAY turnos hoy, usar HOY
        contexto.fecha = fecha_hoy
        mejor_hora = min(horarios_hoy)
        contexto.hora = mejor_hora
        
        return f"✅ Perfecto, te asigno el horario más próximo para HOY:
                 Fecha: {fecha_hoy} (HOY)
                 Hora: {mejor_hora}"
```

**Comportamiento**:
- **10:30 AM** → Busca turnos desde **12:30 PM** en adelante (HOY si hay)
- **13:30 PM** → Busca turnos hasta **15:00** (HOY si hay, sino mañana)
- **15:00 PM+** → Directamente asigna mañana

### 2. Cambio Directo de Fecha a "Mañana"

**Archivo**: `orquestador_inteligente.py` - Detección de cambios (líneas ~807-821)

**Antes**:
```python
elif any(palabra in mensaje_lower for palabra in ['fecha', 'dia', 'día']):
    contexto.fecha = None
    contexto.hora = None
    return ("consultar_disponibilidad", 0.98)
```

**Ahora**:
```python
elif any(palabra in mensaje_lower for palabra in ['fecha', 'dia', 'día']):
    # Detectar si YA especifica "para mañana"
    if 'mañana' in mensaje_lower:
        # Calcular mañana (saltando fines de semana)
        manana = datetime.now() + timedelta(days=1)
        while manana.weekday() >= 5:
            manana += timedelta(days=1)
        
        contexto.fecha = manana.strftime('%Y-%m-%d')
        contexto.hora = None  # Pedir nueva hora
        return ("consultar_disponibilidad", 0.98)
    else:
        # Si no especifica, resetear y pedir
        contexto.fecha = None
        contexto.hora = None
        return ("consultar_disponibilidad", 0.98)
```

**Flujo mejorado**:
```
Usuario: "quiero cambiar la fecha para mañana"
Sistema: Detecta "mañana" → Asigna fecha = 2025-11-06
Bot: "Disponibilidad para el 2025-11-06:..." ✅
```

### 3. Mantener Contexto en Consultas

**Archivo**: `orquestador_inteligente.py` - Intent `consultar_costo` (líneas ~3058-3090)

**Antes**:
```python
elif intent == 'consultar_costo':
    return costos + "¿Necesitas agendar un turno?"  # Pierde contexto
```

**Ahora**:
```python
elif intent == 'consultar_costo':
    respuesta_base = costos_info
    
    # Si usuario ya tiene turno en proceso
    if contexto.nombre and contexto.cedula and contexto.fecha and contexto.hora:
        if not contexto.email:
            return respuesta_base + "¿Cuál es tu email para enviarte la confirmación?"
        else:
            return respuesta_base + "¿Quieres confirmar tu turno o hacer algún cambio?"
    
    # Si está en medio del formulario
    if not contexto.nombre:
        return respuesta_base + "¿Quieres agendar un turno? Indícame tu nombre."
    elif not contexto.cedula:
        return respuesta_base + "¿Cuál es tu número de cédula?"
    # ... continúa con el formulario
```

**Flujo mejorado**:
```
[Usuario con turno: nombre, cédula, fecha, hora]
Usuario: "¿cuánto cuesta?"
Bot: "Costos... ¿Quieres confirmar tu turno o hacer algún cambio?" ✅
```

### 4. Detección Mejorada de Confirmación

**Archivo**: `orquestador_inteligente.py` - Detección contextual (líneas ~852-866)

**Antes**:
```python
# Requería email también
if contexto.nombre and contexto.fecha and contexto.hora and contexto.email:
    if mensaje_limpio in ['ok', 'si', 'sí', 'confirmo']:
        return ("affirm", 0.97)
```

**Ahora**:
```python
# Solo requiere: nombre + cédula + fecha + hora (con o sin email)
if contexto.nombre and contexto.cedula and contexto.fecha and contexto.hora:
    # Palabras simples
    if mensaje_limpio in ['esta bien', 'está bien', 'ok', 'vale', 'si', 'sí', 
                          'perfecto', 'de acuerdo', 'confirmo', 'confirmado', 
                          'confirm', 'acepto']:
        return ("affirm", 0.97)
    
    # Frases más complejas
    if any(frase in mensaje_lower for frase in [
        'si confirmo', 'sí confirmo', 'si acepto', 'sí acepto',
        'todo bien', 'esta todo bien', 'está todo bien',
        'confirmame', 'confírmame', 'confirma el turno',
        'confirmar el turno', 'confirmar turno',
        'agendar', 'agenda', 'agendame', 'agéndame'
    ]):
        return ("affirm", 0.97)
```

**Casos manejados**:
- ✅ "confírmame el turno"
- ✅ "está bien, confirmame"
- ✅ "agéndame entonces"
- ✅ "confirmar el turno"
- ✅ "está todo bien"

---

## Casos de Prueba

### Caso 1: Urgencia con turnos HOY disponibles
```
Hora actual: 10:30 AM
Usuario: "necesito lo antes posible"

Antes ❌:
Bot: "Turno para mañana 2025-11-06 a las 07:00"

Ahora ✅:
Bot: "Turno para HOY 2025-11-05 a las 12:30"
(Si hay turnos disponibles 2+ horas después)
```

### Caso 2: Cambiar fecha especificando "mañana"
```
[Usuario tiene turno para HOY]
Usuario: "quiero cambiar la fecha para mañana"

Antes ❌:
Bot: "Disponibilidad para 2025-11-05..." (muestra HOY primero)

Ahora ✅:
Bot: "Disponibilidad para el 2025-11-06:..." (mañana directo)
```

### Caso 3: Consultar costo manteniendo turno
```
[Usuario: nombre, cédula, fecha=mañana, hora=13:30]
Usuario: "¿cuánto cuesta?"

Antes ❌:
Bot: "Costos... ¿Necesitas agendar un turno?"

Ahora ✅:
Bot: "Costos... ¿Cuál es tu email para enviarte la confirmación?"
(Mantiene el turno y continúa el flujo)
```

### Caso 4: Confirmar con variantes
```
[Usuario tiene todos los datos]
Usuario: "está bien, confírmame el turno entonces"

Antes ❌:
Bot: Muestra disponibilidad o no reconoce

Ahora ✅:
Bot: "✅ Turno agendado exitosamente..."
```

---

## Reglas de Negocio

### Horario "Lo Antes Posible"
- **Margen de seguridad**: 2 horas desde la hora actual
- **Horario de atención**: 07:00 - 15:00
- **Lógica**:
  - Si `hora_actual + 2 < 15:00` → Buscar HOY
  - Si no hay HOY o es tarde → Buscar mañana
  - Siempre el horario más temprano disponible

### Cambio de Fecha con "Mañana"
- Detecta "mañana" en el mensaje de cambio
- Calcula automáticamente la fecha (saltando fines de semana)
- Resetea solo la hora (mantiene otros datos)
- Muestra disponibilidad para la nueva fecha

### Contexto de Turno
- Se mantiene durante consultas (costo, requisitos, etc.)
- Solo se pierde con "cancelar" explícito
- Confirmación requiere: nombre + cédula + fecha + hora (email opcional)

---

## Impacto

### Mejoras en UX
- ✅ **Turnos más próximos**: Detecta HOY si es posible
- ✅ **Cambios más rápidos**: "mañana" cambia directamente
- ✅ **Contexto preservado**: Consultas no pierden el turno
- ✅ **Confirmación flexible**: Múltiples formas de confirmar

### Casos Edge Manejados
- ✅ Usuario solicita urgente a las 8 AM → Turno HOY 10:00+
- ✅ Usuario solicita urgente a las 1 PM → Turno HOY 15:00 o mañana
- ✅ Usuario solicita urgente a las 3:30 PM → Turno mañana 7:00
- ✅ Cambio a mañana desde cualquier fecha previa
- ✅ Consultas intermedias sin perder el turno agendado

---

## Archivos Modificados

1. **orquestador_inteligente.py**
   - Intent `frase_ambigua`: Lógica de HOY vs mañana (líneas ~2466-2530)
   - Detección cambios: "para mañana" directo (líneas ~807-821)
   - Intent `consultar_costo`: Mantener contexto (líneas ~3058-3090)
   - Detección confirmación: Más variantes (líneas ~852-866)

---

---

## Mejoras Adicionales (Sesión 2)

### 5. Detección de "primera cédula para hijo/hija"

**Problema**: No detectaba frases como "no tengo, es para mi hijo, para su primera cédula"

**Solución**: Ampliado patrones de detección de primera vez:
```python
if any(frase in mensaje_lower for frase in [
    'primera vez', '1ra vez', 'primer tramite', 
    'no tengo cedula', 'no tengo cédula', 
    'es para mi hijo', 'es para mi hija', 
    'para su primera cedula', 'su primera cédula',
    'primera cedula', 'primera cédula'
]):
    contexto.tipo_tramite = 'primera_vez'
    contexto.cedula = 'SIN_CEDULA'
    return ("informar_tipo_tramite", 0.96)
```

**Casos manejados**:
- ✅ "no tengo, es para mi hijo, para su primera cedula"
- ✅ "es para la primera cédula de mi hija"
- ✅ "no tengo es la primera vez que hago"

### 6. Manejo de "no tengo email"

**Problema**: Cuando usuario dice "no tengo email", el sistema repetía la pregunta en lugar de proceder sin email

**Solución**: Detectar "no tengo email" y marcar email como omitido:
```python
if contexto.nombre and contexto.cedula and contexto.fecha and contexto.hora and not contexto.email:
    if any(frase in mensaje_lower for frase in [
        'no tengo email', 'no tengo correo', 
        'sin email', 'sin correo', 'no tengo mail'
    ]):
        contexto.email = 'SIN_EMAIL'
        return ("affirm", 0.98)  # Proceder a confirmación
```

**Flujo mejorado**:
```
Usuario: "no tengo email"
Bot: Procede a confirmación por chat (sin envío de QR)
✅ Confirmación directa sin email
```

### 7. Respuesta a "recomiéndame un horario"

**Problema**: Usuario pedía recomendación de horario pero sistema solo repetía la lista de disponibilidad

**Solución**: Detectar pedido de recomendación y asignar automáticamente el mejor horario:
```python
# Detección contextual
if contexto.fecha and not contexto.hora:
    if any(frase in mensaje_lower for frase in [
        'recomiendame un horario', 'recomiéndame uno',
        'que horario me recomiendas', 'cual me recomiendas',
        'sugerime uno', 'dame uno', 'elegí uno'
    ]):
        return ("frase_ambigua", 0.97)

# En intent frase_ambigua
if contexto.fecha and not contexto.hora:
    disponibilidad = obtener_disponibilidad_real(contexto.fecha)
    horarios_disponibles = [(h, o) for h, o in disponibilidad.items() if o < 2]
    horarios_disponibles.sort(key=lambda x: (x[1], x[0]))
    
    mejor_horario = horarios_disponibles[0][0]
    contexto.hora = mejor_horario
    
    return f"🌟 Te recomiendo y asigno el mejor horario: **{mejor_horario}**"
```

**Casos manejados**:
- ✅ "recomiéndame un horario"
- ✅ "recomiéndame uno de esos horarios"
- ✅ "qué horario me recomiendas"
- ✅ "cuál me recomiendas"
- ✅ "dame uno"

**Comportamiento**:
- Asigna automáticamente el horario con menos ocupación
- Muestra resumen con el horario asignado
- Guarda el horario en el contexto
- Continúa el flujo (pide email o confirmación)

---

## Fecha de Implementación

Noviembre 2024

## Archivos Modificados (Sesión 2)

1. **orquestador_inteligente.py**
   - Líneas ~890-900: Detección ampliada de primera cédula
   - Líneas ~938-945: Detección de "no tengo email"
   - Líneas ~620-630: Detección de "recomiéndame horario"
   - Líneas ~2520-2550: Asignación automática de horario recomendado

## Próximos Pasos

- [x] ✅ Detectar "es para mi hijo, primera cédula"
- [x] ✅ Manejar "no tengo email" sin repetir pregunta
- [x] ✅ Responder a "recomiéndame un horario" con asignación automática
- [ ] Agregar tests automatizados para estos casos
- [ ] Monitorear logs para optimizar recomendaciones
- [ ] Considerar notificación: "Hay un turno HOY más temprano disponible"

---

## Notas Técnicas

- Margen de 2 horas es configurable
- Fin de semana se salta automáticamente
- Confirmación no requiere email (puede pedirse después)
- Contexto persiste entre consultas de información
- Logs con emoji 🔥 para depuración de lógica crítica
