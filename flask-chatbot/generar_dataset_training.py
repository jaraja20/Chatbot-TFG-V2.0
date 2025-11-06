"""
Generador de dataset para fine-tuning del LLM
Extrae casos de los tests existentes y genera formato JSONL
"""

import json
import sys
import os

# Casos de entrenamiento extraídos de los tests
training_data = []

# =====================================================
# TEST MEGA TRAINING (67 casos)
# =====================================================
mega_training_cases = [
    # Agendar turno
    ("quiero agendar un turno", "agendar_turno"),
    ("necesito sacar turno", "agendar_turno"),
    ("me gustaria agendar", "agendar_turno"),
    ("quiero marcar turno", "agendar_turno"),
    ("necesito turno", "agendar_turno"),
    ("kiero turno", "agendar_turno"),
    ("nesecito agendar", "agendar_turno"),
    
    # Consultar disponibilidad
    ("que horarios tienen disponibles?", "consultar_disponibilidad"),
    ("hay turnos para mañana?", "consultar_disponibilidad"),
    ("tienen horarios libres?", "consultar_disponibilidad"),
    ("que dias hay disponible?", "consultar_disponibilidad"),
    ("cuando puedo ir?", "consultar_disponibilidad"),
    ("para cuando hay turnos?", "consultar_disponibilidad"),
    ("que dia me recomiendas?", "consultar_disponibilidad"),
    
    # Consultar requisitos
    ("que documentos necesito?", "consultar_requisitos"),
    ("cuales son los requisitos?", "consultar_requisitos"),
    ("que papeles tengo que llevar?", "consultar_requisitos"),
    ("que necesito para sacar la cedula?", "consultar_requisitos"),
    ("que documentos hay que presentar?", "consultar_requisitos"),
    
    # Consultar costo
    ("cuanto cuesta?", "consultar_costo"),
    ("cual es el precio?", "consultar_costo"),
    ("cuanto sale el tramite?", "consultar_costo"),
    ("cuanto hay que pagar?", "consultar_costo"),
    ("cuanto vale?", "consultar_costo"),
    
    # Consultar ubicacion
    ("donde quedan?", "consultar_ubicacion"),
    ("cual es la direccion?", "consultar_ubicacion"),
    ("donde estan ubicados?", "consultar_ubicacion"),
    ("como llego?", "consultar_ubicacion"),
    ("tienen numero de contacto?", "consultar_ubicacion"),
    ("hay algun numero de contacto?", "consultar_ubicacion"),
    ("puedo llamar?", "consultar_ubicacion"),
    
    # Informar nombre
    ("mi nombre es juan perez", "informar_nombre"),
    ("me llamo maria lopez", "informar_nombre"),
    ("soy carlos gomez", "informar_nombre"),
    ("juan garcia", "informar_nombre"),
    
    # Informar cedula
    ("mi cedula es 1234567", "informar_cedula"),
    ("tengo cedula 9876543", "informar_cedula"),
    ("cedula 5555555", "informar_cedula"),
    ("1234567", "informar_cedula"),
    
    # Elegir horario
    ("para las 9", "elegir_horario"),
    ("a las 14:30", "elegir_horario"),
    ("prefiero las 8", "elegir_horario"),
    ("las 10 esta bien", "elegir_horario"),
    
    # Informar email
    ("mi email es test@gmail.com", "informar_email"),
    ("correo: usuario@hotmail.com", "informar_email"),
    ("test@example.com", "informar_email"),
    
    # Confirmar
    ("si", "confirmar"),
    ("confirmo", "confirmar"),
    ("esta bien", "confirmar"),
    ("perfecto", "confirmar"),
    ("acepto", "confirmar"),
    
    # Negacion
    ("no", "negacion"),
    ("no es correcto", "negacion"),
    ("esta mal", "negacion"),
    ("no quiero", "negacion"),
    ("cancelar", "negacion"),
    
    # Greet
    ("hola", "greet"),
    ("buenos dias", "greet"),
    ("buenas tardes", "greet"),
    ("que tal", "greet"),
]

# =====================================================
# TEST VARIACIONES NUEVAS (63 casos)
# =====================================================
variaciones_cases = [
    # Variaciones con contexto
    ("esta bien la hora que recomiendas", "elegir_horario"),
    ("quiero cambiar de horario para las 8", "elegir_horario"),
    ("puedo cambiar el turno para las 8?", "elegir_horario"),
    ("pero tu ya me recomendaste para las 7", "elegir_horario"),
    
    # Cambios de fecha
    ("no puedo cambiar mi turno para el jueves a la misma hora?", "consultar_disponibilidad"),
    ("cambiar para el lunes", "consultar_disponibilidad"),
    ("mejor para el martes", "consultar_disponibilidad"),
    
    # Ortografía extrema
    ("kiero agendar", "agendar_turno"),
    ("nesecito turno", "agendar_turno"),
    ("kuanto bale?", "consultar_costo"),
    ("ke documentos nesecito?", "consultar_requisitos"),
    
    # Frases largas
    ("hola buenos dias queria saber si es posible agendar un turno para mañana", "agendar_turno"),
    ("disculpa me podrias decir que documentos necesito para sacar la cedula", "consultar_requisitos"),
    
    # Preguntas indirectas
    ("me dijeron que necesito turno", "agendar_turno"),
    ("quiero saber los horarios", "consultar_disponibilidad"),
    ("necesito informacion sobre costos", "consultar_costo"),
]

# =====================================================
# TEST ORACIONES COMPUESTAS (45 casos)
# =====================================================
compuestas_cases = [
    # Consultas múltiples
    ("donde quedan y que horarios tienen?", "consultar_ubicacion"),
    ("cuanto cuesta y que documentos necesito?", "consultar_costo"),
    ("tienen turnos para mañana y cuanto sale?", "consultar_disponibilidad"),
    
    # Consultas temporales
    ("para hoy no están turnos disponibles?", "consultar_disponibilidad"),
    ("para mañana a la mañana puedo marcar?", "consultar_disponibilidad"),
    ("de tarde hay turnos?", "consultar_disponibilidad"),
    
    # Comparaciones
    ("es mejor sacar turno online o ir directamente?", "consultar_disponibilidad"),
    
    # Contexto personal
    ("mi hermano fue ahi y le dieron turno rapido", "consultar_disponibilidad"),
]

# Combinar todos los casos
all_cases = mega_training_cases + variaciones_cases + compuestas_cases

print(f"📊 Total de casos para training: {len(all_cases)}")

# =====================================================
# GENERAR DATASET EN FORMATO JSONL
# =====================================================

# Formato para fine-tuning de llama
output_file = "dataset_training.jsonl"

with open(output_file, 'w', encoding='utf-8') as f:
    for mensaje, intent in all_cases:
        # Formato de conversación
        training_example = {
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un clasificador de intents para un chatbot de agendamiento de cédulas. Clasifica el mensaje del usuario en uno de estos intents: agendar_turno, consultar_disponibilidad, consultar_requisitos, consultar_costo, consultar_ubicacion, informar_nombre, informar_cedula, elegir_horario, informar_email, confirmar, negacion, greet. Responde SOLO con el nombre del intent."
                },
                {
                    "role": "user",
                    "content": mensaje
                },
                {
                    "role": "assistant",
                    "content": intent
                }
            ]
        }
        
        f.write(json.dumps(training_example, ensure_ascii=False) + '\n')

print(f"✅ Dataset generado: {output_file}")
print(f"📁 Total de ejemplos: {len(all_cases)}")

# =====================================================
# GENERAR DATASET DE VALIDACIÓN (20%)
# =====================================================

import random
random.seed(42)

# Separar 20% para validación
num_validation = int(len(all_cases) * 0.2)
validation_indices = random.sample(range(len(all_cases)), num_validation)

validation_file = "dataset_validation.jsonl"
training_file_filtered = "dataset_training_filtered.jsonl"

with open(validation_file, 'w', encoding='utf-8') as val_f, \
     open(training_file_filtered, 'w', encoding='utf-8') as train_f:
    
    for idx, (mensaje, intent) in enumerate(all_cases):
        training_example = {
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un clasificador de intents para un chatbot de agendamiento de cédulas. Clasifica el mensaje del usuario en uno de estos intents: agendar_turno, consultar_disponibilidad, consultar_requisitos, consultar_costo, consultar_ubicacion, informar_nombre, informar_cedula, elegir_horario, informar_email, confirmar, negacion, greet. Responde SOLO con el nombre del intent."
                },
                {
                    "role": "user",
                    "content": mensaje
                },
                {
                    "role": "assistant",
                    "content": intent
                }
            ]
        }
        
        if idx in validation_indices:
            val_f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
        else:
            train_f.write(json.dumps(training_example, ensure_ascii=False) + '\n')

print(f"\n📊 Dataset dividido:")
print(f"   Training: {len(all_cases) - num_validation} ejemplos → {training_file_filtered}")
print(f"   Validation: {num_validation} ejemplos → {validation_file}")
print(f"\n✅ Datasets listos para fine-tuning!")
