# FIX: Flujo de Cambio de Datos en Confirmación

## Problema Identificado

Cuando el usuario solicita cambiar un dato en la confirmación final (ej: "Cambiar cédula"):
1. ✅ El sistema correctamente resetea el campo y pregunta por el nuevo valor
2. ✅ El usuario proporciona el nuevo valor
3. ❌ **BUG**: El sistema NO mostraba el resumen de confirmación actualizado
4. ❌ En su lugar, continuaba preguntando por el siguiente campo faltante

### Ejemplo del Bug (Antes del Fix)

```
Usuario: "Cambiar cédula"
Bot: "¿Cuál es tu número de cédula?"
Usuario: "1231234"
Bot: "¿Para qué día necesitas el turno?"  ❌ INCORRECTO

Comportamiento esperado:
Bot: "📋 Resumen actualizado de tu turno:
      Nombre: Juan
      Cédula: 1231234  ← Actualizada
      Fecha: 2024-01-15
      Hora: 09:00
      Email: juan@example.com
      
      ¿Confirmas estos datos?"  ✅ CORRECTO
```

## Solución Implementada

### 1. Agregado campo de rastreo en SessionContext

**Archivo**: `orquestador_inteligente.py`

```python
class SessionContext:
    def __init__(self, session_id: str):
        # ... campos existentes ...
        self.campo_en_cambio = None  # 🆕 Rastrear qué campo se está cambiando
```

**Propósito**: Permite al sistema recordar que estamos en un proceso de cambio activo.

### 2. Marcado de campo en cambio al detectar comando

**Archivo**: `orquestador_inteligente.py` (líneas ~742-780)

```python
# Cambiar CÉDULA
elif any(palabra in mensaje_lower for palabra in ['cedula', 'cédula', 'ci', 'documento']):
    logger.info(f"🔄 [CAMBIO] Usuario quiere cambiar cédula → resetear cédula")
    contexto.cedula = None
    contexto.campo_en_cambio = 'cedula'  # 🆕 Marcar que estamos cambiando
    return ("informar_cedula", 0.98)

# Cambiar NOMBRE
elif any(palabra in mensaje_lower for palabra in ['nombre', 'nombres']):
    logger.info(f"🔄 [CAMBIO] Usuario quiere cambiar nombre → resetear nombre")
    contexto.nombre = None
    contexto.campo_en_cambio = 'nombre'  # 🆕 Marcar que estamos cambiando
    return ("informar_nombre", 0.98)

# Cambiar EMAIL
if any(palabra in mensaje_lower for palabra in ['email', 'correo', 'mail', 'e-mail']):
    logger.info(f"🔄 [CAMBIO] Usuario quiere cambiar email → resetear email")
    contexto.email = None
    contexto.campo_en_cambio = 'email'  # 🆕 Marcar que estamos cambiando
    return ("informar_email", 0.98)

# Cambiar HORA
elif any(palabra in mensaje_lower for palabra in ['hora', 'horario']):
    logger.info(f"🔄 [CAMBIO] Usuario quiere cambiar hora → resetear hora")
    contexto.hora = None
    contexto.campo_en_cambio = 'hora'  # 🆕 Marcar que estamos cambiando
    return ("consultar_disponibilidad", 0.98)

# Cambiar FECHA
elif any(palabra in mensaje_lower for palabra in ['fecha', 'dia', 'día']):
    logger.info(f"🔄 [CAMBIO] Usuario quiere cambiar fecha → resetear fecha y hora")
    contexto.fecha = None
    contexto.hora = None  # También resetear hora
    contexto.campo_en_cambio = 'fecha'  # 🆕 Marcar que estamos cambiando
    return ("consultar_disponibilidad", 0.98)
```

### 3. Verificación de cambio completado

**Archivo**: `orquestador_inteligente.py` (líneas ~1625-1655)

```python
if not es_comando_cambio:
    entidades = extraer_entidades(user_message, intent, contexto)
    contexto.actualizar(**entidades)
    
    # 🔥 VERIFICAR SI ACABAMOS DE COMPLETAR UN CAMBIO
    # Si acabamos de actualizar un campo que estaba en proceso de cambio
    # y ahora todos los datos están completos, mostrar resumen
    if contexto.campo_en_cambio and contexto.tiene_datos_completos() and entidades:
        logger.info(f"✅ [CAMBIO COMPLETADO] Campo '{contexto.campo_en_cambio}' actualizado → Mostrar resumen")
        
        # Limpiar la bandera de cambio
        contexto.campo_en_cambio = None
        
        # Generar resumen de confirmación
        resumen = f"📋 Perfecto! Resumen actualizado de tu turno:\n"
        resumen += f"Nombre: {contexto.nombre}\n"
        
        # Solo mostrar cédula si tiene una válida
        if contexto.cedula and contexto.cedula != "SIN_CEDULA":
            resumen += f"Cédula: {contexto.cedula}\n"
        else:
            resumen += f"Cédula: Sin cédula (trámite nuevo)\n"
        
        resumen += f"Fecha: {contexto.fecha}\n"
        resumen += f"Hora: {contexto.hora}\n"
        resumen += f"Email: {contexto.email}\n\n"
        resumen += f"¿Confirmas estos datos? (Responde 'sí' para confirmar)\n\n"
        resumen += f"💡 Si quieres corregir algo más, di:\n"
        resumen += f"• 'Cambiar [nombre/cédula/fecha/hora/email]'\n"
        resumen += f"• 'Cancelar' (empezar de nuevo)"
        
        return {
            'text': resumen,
            'intent': 'confirmar',
            'confidence': 0.98,
            'entidades': entidades,
            'contexto': contexto.to_dict()
        }
```

**Lógica**:
1. Verifica si hay un campo marcado como "en cambio" (`campo_en_cambio != None`)
2. Verifica si extrajimos entidades en este mensaje (`entidades != {}`)
3. Verifica si todos los datos están completos (`tiene_datos_completos()`)
4. Si las 3 condiciones se cumplen:
   - Limpia la bandera de cambio
   - Genera y devuelve el resumen de confirmación actualizado
   - Establece intent como "confirmar" para que el flujo continúe correctamente

### 4. Mejora adicional: Comando genérico "cambiar"

**Problema**: Usuario dice solo "cambiar" sin especificar qué campo
**Antes**: Bot respondía "No estoy seguro de entender..."
**Ahora**: Bot pregunta específicamente qué dato quiere cambiar

```python
# Cambiar genérico (sin especificar qué)
else:
    logger.info(f"🔄 [CAMBIO] Usuario quiere cambiar algo (no especificó qué)")
    # Devolver un intent especial para manejar este caso
    return ("aclaracion_cambio", 0.95)

# En generar_respuesta_inteligente():
if intent == 'aclaracion_cambio':
    return (
        "¿Qué dato quieres cambiar? Puedes decir:\n"
        "• 'Cambiar nombre'\n"
        "• 'Cambiar cédula'\n"
        "• 'Cambiar fecha'\n"
        "• 'Cambiar hora'\n"
        "• 'Cambiar email'"
    )
```

## Tests Implementados

**Archivo**: `test_cambio_datos.py`

### Test 1: Flujo completo de cambio de cédula
```
✅ Usuario con datos completos
✅ Dice "Cambiar cédula"
✅ Bot resetea cédula y pregunta por nueva
✅ Usuario proporciona "9876543"
✅ Bot muestra resumen actualizado con nueva cédula
```

### Test 2: Comando genérico "cambiar"
```
✅ Usuario con datos completos
✅ Dice solo "cambiar"
✅ Bot pregunta qué dato quiere cambiar con opciones claras
```

### Test 3: Cambio de email
```
✅ Usuario con datos completos
✅ Dice "Cambiar email"
✅ Bot pregunta por nuevo email
✅ Usuario proporciona nuevo email
✅ Bot muestra resumen actualizado con nuevo email
```

## Resultados

```
================================================================================
✅ TODAS LAS PRUEBAS COMPLETADAS
================================================================================

TEST: Flujo de cambio de datos en confirmación
✅ ¡ÉXITO! El bot mostró el resumen de confirmación actualizado

TEST: Comando genérico 'cambiar'
✅ ¡ÉXITO! El bot pidió aclaración de qué dato cambiar

TEST: Cambiar email
✅ ¡ÉXITO! Mostró resumen después de cambiar email
```

## Archivos Modificados

1. **orquestador_inteligente.py**
   - Agregado campo `campo_en_cambio` en `SessionContext.__init__()`
   - Agregado marcado de campo en cambio en detección de comandos (líneas ~742-780)
   - Agregado verificación de cambio completado (líneas ~1625-1655)
   - Agregado intent `aclaracion_cambio` y su manejo

2. **test_cambio_datos.py** (nuevo archivo)
   - 3 tests completos que validan el flujo de cambio
   - Cobertura de casos: cambio específico, cambio genérico, cambio de email

## Flujo Mejorado (Después del Fix)

```
Usuario: [Ya tiene todos los datos completos]
        
Usuario: "Cambiar cédula"
   ↓
Sistema: Detecta comando de cambio
         • Resetea contexto.cedula = None
         • Marca contexto.campo_en_cambio = 'cedula'
         • Retorna intent="informar_cedula"
   ↓
Bot: "¿Cuál es tu número de cédula?"
   ↓
Usuario: "1231234"
   ↓
Sistema: Extrae entidad cedula = "1231234"
         Actualiza contexto.cedula = "1231234"
         ✅ Detecta: campo_en_cambio == 'cedula'
         ✅ Verifica: tiene_datos_completos() == True
         ✅ Genera resumen de confirmación actualizado
         ✅ Limpia campo_en_cambio = None
   ↓
Bot: "📋 Resumen actualizado de tu turno:
      Nombre: Juan
      Cédula: 1231234  ← Actualizada
      Fecha: 2024-01-15
      Hora: 09:00
      Email: juan@example.com
      
      ¿Confirmas estos datos?"
```

## Impacto

✅ **Experiencia de usuario mejorada**: El usuario ahora ve inmediatamente el cambio reflejado
✅ **Flujo más natural**: No hay confusión con preguntas sobre campos ya completos
✅ **Mantiene contexto**: El usuario puede hacer múltiples cambios sin perder el progreso
✅ **Retroalimentación clara**: El resumen muestra explícitamente el cambio realizado

## Fecha de Implementación

Diciembre 2024

## Autor

Fix implementado y documentado por: Sistema de Chatbot TFG V2.0
