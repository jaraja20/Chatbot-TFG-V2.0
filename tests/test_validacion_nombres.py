"""
Script de prueba para validar el reconocimiento de nombres
"""
# -*- coding: utf-8 -*-

import sys
import re

# Palabras comunes que NO son nombres
palabras_prohibidas = {
    'yo', 'tu', 'el', 'ella', 'nosotros', 'ustedes', 'ellos',
    'no', 'si', 'nada', 'algo', 'todo', 'nadie', 'alguien',
    'que', 'como', 'cuando', 'donde', 'por', 'para', 'con', 'sin',
    'mi', 'mis', 'tu', 'tus', 'su', 'sus', 'nuestro', 'vuestro',
    'se', 'me', 'te', 'le', 'nos', 'les', 'lo', 'la', 'los', 'las',
    'un', 'una', 'unos', 'unas', 'el', 'la', 'los', 'las',
    'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
    'quiero', 'quieres', 'quiere', 'queremos', 'quieren',
    'puedo', 'puedes', 'puede', 'podemos', 'pueden',
    'tengo', 'tienes', 'tiene', 'tenemos', 'tienen',
    'soy', 'eres', 'es', 'somos', 'son',
    'hay', 'hola', 'buenos', 'dias', 'tardes', 'noches',
    'muy', 'mucho', 'poco', 'mas', 'menos', 'bien', 'mal',
    'loco', 'loca', 'tonto', 'tonta'
}

def validar_nombre(mensaje):
    """Valida si un mensaje es un nombre válido"""
    
    # Verificar longitud y formato básico
    if not (2 <= len(mensaje.split()) <= 4) or re.search(r'\d', mensaje):
        return False, "Debe tener 2-4 palabras sin números"
    
    palabras = mensaje.split()
    palabras_lower = [p.lower() for p in palabras]
    
    # Verificar palabras prohibidas
    palabras_detectadas = [p for p in palabras_lower if p in palabras_prohibidas]
    if palabras_detectadas:
        return False, f"Contiene palabras no válidas: {', '.join(palabras_detectadas)}"
    
    # Verificar que sean palabras válidas
    if not all(len(p) >= 2 and p.isalpha() for p in palabras):
        return False, "Debe contener solo letras, mínimo 2 por palabra"
    
    # Verificar mayúsculas (nombres propios)
    if not any(p[0].isupper() for p in palabras):
        return False, "Al menos una palabra debe empezar con mayúscula"
    
    return True, "[OK] Nombre válido"

# Casos de prueba
casos_prueba = [
    # Casos INVÁLIDOS (deben ser rechazados)
    "yo soy muy loco",
    "mi nombre es yo",
    "no se nada",
    "yo no se nada",
    "algo raro",
    "esto es malo",
    "quiero algo",
    "juan",  # Solo 1 palabra
    "Juan Lopez Martinez Fernandez Gonzalez",  # Más de 4 palabras
    
    # Casos VÁLIDOS (deben ser aceptados)
    "Juan Pérez",
    "María González",
    "Carlos Alberto Fernández",
    "Ana María Lopez Gonzalez",
    "Elijara Benitez",
    "Pedro Martinez"
]

print("\n" + "="*60)
print("PRUEBA DE VALIDACIÓN DE NOMBRES")
print("="*60 + "\n")

for caso in casos_prueba:
    valido, razon = validar_nombre(caso)
    emoji = "[OK]" if valido else "[FAIL]"
    print(f"{emoji} '{caso}'")
    print(f"   → {razon}\n")
