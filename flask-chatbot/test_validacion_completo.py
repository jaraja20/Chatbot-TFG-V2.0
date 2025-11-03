"""
Test completo del sistema de validación de nombres
Prueba que:
1. Los intents de acción (agendar turno) se detecten correctamente
2. Las frases inválidas como nombres se rechacen
3. Los nombres válidos se acepten
"""

# Simular el contexto
class SessionContext:
    def __init__(self):
        self.nombre = None
        self.cedula = None
        self.fecha = None
        self.hora = None
        self.session_id = "test"

import re

# Palabras clave de intents de ACCIÓN (no son nombres)
palabras_accion = ['agendar', 'turno', 'cita', 'horario', 'disponibilidad', 
                  'requisitos', 'ubicacion', 'ubicación', 'direccion', 'dirección',
                  'costo', 'precio', 'cuanto', 'cuánto', 'pagar',
                  'consultar', 'ver', 'necesito', 'información', 'informacion']

# Lista de palabras comunes que NO son nombres
palabras_prohibidas = {
    'yo', 'tu', 'el', 'ella', 'nosotros', 'ustedes', 'ellos',
    'no', 'nada', 'algo', 'todo', 'nadie', 'alguien',
    'que', 'como', 'cuando', 'donde',
    'se', 'me', 'te', 'le', 'nos', 'les', 'lo', 'la', 'los', 'las',
    'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
    'muy', 'mucho', 'poco', 'mas', 'menos', 'bien', 'mal',
    'loco', 'loca', 'tonto', 'tonta', 'raro', 'rara',
    'cosa', 'cosas', 'bueno', 'malo', 'mala'
}

def simular_clasificacion(mensaje, contexto):
    """Simula la lógica de clasificación del orquestador"""
    mensaje_lower = mensaje.lower().strip()
    
    # Si el mensaje contiene palabras de acción, NO validar como nombre
    es_accion = any(palabra in mensaje_lower for palabra in palabras_accion)
    
    # Si NO tenemos nombre y NO es un mensaje de acción,
    # detectar si el mensaje contiene palabras prohibidas
    if not contexto.nombre and not es_accion:
        palabras = mensaje.split()
        palabras_lower = [p.lower() for p in palabras]
        
        # Si contiene palabras prohibidas, NO es un nombre válido
        if any(p in palabras_prohibidas for p in palabras_lower):
            return "RECHAZAR (palabras prohibidas)"
    
    # Si es acción, permitir
    if es_accion:
        return "ACEPTAR (intent de acción)"
    
    # Si parece nombre válido (2-4 palabras, sin números, con mayúsculas)
    if not contexto.nombre and 2 <= len(mensaje.split()) <= 4 and not re.search(r'\d', mensaje):
        palabras = mensaje.split()
        palabras_lower = [p.lower() for p in palabras]
        
        if not any(p in palabras_prohibidas for p in palabras_lower):
            if all(len(p) >= 2 and p.isalpha() for p in palabras):
                if any(p[0].isupper() for p in palabras):
                    return "ACEPTAR (nombre válido)"
    
    return "PROCESAR CON LLM"

# Casos de prueba
print("\n" + "="*70)
print("TEST COMPLETO DEL SISTEMA DE VALIDACIÓN")
print("="*70 + "\n")

# 1. INTENTS DE ACCIÓN (deben aceptarse)
print("📋 PRUEBA 1: INTENTS DE ACCIÓN")
print("-" * 70)
casos_accion = [
    "Quiero agendar un turno",
    "necesito un turno",
    "consultar horarios disponibles",
    "cuanto cuesta la cedula",
    "donde queda la oficina",
    "requisitos para menores"
]

contexto = SessionContext()
for caso in casos_accion:
    resultado = simular_clasificacion(caso, contexto)
    emoji = "✅" if "acción" in resultado else "❌"
    print(f"{emoji} '{caso}'")
    print(f"   → {resultado}\n")

# 2. FRASES INVÁLIDAS COMO NOMBRES (deben rechazarse)
print("\n📋 PRUEBA 2: FRASES INVÁLIDAS COMO NOMBRES")
print("-" * 70)
casos_invalidos = [
    "yo soy muy loco",
    "yo no se nada",
    "mi nombre es yo",
    "algo raro aqui",
    "esto es malo",
    "no se nada",
    "muy bueno todo"
]

contexto = SessionContext()  # Sin nombre
for caso in casos_invalidos:
    resultado = simular_clasificacion(caso, contexto)
    emoji = "✅" if "RECHAZAR" in resultado else "❌"
    print(f"{emoji} '{caso}'")
    print(f"   → {resultado}\n")

# 3. NOMBRES VÁLIDOS (deben aceptarse)
print("\n📋 PRUEBA 3: NOMBRES VÁLIDOS")
print("-" * 70)
casos_validos = [
    "Juan Pérez",
    "María González",
    "Carlos Alberto Fernández",
    "Elijara Benitez",
    "Ana María Lopez"
]

contexto = SessionContext()  # Sin nombre
for caso in casos_validos:
    resultado = simular_clasificacion(caso, contexto)
    emoji = "✅" if "nombre válido" in resultado else "❌"
    print(f"{emoji} '{caso}'")
    print(f"   → {resultado}\n")

# 4. CASOS AMBIGUOS (deben procesarse con LLM)
print("\n📋 PRUEBA 4: CASOS AMBIGUOS")
print("-" * 70)
casos_ambiguos = [
    "mañana",  # Podría ser fecha
    "para las 10",  # Podría ser hora
    "hola",  # Saludo
    "si",  # Confirmación
    "juan"  # Solo 1 palabra
]

contexto = SessionContext()  # Sin nombre
for caso in casos_ambiguos:
    resultado = simular_clasificacion(caso, contexto)
    print(f"ℹ️  '{caso}'")
    print(f"   → {resultado}\n")

print("="*70)
print("✅ Test completado")
print("="*70)
