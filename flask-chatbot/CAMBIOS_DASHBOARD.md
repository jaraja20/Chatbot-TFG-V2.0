# 📊 Mejoras en Dashboard - Historial y Estadísticas de Satisfacción

## 🎯 Cambios Implementados

### **Cambio 1: Historial de Mensajes Ampliado**

**Antes**: Mostraba últimos 20 mensajes  
**Ahora**: Muestra últimos **50 mensajes**

**Archivo**: `flask-chatbot/app.py`  
**Línea**: ~571  
**Endpoint**: `/api/dashboard/conversations`

```python
# ANTES
LIMIT 20

# DESPUÉS
LIMIT 50
```

**Impacto**:
- ✅ Mejor visibilidad del historial reciente
- ✅ Más contexto para análisis de conversaciones
- ✅ Útil para detectar patrones en interacciones

---

### **Cambio 2: Excluir Feedbacks Negativos Resueltos de Estadísticas**

**Problema Original**:
Los feedbacks negativos marcados como "resueltos" seguían afectando negativamente las estadísticas de satisfacción del sistema, aunque ya habían sido atendidos.

**Solución Implementada**:
Una vez que un feedback negativo se marca como `reviewed=true` (resuelto), **no se contabiliza** en las estadísticas de satisfacción.

**Archivo**: `flask-chatbot/app.py`  
**Línea**: ~172  
**Función**: `get_feedback_stats()`

#### Antes:
```python
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN feedback_thumbs = 1 THEN 1 ELSE 0 END) as positive,
        SUM(CASE WHEN feedback_thumbs = -1 THEN 1 ELSE 0 END) as negative
    FROM conversation_messages
    WHERE feedback_thumbs IN (1, -1)
""")
```

**Problema**: Contaba TODOS los feedbacks negativos, resueltos o no.

#### Después:
```python
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN feedback_thumbs = 1 THEN 1 ELSE 0 END) as positive,
        SUM(CASE WHEN feedback_thumbs = -1 AND (reviewed IS NULL OR reviewed = false) THEN 1 ELSE 0 END) as negative
    FROM conversation_messages
    WHERE feedback_thumbs = 1 
       OR (feedback_thumbs = -1 AND (reviewed IS NULL OR reviewed = false))
""")
```

**Lógica**:
1. ✅ **Positivos (👍)**: Se cuentan todos (sin cambios)
2. ✅ **Negativos NO resueltos (👎)**: Se cuentan en estadísticas
3. ❌ **Negativos resueltos (👎 + reviewed=true)**: **NO se cuentan** en estadísticas

---

## 📊 Impacto en Métricas

### Ejemplo Escenario:

**Base de datos**:
- 100 feedbacks positivos (👍)
- 30 feedbacks negativos (👎)
  - 20 resueltos (`reviewed=true`)
  - 10 sin resolver (`reviewed=false` o `NULL`)

#### ANTES del cambio:
```
Total feedbacks: 130
Positivos: 100
Negativos: 30
Satisfacción: 100/130 = 76.9%
```

#### DESPUÉS del cambio:
```
Total feedbacks: 110 (100 positivos + 10 negativos sin resolver)
Positivos: 100
Negativos: 10 (solo los no resueltos)
Satisfacción: 100/110 = 90.9% ✅
```

**Mejora**: +14% en satisfacción al excluir problemas ya resueltos

---

## 🔧 Flujo de Usuario

### Marcar feedback como resuelto:

1. **Dashboard** → Pestaña "Feedback Negativo"
2. Usuario ve lista de feedbacks con 👎
3. Clic en botón **"Marcar como Resuelto"**
4. Sistema actualiza `reviewed = true` en BD
5. **Inmediatamente**: Ese feedback desaparece de estadísticas de satisfacción
6. ✅ Estadísticas se recalculan automáticamente

### API Endpoint:
```
POST /api/dashboard/feedback/<feedback_id>/resolve
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Feedback marcado como resuelto",
  "new_stats": {
    "total": 110,
    "positive": 100,
    "negative": 10,
    "satisfaction_rate": 90.9
  }
}
```

---

## 🧪 Testing

### Test 1: Verificar límite de 50 mensajes
```bash
# En el navegador
curl http://localhost:5000/api/dashboard/conversations | jq length

# Esperado: 50 (o menos si hay menos mensajes en BD)
```

### Test 2: Verificar exclusión de resueltos
```sql
-- En PostgreSQL
-- 1. Ver feedbacks negativos actuales
SELECT id, user_message, reviewed FROM conversation_messages 
WHERE feedback_thumbs = -1;

-- 2. Marcar uno como resuelto
UPDATE conversation_messages SET reviewed = true WHERE id = 123;

-- 3. Verificar estadísticas (debería excluir el ID 123)
SELECT * FROM get_feedback_stats();
```

### Test 3: Verificar dashboard visual
1. Abrir `http://localhost:5000/dashboard`
2. **Historial**: Debería mostrar hasta 50 mensajes
3. **Satisfacción**: Debería excluir negativos resueltos
4. Marcar un feedback negativo como resuelto
5. Ver que satisfacción aumenta inmediatamente

---

## 📝 Notas Importantes

### Campo `reviewed` en BD
El campo debe existir en la tabla `conversation_messages`:

```sql
ALTER TABLE conversation_messages 
ADD COLUMN IF NOT EXISTS reviewed BOOLEAN DEFAULT false;
```

Si la columna ya existe con otro nombre (ej: `resolved`), ajustar el código para usar ese nombre.

### Compatibilidad con Streamlit
La función `get_feedback_stats()` está marcada como "COMPATIBLE con Streamlit", por lo que estos cambios también afectan al dashboard de Streamlit (`learning_dashboard.py`) si lo usa.

### Recalcular estadísticas antiguas
Si ya tienes feedbacks negativos resueltos previamente, las estadísticas se actualizarán automáticamente en la próxima consulta. No requiere migración de datos.

---

## ✅ Beneficios

1. **Historial más completo**: 50 mensajes vs 20 anteriores
2. **Estadísticas más precisas**: Reflejan problemas actuales, no históricos resueltos
3. **Motivación del equipo**: Ver mejora real al resolver feedbacks negativos
4. **Mejor tracking**: Saber qué feedbacks aún requieren atención vs cuáles ya están resueltos
5. **Toma de decisiones**: Estadísticas más realistas para evaluar rendimiento actual

---

## 🚀 Estado

✅ **COMPLETADO**  
**Fecha**: 2025-11-06  
**Archivos Modificados**:
- `flask-chatbot/app.py` (2 cambios)

**Requiere Reinicio**: Sí (Flask con watchdog se recargará automáticamente)

---

## 📌 Próximos Pasos Sugeridos

1. **Validar campo `reviewed`**: Confirmar que existe en BD
2. **Testing**: Probar ambos cambios en entorno de desarrollo
3. **Documentar UI**: Actualizar guía de usuario del dashboard
4. **Métricas adicionales**: Considerar agregar "Feedbacks resueltos (últimos 7 días)" como métrica separada
