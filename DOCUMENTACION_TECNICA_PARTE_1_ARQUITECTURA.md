# 📘 DOCUMENTACIÓN TÉCNICA DEL SISTEMA - PARTE 1: ARQUITECTURA Y COMPONENTES

## 📋 Índice de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura General del Sistema](#arquitectura-general-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Motor de Razonamiento Difuso](#motor-de-razonamiento-difuso)
5. [Sistema de Corrección Ortográfica](#sistema-de-corrección-ortográfica)
6. [Detección de Oraciones Compuestas](#detección-de-oraciones-compuestas)
7. [Pipeline de Procesamiento](#pipeline-de-procesamiento)
8. [Flujos de Datos](#flujos-de-datos)

---

## 1. Resumen Ejecutivo

### 1.1 Descripción General

Sistema de chatbot inteligente para la gestión de turnos de trámites de cédula de identidad en Paraguay. Implementa técnicas avanzadas de procesamiento de lenguaje natural (NLP) con énfasis en razonamiento difuso, corrección ortográfica automática y manejo de consultas complejas.

### 1.2 Características Principales

- ✅ **Clasificación de Intents** mediante lógica difusa (90% precisión)
- ✅ **Corrección Ortográfica Automática** con FuzzyWuzzy (85% precisión)
- ✅ **Detección de Oraciones Compuestas** (80% precisión)
- ✅ **Validación de Cédulas Paraguayas** (95% precisión)
- ✅ **Detección de Urgencia** (100% precisión)
- ✅ **Gestión Completa de Conversaciones** con contexto persistente
- ✅ **Rendimiento Optimizado** (<100ms por consulta)

### 1.3 Métricas de Rendimiento Globales

| Métrica | Valor |
|---------|-------|
| **Puntuación Global del Sistema** | 93.75% |
| **Casos Totales Evaluados** | 165 |
| **Casos Exitosos** | 152 |
| **Tasa de Éxito Global** | 92.12% |
| **Tiempo Promedio de Respuesta** | 39ms |
| **Componentes Aprobados** | 8/8 (100%) |

---

## 2. Arquitectura General del Sistema

### 2.1 Diagrama de Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                        USUARIO FINAL                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  Frontend   │  │ API REST     │  │  WebSocket/SSE      │   │
│  │  (HTML/JS)  │  │  (Flask)     │  │  (Tiempo Real)      │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE LÓGICA DE NEGOCIO                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         ORQUESTADOR INTELIGENTE (orquestador.py)         │  │
│  │  • Gestión de sesiones                                   │  │
│  │  • Control de flujo conversacional                       │  │
│  │  • Coordinación de componentes                           │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                          │
│       ┌───────────────┼───────────────┬────────────────┐        │
│       ▼               ▼               ▼                ▼        │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │Clasificd│   │Corrector │   │Detector  │   │Validador │     │
│  │ Intent  │   │Ortográf. │   │Oraciones │   │ Datos    │     │
│  │(Fuzzy)  │   │(FuzzyW.) │   │Compuestas│   │          │     │
│  └─────────┘   └──────────┘   └──────────┘   └──────────┘     │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAPA DE PERSISTENCIA                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  Base de     │  │  Contexto de │  │  Sistema de         │  │
│  │  Datos       │  │  Sesiones    │  │  Notificaciones     │  │
│  │  (SQLite)    │  │  (Memoria)   │  │  (Email/WhatsApp)   │  │
│  └──────────────┘  └──────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Stack Tecnológico

#### **Backend**
- **Lenguaje**: Python 3.8+
- **Framework Web**: Flask 2.x
- **NLP/ML**: 
  - Lógica Difusa personalizada
  - FuzzyWuzzy + python-Levenshtein
  - NumPy para cálculos matriciales
  - Matplotlib para visualizaciones

#### **Frontend**
- **HTML5/CSS3/JavaScript**
- **AJAX** para comunicación asíncrona
- **Bootstrap** para diseño responsive

#### **Base de Datos**
- **SQLite** para almacenamiento persistente
- **Estructura optimizada** con índices para turnos y usuarios

#### **Notificaciones**
- **SMTP** para emails
- **Twilio** para WhatsApp (opcional)

---

## 3. Componentes Principales

### 3.1 Tabla de Componentes

| # | Componente | Responsabilidad | Archivo Principal | Precisión |
|---|------------|-----------------|-------------------|-----------|
| 1 | Clasificador de Intents | Identificar la intención del usuario | `razonamiento_difuso.py` | 90% |
| 2 | Corrector Ortográfico | Corregir errores de escritura | `mejoras_fuzzy.py` | 85% |
| 3 | Detector Oraciones Compuestas | Manejar consultas múltiples | `mejoras_fuzzy.py` | 80% |
| 4 | Validador de Cédulas | Validar formato paraguayo | `orquestador_inteligente.py` | 95% |
| 5 | Normalizador de Nombres | Capitalizar nombres correctamente | `orquestador_inteligente.py` | 100% |
| 6 | Detector de Urgencia | Identificar solicitudes urgentes | `orquestador_inteligente.py` | 100% |
| 7 | Gestor de Contexto | Mantener estado conversacional | `orquestador_inteligente.py` | 100% |
| 8 | Sistema de Testing | Validación exhaustiva del sistema | `test_exhaustivo_sistema.py` | 100% |

### 3.2 Desglose Detallado por Componente

#### **3.2.1 Clasificador de Intents (Motor Difuso)**

**Ubicación**: `flask-chatbot/razonamiento_difuso.py`

**Propósito**: Clasificar la intención del usuario utilizando lógica difusa, permitiendo manejar ambigüedad e incertidumbre en el lenguaje natural.

**Intents Soportados**:
1. `agendar_turno` - Solicitud de nuevo turno
2. `consultar_disponibilidad` - Consulta de horarios disponibles
3. `consultar_costo` - Pregunta sobre precios
4. `consultar_requisitos` - Pregunta sobre documentos necesarios
5. `consultar_ubicacion` - Pregunta sobre dirección/contacto
6. `consultar_tramites` - Pregunta sobre servicios disponibles
7. `elegir_horario` - Selección de hora específica
8. `affirm` - Confirmación (sí/ok/confirmo)
9. `negacion` - Negación (no/no me sirve)
10. `cancelar` - Cancelación de turno
11. `frase_ambigua` - Frases que requieren clarificación

**Algoritmo de Clasificación**:

```python
def clasificar(mensaje: str) -> (intent: str, confianza: float):
    1. Preprocesar mensaje (lowercase, tokenización)
    2. Para cada intent:
       a. Calcular membresía difusa por nivel (alta/media/baja)
       b. Aplicar pesos (alta=1.0, media=0.6, baja=0.3)
       c. Sumar scores ponderados
    3. Normalizar scores (0-1)
    4. Seleccionar intent con mayor score
    5. Si score < threshold (0.3), retornar nlu_fallback
    6. Retornar (intent, confianza)
```

**Ejemplo de Funcionamiento**:

```
Input: "quiero un turno para mañana"

Análisis Difuso:
  agendar_turno:
    - "quiero" → alta (1.0)
    - "turno" → alta (1.0)
    - "para" → media (0.6)
    Total: 2.6 / 3 palabras = 0.87 → 87%
  
  consultar_disponibilidad:
    - "mañana" → media (0.6)
    - "para" → media (0.6)
    Total: 1.2 / 3 palabras = 0.40 → 40%

Output: (intent="agendar_turno", confianza=0.87)
```

**Palabras Clave por Intent** (muestra):

```python
FUZZY_KEYWORDS = {
    'agendar_turno': {
        'alta': ['quiero', 'necesito', 'agendar', 'sacar', 'reservar', 'turno'],
        'media': ['para', 'dame', 'porfavor', 'hora'],
        'baja': ['podria', 'quisiera', 'che']
    },
    'consultar_disponibilidad': {
        'alta': ['cuando', 'disponible', 'horarios', 'hay', 'hueco', 'libre'],
        'media': ['puedo', 'hoy', 'mañana', 'tarde'],
        'baja': ['dia', 'semana', 'mejor']
    },
    # ... más intents
}
```

---

#### **3.2.2 Corrector Ortográfico**

**Ubicación**: `flask-chatbot/mejoras_fuzzy.py` - Clase `CorrectOrOrtografico`

**Propósito**: Corregir automáticamente errores ortográficos para mejorar la precisión de clasificación.

**Tecnología Utilizada**: 
- **FuzzyWuzzy** - Algoritmo de distancia de Levenshtein
- **python-Levenshtein** - Implementación optimizada en C

**Proceso de Corrección**:

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRADA: "kiero un turno para mañana"                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Tokenización                                       │
│  Tokens: ["kiero", "un", "turno", "para", "mañana"]        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: Verificación de cada token                         │
│                                                              │
│  "kiero":                                                    │
│    ├─ ¿Está en correcciones_manuales? → SÍ → "quiero"      │
│    └─ (Mapeo directo kiero→quiero)                         │
│                                                              │
│  "un":                                                       │
│    ├─ ¿Está en diccionario_base? → NO                      │
│    ├─ Buscar similar en diccionario (umbral 75%)           │
│    └─ No hay match suficiente → mantener "un"              │
│                                                              │
│  "turno":                                                    │
│    └─ ¿Está en diccionario_base? → SÍ → mantener           │
│                                                              │
│  "para":                                                     │
│    └─ ¿Está en diccionario_base? → SÍ → mantener           │
│                                                              │
│  "mañana":                                                   │
│    └─ ¿Está en diccionario_base? → SÍ → mantener           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: Reconstrucción                                     │
│  Tokens corregidos: ["quiero", "un", "turno", "para",      │
│                      "mañana"]                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  SALIDA: "quiero un turno para mañana"                      │
│  Correcciones: ["kiero → quiero"]                           │
└─────────────────────────────────────────────────────────────┘
```

**Diccionario de Correcciones Manuales** (muestra):

```python
correcciones_manuales = {
    'kiero': 'quiero',
    'nesecito': 'necesito',
    'bale': 'vale',
    'kuando': 'cuando',
    'rekisitos': 'requisitos',
    'disponivilidad': 'disponibilidad',
    'perfekto': 'perfecto',
    'konfirmo': 'confirmo',
    'k': 'que',
    'q': 'que',
    'xfa': 'favor',
    'tmb': 'tambien',
    # ... 30+ correcciones
}
```

**Diccionario Base** (60+ palabras clave):
- Verbos: quiero, necesito, puedo, tengo, debo, hay, tienen, etc.
- Sustantivos: turno, cita, hora, dia, cedula, documento, precio, etc.
- Interrogativos: cuando, donde, como, cuanto, que, cual
- Temporales: hoy, mañana, lunes, martes, semana, etc.

**Métricas de Rendimiento**:
- **Precisión**: 85% (17/20 casos correctos)
- **Umbral de similitud**: 75%
- **Tiempo promedio**: 0.20ms por corrección
- **Mejora respecto al sistema base**: +50%

---

#### **3.2.3 Detector de Oraciones Compuestas**

**Ubicación**: `flask-chatbot/mejoras_fuzzy.py` - Clase `DetectorOracionesCompuestas`

**Propósito**: Identificar y procesar correctamente mensajes con múltiples intenciones o consultas complejas.

**Estrategias Implementadas**:

##### **A) Fragmentación por Conectores**

Detecta conectores que indican múltiples consultas:

```python
conectores = [
    r'\s+y\s+',        # "cuanto cuesta y que documentos"
    r'\s*,\s*',        # "hola, quiero turno"
    r'\s+pero\s+',     # "quiero turno pero solo tarde"
    r'\s+entonces\s+', # "bueno, entonces cuando hay"
    r'\s+ademas\s+',   # "necesito saber ademas donde"
    r'\s+tambien\s+',  # "quiero saber tambien cuando"
]
```

**Ejemplo de Fragmentación**:

```
Input: "cuanto sale y que documentos necesito?"

PASO 1: Detectar conector "y"
  ↓
Fragmento 1: "cuanto sale"
Fragmento 2: "que documentos necesito"

PASO 2: Clasificar cada fragmento
  Fragmento 1 → consultar_costo (0.80)
  Fragmento 2 → consultar_requisitos (0.67)

PASO 3: Seleccionar el de mayor confianza
  Output: (intent="consultar_costo", confianza=0.80)
```

##### **B) Priorización por Palabras Clave**

Patrones regex que dan prioridad a intents específicos según palabras iniciales:

```python
patrones_prioritarios = {
    'consultar_costo': [
        r'^(cuanto|precio|costo|vale)',
        r'(caro|barato|cuesta|plata)'
    ],
    'consultar_disponibilidad': [
        r'^(cuando|que dia|que hora)',
        r'(disponible|hay|atienden|cierran)'
    ],
    'consultar_requisitos': [
        r'^(que necesito|que documentos)',
        r'(llevar|traer|presentar)'
    ],
    'consultar_ubicacion': [
        r'^(donde|como llego)',
        r'(llegar|quedan|lejos|cerca)'
    ],
    'agendar_turno': [
        r'^(quiero|necesito).*(turno|cita)',
        r'(sacar turno|agendar|reservar)'
    ]
}
```

**Ejemplo de Priorización**:

```
Input: "cuanto cuesta y cuando puedo ir?"

PASO 1: Detectar fragmentos
  Fragmento 1: "cuanto cuesta"
  Fragmento 2: "cuando puedo ir"

PASO 2: Detectar intent prioritario
  Patron r'^(cuanto|precio)' → MATCH
  Intent prioritario: consultar_costo

PASO 3: Clasificar mensaje completo
  consultar_costo detectado con patrón inicial
  ↓
  Boost de confianza: 0.65 * 1.3 = 0.85

Output: (intent="consultar_costo", confianza=0.85)
```

##### **C) Boost de Confianza**

Cuando se detecta palabra clave prioritaria y el intent clasificado coincide:

```python
if intent_detectado == intent_clasificado:
    confianza_final = min(confianza_base * 1.3, 1.0)  # Boost 30%
else:
    # Forzar el intent prioritario si hay match claro
    intent = intent_prioritario
    confianza = 0.75
```

**Casos de Uso Exitosos**:

| Mensaje | Método | Resultado |
|---------|--------|-----------|
| "necesito un turno para el lunes, hay disponible?" | Priorización | `consultar_disponibilidad` ✅ |
| "cuanto sale y que documentos necesito?" | Priorización | `consultar_costo` ✅ |
| "quiero agendar pero solo puedo tarde" | Fragmentación + Boost | `agendar_turno` ✅ |
| "bueno, entonces, que horarios hay?" | Fragmentación | `consultar_disponibilidad` ✅ |

**Métricas de Rendimiento**:
- **Precisión**: 80% (20/25 casos correctos)
- **Tiempo promedio**: 1.32ms por clasificación
- **Mejora respecto al sistema base**: +16%

---

#### **3.2.4 Validador de Cédulas Paraguayas**

**Ubicación**: `flask-chatbot/orquestador_inteligente.py`

**Propósito**: Validar que las cédulas de identidad cumplan el formato paraguayo estándar.

**Formato Válido**: 
- 6-8 dígitos numéricos
- Con o sin puntos separadores
- Ejemplos: `1234567`, `1.234.567`, `12345678`

**Algoritmo de Validación**:

```python
def validar_cedula(cedula: str) -> bool:
    # 1. Limpiar formato (remover puntos, guiones, espacios)
    cedula_limpia = re.sub(r'[.\-\s]', '', cedula)
    
    # 2. Verificar que sea solo dígitos
    if not cedula_limpia.isdigit():
        return False
    
    # 3. Verificar longitud (6-8 dígitos)
    if len(cedula_limpia) < 6 or len(cedula_limpia) > 8:
        return False
    
    return True
```

**Casos de Prueba**:

| Cédula | Válida | Motivo |
|--------|--------|--------|
| `1234567` | ✅ | Formato correcto (7 dígitos) |
| `1.234.567` | ✅ | Con puntos (válido) |
| `123456` | ✅ | Mínimo válido (6 dígitos) |
| `12345678` | ✅ | Máximo válido (8 dígitos) |
| `12345` | ❌ | Muy corta (< 6 dígitos) |
| `123456789` | ❌ | Muy larga (> 8 dígitos) |
| `12-34-56` | ❌ | Formato incorrecto (solo 4+2) |
| `abc1234` | ❌ | Contiene letras |

**Precisión**: 95% (19/20 casos correctos)

---

#### **3.2.5 Normalizador de Nombres**

**Ubicación**: `flask-chatbot/orquestador_inteligente.py`

**Propósito**: Capitalizar correctamente nombres propios para consistencia en la base de datos.

**Algoritmo**:

```python
def normalizar_nombre(nombre: str) -> str:
    # 1. Limpiar espacios múltiples
    nombre = re.sub(r'\s+', ' ', nombre.strip())
    
    # 2. Capitalizar cada palabra
    # title() capitaliza la primera letra de cada palabra
    nombre_normalizado = nombre.title()
    
    # 3. Manejar casos especiales (O'Connor, Jean-Paul, etc.)
    # Mantener apóstrofes y guiones
    
    return nombre_normalizado
```

**Ejemplos**:

| Input | Output |
|-------|--------|
| `"juan perez"` | `"Juan Perez"` |
| `"MARIA GARCIA"` | `"Maria Garcia"` |
| `"pedro  luis   gomez"` | `"Pedro Luis Gomez"` |
| `"  ana  maria  "` | `"Ana Maria"` |
| `"o'connor"` | `"O'Connor"` |
| `"jean-paul"` | `"Jean-Paul"` |
| `"maría josé"` | `"María José"` |

**Precisión**: 100% (15/15 casos correctos)

---

#### **3.2.6 Detector de Urgencia**

**Ubicación**: `flask-chatbot/orquestador_inteligente.py`

**Propósito**: Identificar solicitudes que requieren atención prioritaria.

**Palabras Clave de Urgencia**:

```python
URGENCIA_KEYWORDS = [
    'urgente', 'urgencia', 'apurado', 'apurada', 'rapido', 'rápido',
    'ya', 'ahora', 'hoy', 'cuanto antes', 'lo antes posible',
    'necesito ya', 'ahora mismo', 'pronto', 'inmediato'
]
```

**Algoritmo**:

```python
def detectar_urgencia(mensaje: str) -> bool:
    mensaje_lower = mensaje.lower()
    
    for keyword in URGENCIA_KEYWORDS:
        if keyword in mensaje_lower:
            return True
    
    return False
```

**Ejemplos**:

| Mensaje | Urgente | Keyword |
|---------|---------|---------|
| `"necesito turno urgente"` | ✅ | "urgente" |
| `"quiero ir hoy mismo"` | ✅ | "hoy" |
| `"estoy apurado, cuando puedo?"` | ✅ | "apurado" |
| `"necesito ya el turno"` | ✅ | "ya" |
| `"quiero un turno para mañana"` | ❌ | — |
| `"cuando hay disponible?"` | ❌ | — |

**Precisión**: 100% (20/20 casos correctos)

---

## 4. Motor de Razonamiento Difuso

### 4.1 Fundamentos de Lógica Difusa

La lógica difusa permite manejar la incertidumbre inherente al lenguaje natural, donde las categorías no son binarias sino graduales.

**Concepto Clave**: Una palabra no pertenece 100% a un intent, sino que tiene un **grado de pertenencia** (membresía) entre 0 y 1.

### 4.2 Funciones de Pertenencia

Cada palabra clave tiene un grado de pertenencia según su importancia:

```
┌─────────────────────────────────────────────────────┐
│  NIVELES DE PERTENENCIA                             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ALTA (peso = 1.0)                                  │
│  ████████████████████████████ 100%                  │
│  Palabras clave principales                         │
│  Ej: "turno", "quiero", "necesito"                  │
│                                                      │
│  MEDIA (peso = 0.6)                                 │
│  █████████████████ 60%                              │
│  Palabras de apoyo                                  │
│  Ej: "para", "dame", "hora"                         │
│                                                      │
│  BAJA (peso = 0.3)                                  │
│  █████████ 30%                                      │
│  Palabras contextuales                              │
│  Ej: "che", "podria", "quisiera"                    │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 4.3 Cálculo de Membresía Difusa

**Fórmula**:

```
Para un mensaje M con palabras {w1, w2, ..., wn}
Para un intent I:

membership(M, I) = Σ(peso_palabra_i) / total_palabras_mensaje

Donde:
  peso_palabra_i = {
    1.0  si palabra_i está en keywords_alta[I]
    0.6  si palabra_i está en keywords_media[I]
    0.3  si palabra_i está en keywords_baja[I]
    0.0  si palabra_i no está en keywords[I]
  }
```

**Ejemplo Detallado**:

```
Mensaje: "quiero un turno para mañana"
Palabras: ["quiero", "un", "turno", "para", "mañana"]

Para intent "agendar_turno":
  "quiero" → ALTA → 1.0
  "un"     → (no encontrada) → 0.0
  "turno"  → ALTA → 1.0
  "para"   → MEDIA → 0.6
  "mañana" → (no en este intent) → 0.0
  
  Total = 1.0 + 0.0 + 1.0 + 0.6 + 0.0 = 2.6
  Membresía = 2.6 / 5 palabras = 0.52 → 52%

Para intent "consultar_disponibilidad":
  "quiero" → (no encontrada) → 0.0
  "un"     → (no encontrada) → 0.0
  "turno"  → ALTA → 1.0
  "para"   → MEDIA → 0.6
  "mañana" → MEDIA → 0.6
  
  Total = 0.0 + 0.0 + 1.0 + 0.6 + 0.6 = 2.2
  Membresía = 2.2 / 5 palabras = 0.44 → 44%

RESULTADO: agendar_turno (52% > 44%)
```

### 4.4 Normalización y Selección

```python
def seleccionar_intent(memberships: Dict[str, float]) -> (str, float):
    # 1. Encontrar la membresía máxima
    max_membership = max(memberships.values())
    
    # 2. Verificar threshold mínimo
    if max_membership < 0.3:
        return ("nlu_fallback", max_membership)
    
    # 3. Seleccionar intent con mayor membresía
    intent_seleccionado = max(memberships, key=memberships.get)
    
    return (intent_seleccionado, max_membership)
```

### 4.5 Ventajas de la Lógica Difusa

1. **Manejo de Ambigüedad**: Permite palabras con significados múltiples
2. **Robustez**: No requiere match exacto de patrones
3. **Transparencia**: El scoring es explicable y auditable
4. **Adaptabilidad**: Fácil agregar nuevas palabras clave
5. **Eficiencia**: Cálculo rápido sin modelos complejos

---

## 5. Sistema de Corrección Ortográfica

### 5.1 Algoritmo de Levenshtein

**Definición**: Mide la distancia entre dos cadenas como el mínimo número de operaciones (inserción, eliminación, sustitución) necesarias para transformar una en la otra.

**Ejemplo**:

```
Distancia("kiero", "quiero") = 1 operación
  kiero
  ↓ (sustituir k → q)
  quiero

Similitud = 1 - (distancia / max_length)
         = 1 - (1 / 6) 
         = 0.833 → 83.3%
```

### 5.2 Proceso de Matching

```
┌──────────────────────────────────────────────────────────┐
│  Palabra a corregir: "nesecito"                          │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  Calcular similitud con todas las palabras del          │
│  diccionario (60+ palabras)                              │
│                                                           │
│  "necesito"  → similitud: 88% ✅ (1 char diferente)     │
│  "nesecito"  → similitud: 100% (pero no está)            │
│  "quiero"    → similitud: 43%                            │
│  "puedo"     → similitud: 29%                            │
│  ...                                                      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  Seleccionar match con mayor similitud                   │
│  y que supere el umbral (75%)                            │
│                                                           │
│  Mejor match: "necesito" (88% ≥ 75%) ✅                 │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  Reemplazar: "nesecito" → "necesito"                     │
└──────────────────────────────────────────────────────────┘
```

### 5.3 Optimizaciones Implementadas

#### **A) Caché de Correcciones Manuales**

```python
# Consulta O(1) antes de calcular distancia O(n*m)
if palabra in correcciones_manuales:
    return correcciones_manuales[palabra]
```

Evita cálculos para los 30+ errores más comunes.

#### **B) Skip de Palabras Correctas**

```python
# Si la palabra ya está en el diccionario, no corregir
if palabra in diccionario_base:
    return palabra
```

Reduce tiempo de procesamiento en ~60% de casos.

#### **C) Umbral Ajustable**

```python
# Umbral más bajo para palabras cortas
umbral = 70 if len(palabra) <= 4 else 75
```

Mejora precisión en palabras como "k" → "que".

### 5.4 Casos Especiales

#### **Preservación de Puntuación**

```python
"hola!" → procesar "hola" → "hola" → "hola!"
"cuanto?" → procesar "cuanto" → "cuanto" → "cuanto?"
```

#### **Palabras Desconocidas**

Si no hay match con ≥75% similitud, se mantiene la palabra original:

```python
"xyz123" → sin match → mantener "xyz123"
```

---

## 6. Detección de Oraciones Compuestas

### 6.1 Tipos de Oraciones Compuestas

#### **Tipo 1: Consultas Múltiples**

```
"cuanto sale y que documentos necesito?"
     ↓              ↓
consultar_costo  consultar_requisitos
```

**Estrategia**: Priorizar el primer intent detectado o el de mayor confianza.

#### **Tipo 2: Agendar con Condiciones**

```
"quiero turno pero solo puedo por la tarde"
      ↓                      ↓
agendar_turno          restricción temporal
```

**Estrategia**: Identificar intent principal y extraer condiciones como contexto.

#### **Tipo 3: Consultas Indirectas**

```
"trabajo hasta las 6, ustedes cierran a esa hora?"
              ↓                    ↓
        contexto personal   consultar_disponibilidad
```

**Estrategia**: Buscar interrogativos ("cierran", "hora") para identificar la consulta real.

### 6.2 Flujo de Procesamiento

```
┌─────────────────────────────────────────────────────┐
│  INPUT: "cuanto sale y que documentos necesito?"    │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ ¿Es compuesta?      │
         │ (detectar "y", ",") │
         └──────┬──────┬───────┘
                │      │
            NO  │      │  SI
                │      │
                ▼      ▼
    ┌─────────────┐  ┌──────────────────────────────┐
    │Clasificación│  │ PROCESAMIENTO COMPUESTO:     │
    │   Simple    │  │                              │
    └─────────────┘  │ 1. Dividir por conectores   │
                     │    Fragmento 1: "cuanto sale"│
                     │    Fragmento 2: "que docs"   │
                     │                              │
                     │ 2. Detectar prioridad        │
                     │    Patrón r'^cuanto' → MATCH │
                     │    Priority: consultar_costo │
                     │                              │
                     │ 3. Clasificar fragmentos     │
                     │    F1 → costo (0.80)        │
                     │    F2 → requisitos (0.67)    │
                     │                              │
                     │ 4. Seleccionar resultado     │
                     │    IF priority MATCH:        │
                     │      boost confianza         │
                     │    ELSE:                     │
                     │      max(confianzas)         │
                     └──────────────────────────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ OUTPUT:              │
                     │ intent: costo        │
                     │ confianza: 0.80      │
                     │ metadata: compuesta  │
                     └──────────────────────┘
```

### 6.3 Métodos de Clasificación

#### **Método 1: Priorización Contextual**

Usado cuando hay palabra clave inicial clara:

```python
if detect_priority_pattern(mensaje):
    intent = get_priority_intent(mensaje)
    confianza = clasificar_base(mensaje) * 1.3  # Boost
    metadata['metodo'] = 'priorizacion_contextual'
```

**Tasa de éxito**: 95% (19/20 casos)

#### **Método 2: Fragmentación Múltiple**

Usado cuando no hay prioridad clara:

```python
fragmentos = dividir_por_conectores(mensaje)
resultados = []
for f in fragmentos:
    if len(f.split()) >= 2:
        intent, conf = clasificar_base(f)
        resultados.append((intent, conf))

# Seleccionar el de mayor confianza
mejor = max(resultados, key=lambda x: x[1])
metadata['metodo'] = 'fragmentacion_multiple'
```

**Tasa de éxito**: 75% (15/20 casos)

### 6.4 Patrones Regex de Priorización

```python
# Ejemplo de patrones para consultar_costo
patrones_prioritarios['consultar_costo'] = [
    r'^(cuanto|cuánto|precio|costo|vale|bale|sale)',
    r'(caro|barato|cuesta|cobran|pagar|plata|dinero)',
]

# Uso:
mensaje = "cuanto cuesta y cuando puedo ir?"
for patron in patrones_prioritarios['consultar_costo']:
    if re.search(patron, mensaje.lower()):
        return 'consultar_costo'  # Prioridad detectada
```

---

## 7. Pipeline de Procesamiento

### 7.1 Flujo Completo de un Mensaje

```
┌────────────────────────────────────────────────────────┐
│  FASE 1: ENTRADA                                       │
│  Usuario envía: "kiero un turno para mañana"          │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  FASE 2: PREPROCESAMIENTO                              │
│  • Corrección ortográfica                              │
│    "kiero" → "quiero"                                  │
│  • Mensaje corregido: "quiero un turno para mañana"   │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  FASE 3: DETECCIÓN DE COMPLEJIDAD                      │
│  • ¿Es oración compuesta? → NO                         │
│  • Método: Clasificación simple                        │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  FASE 4: CLASIFICACIÓN DE INTENT                       │
│  • Motor difuso calcula membresías:                    │
│    - agendar_turno: 0.67                               │
│    - consultar_disponibilidad: 0.44                    │
│    - ...otros intents                                  │
│  • Intent seleccionado: agendar_turno (0.67)          │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  FASE 5: EXTRACCIÓN DE ENTIDADES                       │
│  • Detectar fecha: "mañana" → fecha calculada          │
│  • Detectar urgencia: NO                               │
│  • Contexto actualizado                                │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  FASE 6: GENERACIÓN DE RESPUESTA                       │
│  • Consultar disponibilidad para mañana                │
│  • Formatear opciones de horarios                      │
│  • Construir mensaje de respuesta                      │
└────────────┬───────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  FASE 7: SALIDA                                        │
│  Bot responde: "Para mañana tengo disponible:         │
│  - 09:00 AM                                            │
│  - 14:00 PM                                            │
│  ¿Cuál prefieres?"                                     │
└────────────────────────────────────────────────────────┘
```

### 7.2 Gestión de Contexto de Sesión

```python
contexto_sesion = {
    'session_id': 'unique_id_12345',
    'intent_actual': 'agendar_turno',
    'estado': 'esperando_fecha',
    'datos_temporales': {
        'nombre': None,
        'cedula': None,
        'email': None,
        'fecha': 'mañana',
        'hora': None,
        'urgente': False
    },
    'historial': [
        {'usuario': 'quiero un turno', 'bot': 'Para cuándo?'},
        {'usuario': 'mañana', 'bot': 'Horarios disponibles...'}
    ],
    'timestamp': '2025-11-06 15:30:00'
}
```

### 7.3 Máquina de Estados

```
                  ┌─────────────┐
                  │   INICIO    │
                  └──────┬──────┘
                         │
              ┌──────────▼──────────┐
              │  DETECTAR_INTENT    │
              └──────┬──────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌────────────┐  ┌──────────┐
│CONSULTAR │  │  AGENDAR   │  │  OTROS   │
└────┬─────┘  └─────┬──────┘  └────┬─────┘
     │              │               │
     │         ┌────▼────┐          │
     │         │ PEDIR   │          │
     │         │ NOMBRE  │          │
     │         └────┬────┘          │
     │         ┌────▼────┐          │
     │         │ PEDIR   │          │
     │         │ CEDULA  │          │
     │         └────┬────┘          │
     │         ┌────▼────┐          │
     │         │ PEDIR   │          │
     │         │ EMAIL   │          │
     │         └────┬────┘          │
     │         ┌────▼────┐          │
     │         │ PEDIR   │          │
     │         │ FECHA   │          │
     │         └────┬────┘          │
     │         ┌────▼────┐          │
     │         │ PEDIR   │          │
     │         │  HORA   │          │
     │         └────┬────┘          │
     │         ┌────▼────┐          │
     │         │CONFIRMAR│          │
     │         └────┬────┘          │
     └──────────────┼───────────────┘
                    │
              ┌─────▼─────┐
              │   FINAL   │
              └───────────┘
```

---

## 8. Flujos de Datos

### 8.1 Flujo de Agendamiento Completo

```
USUARIO                 FRONTEND                BACKEND                 BASE DE DATOS
  │                        │                       │                           │
  │  "Quiero turno"        │                       │                           │
  ├───────────────────────>│                       │                           │
  │                        │  POST /process        │                           │
  │                        ├──────────────────────>│                           │
  │                        │                       │  Clasificar intent        │
  │                        │                       │  ↓ agendar_turno          │
  │                        │                       │                           │
  │                        │<─────────────────────┤                           │
  │  "¿Tu nombre?"         │  Response             │                           │
  │<───────────────────────┤                       │                           │
  │                        │                       │                           │
  │  "Juan Perez"          │                       │                           │
  ├───────────────────────>│                       │                           │
  │                        │  POST /process        │                           │
  │                        ├──────────────────────>│                           │
  │                        │                       │  Validar nombre           │
  │                        │                       │  Guardar en contexto      │
  │                        │<─────────────────────┤                           │
  │  "¿Tu cédula?"         │                       │                           │
  │<───────────────────────┤                       │                           │
  │                        │                       │                           │
  │  "1234567"             │                       │                           │
  ├───────────────────────>│                       │                           │
  │                        │  POST /process        │                           │
  │                        ├──────────────────────>│                           │
  │                        │                       │  Validar cédula           │
  │                        │                       │  Guardar en contexto      │
  │                        │<─────────────────────┤                           │
  │  "¿Para cuándo?"       │                       │                           │
  │<───────────────────────┤                       │                           │
  │                        │                       │                           │
  │  "Mañana a las 9"      │                       │                           │
  ├───────────────────────>│                       │                           │
  │                        │  POST /process        │                           │
  │                        ├──────────────────────>│                           │
  │                        │                       │  Extraer fecha y hora     │
  │                        │                       │  Verificar disponibilidad │
  │                        │                       ├──────────────────────────>│
  │                        │                       │  SELECT disponibilidad    │
  │                        │                       │<──────────────────────────┤
  │                        │                       │  Slot disponible          │
  │                        │<─────────────────────┤                           │
  │  "Confirmar datos?"    │                       │                           │
  │  Resumen completo      │                       │                           │
  │<───────────────────────┤                       │                           │
  │                        │                       │                           │
  │  "Confirmo"            │                       │                           │
  ├───────────────────────>│                       │                           │
  │                        │  POST /process        │                           │
  │                        ├──────────────────────>│                           │
  │                        │                       │  Crear turno              │
  │                        │                       ├──────────────────────────>│
  │                        │                       │  INSERT INTO turnos       │
  │                        │                       │<──────────────────────────┤
  │                        │                       │  turno_id = 123           │
  │                        │                       │                           │
  │                        │                       │  Enviar notificación      │
  │                        │                       │  (email/WhatsApp)         │
  │                        │<─────────────────────┤                           │
  │  "✅ Turno confirmado" │                       │                           │
  │  "Código: XYZ-123"     │                       │                           │
  │<───────────────────────┤                       │                           │
```

### 8.2 Flujo de Consulta Simple

```
USUARIO                 SISTEMA
  │                        │
  │  "Cuanto cuesta?"      │
  ├───────────────────────>│
  │                        │  1. Corrección ortográfica
  │                        │     (no hay errores)
  │                        │  
  │                        │  2. Clasificación intent
  │                        │     → consultar_costo (0.67)
  │                        │  
  │                        │  3. Buscar información
  │                        │     → Gs. 50,000
  │                        │  
  │                        │  4. Generar respuesta
  │<───────────────────────┤
  │  "El costo es Gs. 50k" │
  │  "para cédula nueva"   │
```

### 8.3 Flujo de Corrección Ortográfica

```
┌──────────────────────────────────────────────────────────┐
│  Mensaje original: "kiero un turno kuando ay disponible" │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  Tokenización: ["kiero", "un", "turno", "kuando",       │
│                 "ay", "disponible"]                       │
└────────────────────┬─────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │"kiero" │  │  "un"  │  │"turno" │
   │   ↓    │  │   ↓    │  │   ↓    │
   │"quiero"│  │  "un"  │  │"turno" │
   │(corr.) │  │(ok)    │  │(ok)    │
   └────────┘  └────────┘  └────────┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌────────┐  ┌────────────┐
   │"kuando"│  │  "ay"  │  │"disponible"│
   │   ↓    │  │   ↓    │  │     ↓      │
   │"cuando"│  │ "hay"  │  │"disponible"│
   │(corr.) │  │(corr.) │  │   (ok)     │
   └────────┘  └────────┘  └────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│  Mensaje corregido:                                      │
│  "quiero un turno cuando hay disponible"                 │
│                                                           │
│  Correcciones aplicadas:                                 │
│  • kiero → quiero                                        │
│  • kuando → cuando                                       │
│  • ay → hay                                              │
└──────────────────────────────────────────────────────────┘
```

---

## 📊 Resumen de Métricas Finales

| Componente | Precisión | Casos | Tiempo |
|------------|-----------|-------|--------|
| **Clasificación Intents** | 90.00% | 40 | 0.03ms |
| **Validación Cédula** | 95.00% | 20 | 0.00ms |
| **Normalización Nombres** | 100% | 15 | 0.00ms |
| **Detección Urgencia** | 100% | 20 | 0.00ms |
| **Corrección Ortografía** | 85.00% | 20 | 0.20ms |
| **Casos Reales** | 100% | 15 | 0.00ms |
| **Oraciones Compuestas** | 80.00% | 25 | 1.32ms |
| **Rendimiento** | 100% | 10 | 0.10ms |
| **TOTAL SISTEMA** | **93.75%** | **165** | **39ms** |

---

## 🎯 Conclusiones de la Parte 1

El sistema implementa una arquitectura robusta y modular que combina:

1. **Lógica Difusa** para manejo de ambigüedad natural
2. **Corrección Ortográfica Automática** con FuzzyWuzzy
3. **Detección Inteligente de Oraciones Compuestas**
4. **Validación Rigurosa** de datos críticos
5. **Pipeline de Procesamiento Optimizado**

Con una **puntuación global de 93.75%**, el sistema demuestra alta confiabilidad y está listo para producción.

---

**Continúa en**: [DOCUMENTACION_TECNICA_PARTE_2_TESTING_Y_METRICAS.md](./DOCUMENTACION_TECNICA_PARTE_2_TESTING_Y_METRICAS.md)

---

*Documento generado: 06 de Noviembre de 2025*  
*Versión del Sistema: 2.1*  
*Estado: APROBADO PARA PRODUCCIÓN*
