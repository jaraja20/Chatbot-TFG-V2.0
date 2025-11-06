# ✅ Validación de Horarios Completos - Sistema de Turnos

## 🎯 Funcionalidad Implementada

El sistema ahora **valida automáticamente** si un horario está lleno cuando el usuario lo selecciona, y **recomienda el siguiente horario disponible**.

---

## 📋 Especificaciones

### Límite de Turnos
- **Máximo**: 2 personas por horario
- **Horarios**: De 07:00 a 15:00, cada 30 minutos
- **Total**: 17 horarios por día (07:00, 07:30, ..., 14:30, 15:00)

### Validación Automática
Cuando un usuario elige un horario:

1. **Verificar disponibilidad en BD**:
   ```sql
   SELECT COUNT(*) FROM turnos 
   WHERE DATE(fecha_hora) = fecha 
   AND TO_CHAR(fecha_hora, 'HH24:MI') = hora
   AND estado = 'activo'
   ```

2. **Si ocupación >= 2**:
   - ❌ Rechazar el horario
   - 🔍 Buscar siguiente horario disponible
   - 💬 Informar al usuario con alternativa

3. **Si ocupación < 2**:
   - ✅ Permitir agendar
   - Continuar flujo normal

---

## 💬 Flujo de Conversación

### Escenario 1: Horario Lleno con Alternativa

```
👤 Usuario: "Quiero turno para mañana a las 09:00"

🔍 Sistema: Verifica disponibilidad
    - 09:00: 2/2 personas (LLENO)
    - 09:30: 1/2 personas (DISPONIBLE)

🤖 Bot: 
"⚠️ Lo siento, el horario 09:00 ya está completo (2 personas agendadas).

🌟 Te recomiendo el siguiente horario disponible: **09:30**

Otros horarios disponibles: 09:30, 10:00, 10:30, 11:00, 11:30

¿Prefieres alguno de estos?"
```

### Escenario 2: Horario Lleno sin Alternativa

```
👤 Usuario: "Para las 14:30"

🔍 Sistema: Verifica disponibilidad
    - 14:30: 2/2 personas (LLENO)
    - 15:00: 2/2 personas (LLENO)
    - No hay más horarios después

🤖 Bot:
"⚠️ Lo siento, el horario 14:30 ya está completo.

❌ No hay más horarios disponibles para el 2025-11-07.

¿Prefieres otro día? Puedes decir 'mañana', 'próxima semana', etc."
```

### Escenario 3: Horario Disponible

```
👤 Usuario: "A las 10:00"

🔍 Sistema: Verifica disponibilidad
    - 10:00: 0/2 personas (DISPONIBLE)

🤖 Bot:
"✅ Perfecto! Turno agendado para 10:00.

¿Cuál es tu email para enviarte la confirmación?"
```

---

## 🔧 Implementación Técnica

### Archivo Modificado
`flask-chatbot/orquestador_inteligente.py`

### Función Principal
`generar_respuesta()` → Intent: `elegir_horario`

### Código Agregado (líneas ~2658-2693)

```python
# 🔥 NUEVO: VALIDAR SI EL HORARIO YA ESTÁ LLENO
if contexto.fecha:
    try:
        disponibilidad = obtener_disponibilidad_real(contexto.fecha)
        ocupacion = disponibilidad.get(contexto.hora, 0)
        
        if ocupacion >= 2:
            # Horario lleno, buscar siguiente disponible
            horarios_disponibles = [h for h, o in sorted(disponibilidad.items()) 
                                    if o < 2 and h > contexto.hora]
            
            contexto.hora = None  # Resetear hora llena
            
            if horarios_disponibles:
                siguiente_horario = horarios_disponibles[0]
                return (
                    f"⚠️ Lo siento, el horario {hora} ya está completo.\n"
                    f"🌟 Te recomiendo: **{siguiente_horario}**\n"
                    f"Otros: {', '.join(horarios_disponibles[:5])}"
                )
            else:
                return (
                    f"⚠️ Horario lleno.\n"
                    f"❌ No hay más horarios para {fecha}.\n"
                    f"¿Prefieres otro día?"
                )
    except Exception as e:
        logger.error(f"Error validando disponibilidad: {e}")
```

---

## 📊 Lógica de Búsqueda

### Algoritmo de Siguiente Horario

```python
# 1. Obtener todos los horarios del día
disponibilidad = obtener_disponibilidad_real(fecha)
# Ejemplo: {'07:00': 2, '07:30': 1, '08:00': 0, '08:30': 2, ...}

# 2. Filtrar disponibles DESPUÉS de la hora solicitada
horarios_disponibles = [
    h for h, ocupacion in sorted(disponibilidad.items()) 
    if ocupacion < 2 and h > hora_solicitada
]
# Resultado: ['08:00', '09:00', '09:30', ...]

# 3. Tomar el primero como recomendación
siguiente = horarios_disponibles[0] if horarios_disponibles else None
```

### Ejemplo Práctico

**Hora solicitada**: 09:00  
**Estado del día**:
```
07:00: 2/2 ❌
07:30: 1/2 ✅ (pero es anterior, no se muestra)
08:00: 2/2 ❌
08:30: 2/2 ❌
09:00: 2/2 ❌ (hora solicitada - LLENA)
09:30: 1/2 ✅ ← RECOMENDADA
10:00: 0/2 ✅
10:30: 1/2 ✅
11:00: 2/2 ❌
...
```

**Bot responde**:
- 🌟 Recomendado: 09:30
- Otros: 09:30, 10:00, 10:30, 11:30, 12:00

---

## 🧪 Testing

### Test 1: Horario Parcialmente Ocupado
```sql
-- Crear 1 turno para 09:00
INSERT INTO turnos (nombre, cedula, fecha_hora, estado) 
VALUES ('Juan', '123', '2025-11-10 09:00:00', 'activo');

-- Usuario intenta 09:00
-- Resultado: ✅ Permitido (1/2)
```

### Test 2: Horario Completo
```sql
-- Crear 2 turnos para 09:00
INSERT INTO turnos (nombre, cedula, fecha_hora, estado) 
VALUES 
    ('Juan', '123', '2025-11-10 09:00:00', 'activo'),
    ('María', '456', '2025-11-10 09:00:00', 'activo');

-- Usuario intenta 09:00
-- Resultado: ❌ Rechazado → Recomienda 09:30
```

### Test 3: Todos los Horarios Llenos
```sql
-- Llenar TODOS los horarios del día (34 turnos = 17 horarios × 2)
-- Usuario intenta cualquier hora
-- Resultado: ❌ Rechazado → Sugiere otro día
```

---

## 📝 Mensajes del Bot

### Variantes de Respuesta

**Caso A: Siguiente horario cercano**
```
⚠️ Lo siento, el horario 09:00 ya está completo (2 personas agendadas).

🌟 Te recomiendo el siguiente horario disponible: **09:30**
```

**Caso B: Varios horarios disponibles**
```
⚠️ Lo siento, el horario 14:00 ya está completo.

🌟 Te recomiendo: **14:30**

Otros horarios disponibles: 14:30, 15:00

¿Prefieres alguno de estos?
```

**Caso C: Sin horarios restantes**
```
⚠️ Lo siento, el horario 14:30 ya está completo.

❌ No hay más horarios disponibles para el 2025-11-10.

¿Prefieres otro día? Puedes decir 'mañana', 'próxima semana', etc.
```

---

## ⚙️ Configuración

### Cambiar Límite de Personas por Turno

Actualmente: **2 personas por turno**

Para cambiar a 3 personas:

```python
# En obtener_disponibilidad_real()
horarios_disponibles = sum(1 for ocupacion in horarios_completos.values() 
                           if ocupacion < 3)  # Cambiar de 2 a 3

# En validación de elegir_horario
if ocupacion >= 3:  # Cambiar de 2 a 3
    # Rechazar horario
```

### Cambiar Rango de Horarios

Actualmente: **07:00 - 15:00**

Para cambiar a 08:00 - 16:00:

```python
# En obtener_disponibilidad_real()
for hora in range(8, 17):  # Cambiar de range(7, 16) a range(8, 17)
    for minuto in [0, 30]:
        if hora == 16 and minuto == 30:  # Ajustar límite superior
            break
```

---

## 🔍 Logs de Debugging

Cuando un horario está lleno, el sistema registra:

```log
WARNING: ⚠️ Horario 09:00 lleno (2/2) para 2025-11-10
INFO: 🔍 Siguiente horario disponible encontrado: 09:30
INFO: 📋 Mostrando 5 alternativas al usuario
```

---

## 🎯 Beneficios

1. **Mejor experiencia de usuario**: No permite seleccionar horarios no disponibles
2. **Optimización automática**: Sugiere inmediatamente la mejor alternativa
3. **Transparencia**: Informa claramente por qué no puede agendar
4. **Gestión inteligente**: Distribuye usuarios en horarios disponibles
5. **Prevención de conflictos**: Evita sobrecarga en la BD

---

## 🚀 Estado

✅ **IMPLEMENTADO Y ACTIVO**  
**Fecha**: 2025-11-06  
**Versión**: orquestador_inteligente.py v3.9  

**Requiere Reinicio**: Sí (watchdog lo hará automáticamente)

---

## 📌 Próximas Mejoras Sugeridas

1. **Notificación de Lista de Espera**: Si horario lleno, ofrecer unirse a lista de espera
2. **Predicción de Ocupación**: "Este horario se llena rápido, te recomiendo agendarNow"
3. **Visualización de Ocupación**: "9:00 (1/2 lugares) - 10:00 (0/2 lugares)"
4. **Smart Suggestions**: Basado en historial, sugerir horarios con menor demanda
5. **Cancelaciones Automáticas**: Liberar horarios si usuario no confirma en X tiempo

---

**Conclusión**: El sistema ahora protege contra sobrecarga de horarios y mejora la experiencia del usuario al sugerir automáticamente alternativas cuando su elección no está disponible. 🎉
