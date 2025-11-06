"""
Test completo del flujo de conversación reportado
"""
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\tfg funcional\Chatbot-TFG-V2.0\flask-chatbot')

from orquestador_inteligente import procesar_mensaje_inteligente, SessionContext

print("\n" + "="*70)
print("SIMULACIÓN COMPLETA DE CONVERSACIÓN")
print("="*70)

# Crear contexto de sesión
contexto = SessionContext('test_completo')

# Paso 1: Quiero agendar un turno
print("\n[USER] Usuario: Quiero agendar un turno")
print("-" * 70)
resultado = procesar_mensaje_inteligente('Quiero agendar un turno', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

# Paso 2: Macaco volador (debería rechazarse)
print("\n[USER] Usuario: macaco volador")
print("-" * 70)
resultado = procesar_mensaje_inteligente('macaco volador', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

# Paso 3: Nombre real
print("\n[USER] Usuario: Juan Pérez")
print("-" * 70)
resultado = procesar_mensaje_inteligente('Juan Pérez', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

# Paso 4: Cédula
print("\n[USER] Usuario: 245343")
print("-" * 70)
resultado = procesar_mensaje_inteligente('245343', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

# Paso 5: Consultar disponibilidad próxima semana
print("\n[USER] Usuario: que tal la disponibilidad para la proxima semana?")
print("-" * 70)
resultado = procesar_mensaje_inteligente('que tal la disponibilidad para la proxima semana?', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

# Paso 6: Elegir un día específico (mañana)
print("\n[USER] Usuario: para mañana")
print("-" * 70)
resultado = procesar_mensaje_inteligente('para mañana', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

# Paso 7: Aceptar hora recomendada
print("\n[USER] Usuario: esa hora recomendada esta bien")
print("-" * 70)
resultado = procesar_mensaje_inteligente('esa hora recomendada esta bien', contexto)
print(f"[BOT] Bot: {resultado['text']}\n")

print("="*70)
print("[OK] Simulación completada")
print("="*70)
print(f"\nDatos finales del contexto:")
print(f"- Nombre: {contexto.nombre}")
print(f"- Cédula: {contexto.cedula}")
print(f"- Fecha: {contexto.fecha}")
print(f"- Hora: {contexto.hora}")
print(f"- Hora recomendada: {contexto.hora_recomendada}")
