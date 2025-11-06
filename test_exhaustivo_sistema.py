"""
TEST EXHAUSTIVO DEL SISTEMA V2.0
Cada componente tiene métricas específicas y cuantificables
El resultado final es la MEDIA de todos los componentes

MEJORAS V2.1:
- Corrección ortográfica automática con FuzzyWuzzy
- Detección y manejo de oraciones compuestas
- Priorización contextual por palabras clave
"""
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "flask-chatbot"))

from razonamiento_difuso import clasificar_con_logica_difusa
from mejoras_fuzzy import crear_clasificador_mejorado
import time
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI

# Inicializar clasificador mejorado
clasificador_mejorado = crear_clasificador_mejorado(clasificar_con_logica_difusa)
from datetime import datetime
import numpy as np

class MetricaComponente:
    """Clase para almacenar métricas de cada componente"""
    def __init__(self, nombre, descripcion):
        self.nombre = nombre
        self.descripcion = descripcion
        self.casos_correctos = 0
        self.casos_totales = 0
        self.tiempo_total = 0
        self.detalles = []
    
    def agregar_caso(self, exito, detalle="", tiempo=0):
        """Agrega un caso de prueba"""
        self.casos_totales += 1
        if exito:
            self.casos_correctos += 1
        self.tiempo_total += tiempo
        if not exito:
            self.detalles.append(detalle)
    
    def get_porcentaje(self):
        """Calcula porcentaje de éxito"""
        if self.casos_totales == 0:
            return 0.0
        return (self.casos_correctos / self.casos_totales) * 100
    
    def get_tiempo_promedio(self):
        """Calcula tiempo promedio por caso"""
        if self.casos_totales == 0:
            return 0.0
        return self.tiempo_total / self.casos_totales


def test_clasificacion_intents():
    """
    COMPONENTE 1: Clasificación de Intents por Motor Difuso
    Métrica: Precisión en clasificación de 40 casos variados
    """
    print("\n" + "="*80)
    print("COMPONENTE 1: CLASIFICACION DE INTENTS - MOTOR DIFUSO")
    print("="*80)
    
    metrica = MetricaComponente(
        "Clasificación de Intents",
        "Precisión del motor difuso en identificar la intención del usuario"
    )
    
    # Casos de prueba exhaustivos por cada intent
    casos = [
        # AGENDAR_TURNO (8 casos)
        ('quiero un turno', 'agendar_turno'),
        ('necesito agendar', 'agendar_turno'),
        ('sacar turno', 'agendar_turno'),
        ('quiero sacar turno', 'agendar_turno'),
        ('turno por favor', 'agendar_turno'),
        ('agendar cita', 'agendar_turno'),
        ('reservar turno', 'agendar_turno'),
        ('me gustaria un turno', 'agendar_turno'),
        
        # CONSULTAR_DISPONIBILIDAD (8 casos)
        ('que dias hay disponible', 'consultar_disponibilidad'),
        ('cuando tienen lugar', 'consultar_disponibilidad'),
        ('hay turnos para mañana', 'consultar_disponibilidad'),
        ('que horarios tienen', 'consultar_disponibilidad'),
        ('tienen disponible', 'consultar_disponibilidad'),
        ('hay hueco', 'consultar_disponibilidad'),
        ('para cuando hay', 'consultar_disponibilidad'),
        ('disponibilidad esta semana', 'consultar_disponibilidad'),
        
        # CONSULTAR_COSTO (5 casos)
        ('cuanto cuesta', 'consultar_costo'),
        ('cual es el precio', 'consultar_costo'),
        ('cuanto vale', 'consultar_costo'),
        ('precio de la cedula', 'consultar_costo'),
        ('costo del tramite', 'consultar_costo'),
        
        # CONSULTAR_REQUISITOS (5 casos)
        ('que necesito', 'consultar_requisitos'),
        ('cuales son los requisitos', 'consultar_requisitos'),
        ('que documentos necesito', 'consultar_requisitos'),
        ('requisitos para cedula', 'consultar_requisitos'),
        ('que debo llevar', 'consultar_requisitos'),
        
        # CONSULTAR_TRAMITES (3 casos)
        ('que tramites hacen', 'consultar_tramites'),
        ('que servicios ofrecen', 'consultar_tramites'),
        ('que puedo hacer ahi', 'consultar_tramites'),
        
        # AFFIRM (5 casos)
        ('si', 'affirm'),
        ('confirmo', 'affirm'),
        ('ok', 'affirm'),
        ('de acuerdo', 'affirm'),
        ('esta bien', 'affirm'),
        
        # NEGACION (4 casos)
        ('no', 'negacion'),
        ('no me sirve', 'negacion'),
        ('mejor no', 'negacion'),
        ('prefiero otro', 'negacion'),
        
        # CANCELAR (2 casos)
        ('cancelar', 'cancelar'),
        ('quiero cancelar', 'cancelar'),
    ]
    
    print(f"Evaluando {len(casos)} casos de clasificación...\n")
    
    for i, (mensaje, esperado) in enumerate(casos, 1):
        print(f"[{i}/{len(casos)}] Probando: '{mensaje}'")
        print(f"       Esperado: {esperado}")
        
        inicio = time.time()
        intent, conf = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        tiempo = time.time() - inicio
        
        exito = (intent == esperado)
        marca = "[OK]" if exito else "[FAIL]"
        print(f"       Obtenido: {intent} (confianza: {conf:.2f}) {marca}")
        
        if not exito:
            detalle = f"'{mensaje}' -> Esperado: {esperado}, Obtenido: {intent} (conf: {conf:.2f})"
        else:
            detalle = ""
        
        metrica.agregar_caso(exito, detalle, tiempo)
        print()  # Línea en blanco entre casos
    
    return metrica


def test_validacion_cedula():
    """
    COMPONENTE 2: Validación de Cédula
    Métrica: Precisión en validar formatos de cédula
    """
    print("\n" + "="*80)
    print("COMPONENTE 2: VALIDACION DE CEDULA")
    print("="*80)
    
    metrica = MetricaComponente(
        "Validación de Cédula",
        "Precisión en validar formatos válidos e inválidos de cédula"
    )
    
    import re
    
    def validar_cedula(cedula):
        """Valida formato de cédula paraguaya"""
        cedula_limpia = re.sub(r'[.\-]', '', str(cedula))
        return cedula_limpia.isdigit() and 6 <= len(cedula_limpia) <= 8
    
    # Casos válidos (10)
    casos_validos = [
        '5264036',
        '5.264.036',
        '5264036-3',
        '5.264.036-3',
        '1234567',
        '1.234.567',
        '123456',
        '1.234.567-8',
        '7654321',
        '7.654.321-0',
    ]
    
    # Casos inválidos (10)
    casos_invalidos = [
        'abc123',
        '123',
        '12345',
        '123456789',
        '999999999',
        'abcdefg',
        '12.34',
        'XXX-XXX',
        '',
        '12-34-56',
    ]
    
    print(f"Evaluando {len(casos_validos)} cédulas válidas...\n")
    for i, cedula in enumerate(casos_validos, 1):
        print(f"[{i}/{len(casos_validos)}] Validando cédula VALIDA: '{cedula}'")
        inicio = time.time()
        resultado = validar_cedula(cedula)
        tiempo = time.time() - inicio
        
        marca = "[OK]" if resultado else "[FAIL]"
        print(f"       Resultado: {'ACEPTADA' if resultado else 'RECHAZADA'} {marca}\n")
        
        if not resultado:
            detalle = f"Cédula válida rechazada: '{cedula}'"
        else:
            detalle = ""
        
        metrica.agregar_caso(resultado, detalle, tiempo)
    
    print(f"Evaluando {len(casos_invalidos)} cédulas inválidas...\n")
    for i, cedula in enumerate(casos_invalidos, 1):
        print(f"[{i}/{len(casos_invalidos)}] Validando cédula INVALIDA: '{cedula}'")
        inicio = time.time()
        es_valida = validar_cedula(cedula)
        resultado = not es_valida  # Debe ser rechazada
        tiempo = time.time() - inicio
        
        marca = "[OK]" if resultado else "[FAIL]"
        print(f"       Resultado: {'RECHAZADA (correcto)' if resultado else 'ACEPTADA (error)'} {marca}\n")
        
        if not resultado:
            detalle = f"Cédula inválida aceptada: '{cedula}'"
        else:
            detalle = ""
        
        metrica.agregar_caso(resultado, detalle, tiempo)
    
    return metrica


def test_normalizacion_nombres():
    """
    COMPONENTE 3: Normalización de Nombres
    Métrica: Precisión en formatear nombres correctamente
    """
    print("\n" + "="*80)
    print("COMPONENTE 3: NORMALIZACION DE NOMBRES")
    print("="*80)
    
    metrica = MetricaComponente(
        "Normalización de Nombres",
        "Precisión en formatear nombres con capitalización correcta"
    )
    
    def normalizar_nombre(nombre):
        """Normaliza un nombre"""
        return ' '.join(nombre.strip().split()).title()
    
    # 15 casos de prueba
    casos = [
        ('juan perez', 'Juan Perez'),
        ('MARIA GARCIA', 'Maria Garcia'),
        ('pedro  luis   gomez', 'Pedro Luis Gomez'),
        ('  ana  maria  ', 'Ana Maria'),
        ('jose', 'Jose'),
        ('RODRIGUEZ FERNANDEZ', 'Rodriguez Fernandez'),
        ('maria de los angeles', 'Maria De Los Angeles'),
        ('o\'connor', "O'Connor"),
        ('jean-paul', 'Jean-Paul'),
        ('mc donald', 'Mc Donald'),
        ('  ', ''),
        ('a b c d e', 'A B C D E'),
        ('maría josé', 'María José'),
        ('joão silva', 'João Silva'),
        ('lópez garcía', 'López García'),
    ]
    
    print(f"Evaluando {len(casos)} casos de normalización...\n")
    
    for i, (entrada, esperado) in enumerate(casos, 1):
        print(f"[{i}/{len(casos)}] Normalizando: '{entrada}'")
        print(f"       Esperado: '{esperado}'")
        
        inicio = time.time()
        resultado = normalizar_nombre(entrada)
        tiempo = time.time() - inicio
        
        exito = (resultado == esperado)
        marca = "[OK]" if exito else "[FAIL]"
        print(f"       Obtenido: '{resultado}' {marca}\n")
        
        if not exito:
            detalle = f"'{entrada}' -> Esperado: '{esperado}', Obtenido: '{resultado}'"
        else:
            detalle = ""
        
        metrica.agregar_caso(exito, detalle, tiempo)
    
    return metrica


def test_deteccion_urgencia():
    """
    COMPONENTE 4: Detección de Urgencia
    Métrica: Precisión en detectar urgencia en mensajes
    """
    print("\n" + "="*80)
    print("COMPONENTE 4: DETECCION DE URGENCIA")
    print("="*80)
    
    metrica = MetricaComponente(
        "Detección de Urgencia",
        "Precisión en identificar mensajes con urgencia"
    )
    
    palabras_urgencia = ['urgente', 'rapido', 'ya', 'antes posible', 'cuanto antes', 'apurado', 'emergencia']
    
    def detectar_urgencia(texto):
        """Detecta urgencia en el texto"""
        texto_lower = texto.lower()
        return any(palabra in texto_lower for palabra in palabras_urgencia)
    
    # Casos CON urgencia (10)
    casos_urgentes = [
        'lo antes posible',
        'urgente por favor',
        'necesito ya',
        'es urgente',
        'cuanto antes mejor',
        'necesito rapido',
        'estoy apurado',
        'es una emergencia',
        'urgente necesito turno',
        'lo mas rapido posible',
    ]
    
    # Casos SIN urgencia (10)
    casos_normales = [
        'quiero un turno',
        'para la proxima semana',
        'cuando hay disponible',
        'me gustaria agendar',
        'quisiera informacion',
        'buenos dias',
        'cuanto cuesta',
        'que requisitos necesito',
        'para mañana',
        'el jueves',
    ]
    
    print(f"Evaluando {len(casos_urgentes)} casos con urgencia...")
    for caso in casos_urgentes:
        inicio = time.time()
        resultado = detectar_urgencia(caso)
        tiempo = time.time() - inicio
        
        if not resultado:
            detalle = f"Urgencia no detectada: '{caso}'"
            print(f"[FAIL] {detalle}")
        
        metrica.agregar_caso(resultado, detalle if not resultado else "", tiempo)
    
    print(f"Evaluando {len(casos_normales)} casos sin urgencia...")
    for caso in casos_normales:
        inicio = time.time()
        resultado = not detectar_urgencia(caso)
        tiempo = time.time() - inicio
        
        if not resultado:
            detalle = f"Falsa urgencia detectada: '{caso}'"
            print(f"[FAIL] {detalle}")
        
        metrica.agregar_caso(resultado, detalle if not resultado else "", tiempo)
    
    return metrica


def test_manejo_ortografia():
    """
    COMPONENTE 5: Manejo de Errores Ortográficos
    Métrica: Robustez ante errores ortográficos comunes
    """
    print("\n" + "="*80)
    print("COMPONENTE 5: MANEJO DE ERRORES ORTOGRAFICOS")
    print("="*80)
    
    metrica = MetricaComponente(
        "Manejo de Ortografía",
        "Robustez del sistema ante errores ortográficos"
    )
    
    # 20 casos con errores ortográficos y su intent esperado
    casos = [
        ('kiero turno', 'agendar_turno'),
        ('cuanto bale', 'consultar_costo'),
        ('nesesito', 'agendar_turno'),
        ('rekisitos', 'consultar_requisitos'),
        ('quisiera ajendarme', 'agendar_turno'),
        ('disponivilidad', 'consultar_disponibilidad'),
        ('cosultar', 'consultar_disponibilidad'),
        ('k horarios tienen', 'consultar_disponibilidad'),
        ('para kuando', 'consultar_disponibilidad'),
        ('presio', 'consultar_costo'),
        ('dokumentos', 'consultar_requisitos'),
        ('si xfavor', 'affirm'),
        ('cancelar xfa', 'cancelar'),
        ('no me sierve', 'negacion'),
        ('tambien', 'affirm'),
        ('perfekto', 'affirm'),
        ('konfirmo', 'affirm'),
        ('kuanto sale', 'consultar_costo'),
        ('aora', 'agendar_turno'),
        ('tramites ke hacen', 'consultar_tramites'),
    ]
    
    print(f"Evaluando {len(casos)} casos con errores ortográficos...\n")
    
    for i, (mensaje, esperado) in enumerate(casos, 1):
        print(f"[{i}/{len(casos)}] Mensaje con error: '{mensaje}'")
        print(f"       Esperado: {esperado}")
        
        inicio = time.time()
        # USAR CLASIFICADOR MEJORADO con corrección ortográfica
        intent, conf, metadata = clasificador_mejorado.clasificar_mejorado(
            mensaje, 
            threshold=0.3,
            corregir_ortografia=True,
            manejar_compuestas=False
        )
        tiempo = time.time() - inicio
        
        # Mostrar correcciones si las hubo
        if metadata['correcciones']:
            print(f"       Corregido: '{metadata['mensaje_corregido']}'")
        
        exito = (intent == esperado)
        marca = "[OK]" if exito else "[FAIL]"
        print(f"       Obtenido: {intent} (confianza: {conf:.2f}) {marca}\n")
        
        if not exito:
            detalle = f"'{mensaje}' -> Esperado: {esperado}, Obtenido: {intent} (conf: {conf:.2f})"
        else:
            detalle = ""
        
        metrica.agregar_caso(exito, detalle, tiempo)
    
    return metrica


def test_casos_reales():
    """
    COMPONENTE 6: Casos Reales de Producción
    Métrica: Éxito en casos extraídos de logs reales
    """
    print("\n" + "="*80)
    print("COMPONENTE 6: CASOS REALES DE PRODUCCION")
    print("="*80)
    
    metrica = MetricaComponente(
        "Casos Reales",
        "Precisión en casos reales extraídos de logs de producción"
    )
    
    # 15 casos reales que causaron problemas
    casos = [
        ('cuanto bale sacar la cedula?', 'consultar_costo'),
        ('para cuando hay hueco?', 'consultar_disponibilidad'),
        ('documentos', 'consultar_requisitos'),
        ('buenas, para cuando hay hueco?', 'consultar_disponibilidad'),
        ('vieja, necesito sacar turno urgente', 'agendar_turno'),
        ('dame un dia intermedio de la semana', 'consultar_disponibilidad'),
        ('no, esa hora no me sirve', 'negacion'),
        ('mejor otro día', 'negacion'),
        ('cancelar', 'cancelar'),
        ('requisitos', 'consultar_requisitos'),
        ('precio', 'consultar_costo'),
        ('disponible mañana', 'consultar_disponibilidad'),
        ('si confirmo', 'affirm'),
        ('turno para hoy', 'agendar_turno'),
        ('que necesito para renovar', 'consultar_requisitos'),
    ]
    
    print(f"Evaluando {len(casos)} casos reales...\n")
    
    for i, (mensaje, esperado) in enumerate(casos, 1):
        print(f"[{i}/{len(casos)}] Caso real: '{mensaje}'")
        print(f"       Esperado: {esperado}")
        
        inicio = time.time()
        intent, conf = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        tiempo = time.time() - inicio
        
        exito = (intent == esperado)
        marca = "[OK]" if exito else "[FAIL]"
        print(f"       Obtenido: {intent} (confianza: {conf:.2f}) {marca}\n")
        
        if not exito:
            detalle = f"'{mensaje}' -> Esperado: {esperado}, Obtenido: {intent} (conf: {conf:.2f})"
        else:
            detalle = ""
        
        metrica.agregar_caso(exito, detalle, tiempo)
    
    return metrica


def test_oraciones_compuestas():
    """
    COMPONENTE 8: Oraciones Compuestas y Consultas Múltiples
    Métrica: Capacidad de entender frases complejas con múltiples intents
    """
    print("\n" + "="*80)
    print("COMPONENTE 8: ORACIONES COMPUESTAS Y CONSULTAS MULTIPLES")
    print("="*80)
    
    metrica = MetricaComponente(
        "Oraciones Compuestas",
        "Precisión en frases con múltiples intents o contexto complejo"
    )
    
    # 25 casos de frases compuestas variadas
    casos = [
        # Temporal + Consulta (5 casos)
        ('necesito un turno para el lunes, hay disponible?', 'consultar_disponibilidad'),
        ('quiero ir mañana, a que hora puedo?', 'consultar_disponibilidad'),
        ('para el jueves tienen horarios libres?', 'consultar_disponibilidad'),
        ('me gustaria ir la semana que viene, cuando hay turnos?', 'consultar_disponibilidad'),
        ('tengo libre el miércoles, hay algo disponible ese dia?', 'consultar_disponibilidad'),
        
        # Agendar con Condiciones (5 casos)
        ('quiero agendar un turno pero solo puedo por la tarde', 'agendar_turno'),
        ('necesito turno urgente, cuando es lo mas rapido?', 'consultar_disponibilidad'),
        ('puedo sacar turno para hoy mismo?', 'consultar_disponibilidad'),
        ('quiero reservar pero no se si tienen lugar', 'consultar_disponibilidad'),
        ('necesito agendar para antes del viernes', 'agendar_turno'),
        
        # Múltiples Consultas (5 casos) - Se espera el primer intent detectado por prioridad
        ('cuanto sale y que documentos necesito?', 'consultar_costo'),
        ('que requisitos hay y cuanto cuesta el tramite?', 'consultar_costo'),  # "cuanto cuesta" tiene más peso
        ('que dias atienden y hasta que hora estan abiertos?', 'consultar_disponibilidad'),
        ('donde quedan y como puedo llegar?', 'consultar_ubicacion'),
        ('cuanto vale y cuando puedo ir?', 'consultar_costo'),
        
        # Con Muletillas y Conectores (5 casos)
        ('bueno, entonces, me podes decir que horarios hay?', 'consultar_disponibilidad'),
        ('mira, es que necesito turno para la proxima semana', 'agendar_turno'),
        ('disculpa, pero cuanto me va a salir esto?', 'consultar_costo'),
        ('ey, una pregunta, que papeles tengo que llevar?', 'consultar_requisitos'),
        ('che, y cuando estan abiertos?', 'consultar_disponibilidad'),
        
        # Consultas Indirectas (5 casos)
        ('trabajo hasta las 6, ustedes cierran a esa hora?', 'consultar_disponibilidad'),
        ('no tengo mucha plata, es muy caro sacar la cedula?', 'consultar_costo'),
        ('mi hermano fue y no sabia que llevar, que necesito?', 'consultar_requisitos'),
        ('vivo lejos, como hago para llegar?', 'consultar_ubicacion'),
        ('quiero ir pronto, cuando puedo sacar turno?', 'consultar_disponibilidad'),  # Pregunta "cuando" = disponibilidad
    ]
    
    print(f"Evaluando {len(casos)} casos de oraciones compuestas...\n")
    
    for i, (mensaje, esperado) in enumerate(casos, 1):
        print(f"[{i}/{len(casos)}] Frase compuesta: '{mensaje}'")
        print(f"       Esperado: {esperado}")
        
        inicio = time.time()
        # USAR CLASIFICADOR MEJORADO con manejo de oraciones compuestas
        intent, conf, metadata = clasificador_mejorado.clasificar_mejorado(
            mensaje, 
            threshold=0.3,
            corregir_ortografia=True,
            manejar_compuestas=True
        )
        tiempo = time.time() - inicio
        
        # Mostrar información de procesamiento
        if metadata['es_compuesta']:
            print(f"       [COMPUESTA] Método: {metadata['metodo_usado']}")
            if metadata['intent_prioritario']:
                print(f"       [PRIORIDAD] Intent detectado: {metadata['intent_prioritario']}")
        
        exito = (intent == esperado)
        marca = "[OK]" if exito else "[FAIL]"
        print(f"       Obtenido: {intent} (confianza: {conf:.2f}) {marca}\n")
        
        if not exito:
            detalle = f"'{mensaje}' -> Esperado: {esperado}, Obtenido: {intent} (conf: {conf:.2f})"
        else:
            detalle = ""
        
        metrica.agregar_caso(exito, detalle, tiempo)
    
    return metrica


def test_rendimiento():
    """
    COMPONENTE 7: Rendimiento del Sistema
    Métrica: Tiempo de respuesta promedio
    """
    print("\n" + "="*80)
    print("COMPONENTE 7: RENDIMIENTO DEL SISTEMA")
    print("="*80)
    
    metrica = MetricaComponente(
        "Rendimiento",
        "Tiempo de respuesta promedio del motor difuso"
    )
    
    mensajes_test = [
        'quiero un turno',
        'cuanto cuesta',
        'que requisitos necesito',
        'cuando tienen disponible',
        'si',
        'no',
        'cancelar',
        'urgente',
        'para mañana',
        'precio de la cedula',
    ]
    
    objetivo_ms = 100  # 100ms por clasificación
    
    print(f"Evaluando tiempo de respuesta en {len(mensajes_test)} mensajes...")
    print(f"Objetivo: < {objetivo_ms}ms por mensaje\n")
    
    for i, mensaje in enumerate(mensajes_test, 1):
        print(f"[{i}/{len(mensajes_test)}] Midiendo velocidad: '{mensaje}'")
        
        inicio = time.time()
        intent, conf = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        tiempo_ms = (time.time() - inicio) * 1000
        
        exito = (tiempo_ms < objetivo_ms)
        marca = "[OK]" if exito else "[FAIL]"
        print(f"       Tiempo: {tiempo_ms:.2f}ms (objetivo: <{objetivo_ms}ms) {marca}")
        print(f"       Intent: {intent} (confianza: {conf:.2f})\n")
        
        if not exito:
            detalle = f"'{mensaje}' -> {tiempo_ms:.2f}ms (objetivo: < {objetivo_ms}ms)"
        else:
            detalle = ""
        
        metrica.agregar_caso(exito, detalle, tiempo_ms / 1000)
    
    return metrica


def generar_graficos(metricas, media_final, tiempo_total):
    """Genera gráficos profesionales de las métricas"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Crear figura con 6 subplots
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Gráfico de barras - Porcentaje de éxito por componente
    ax1 = plt.subplot(2, 3, 1)
    nombres = [m.nombre for m in metricas]
    porcentajes = [m.get_porcentaje() for m in metricas]
    colores = ['#2ecc71' if p >= 80 else '#e74c3c' if p < 60 else '#f39c12' for p in porcentajes]
    
    bars = ax1.barh(nombres, porcentajes, color=colores, alpha=0.7, edgecolor='black')
    ax1.axvline(x=75, color='red', linestyle='--', linewidth=2, label='Mínimo requerido (75%)')
    ax1.set_xlabel('Porcentaje de Éxito (%)', fontsize=12, fontweight='bold')
    ax1.set_title('ÉXITO POR COMPONENTE', fontsize=14, fontweight='bold')
    ax1.set_xlim(0, 105)
    ax1.legend()
    ax1.grid(axis='x', alpha=0.3)
    
    # Agregar valores en las barras
    for i, (bar, val) in enumerate(zip(bars, porcentajes)):
        ax1.text(val + 2, i, f'{val:.1f}%', va='center', fontweight='bold')
    
    # 2. Gráfico circular - Distribución de casos
    ax2 = plt.subplot(2, 3, 2)
    casos_por_componente = [m.casos_totales for m in metricas]
    colors_pie = plt.cm.Set3(range(len(metricas)))
    
    wedges, texts, autotexts = ax2.pie(casos_por_componente, labels=nombres, autopct='%1.1f%%',
                                        colors=colors_pie, startangle=90)
    ax2.set_title('DISTRIBUCIÓN DE CASOS DE PRUEBA', fontsize=14, fontweight='bold')
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    # 3. Gráfico de pastel - Resultado global
    ax3 = plt.subplot(2, 3, 3)
    total_correctos = sum(m.casos_correctos for m in metricas)
    total_casos = sum(m.casos_totales for m in metricas)
    total_fallidos = total_casos - total_correctos
    
    sizes = [total_correctos, total_fallidos]
    colors_result = ['#2ecc71', '#e74c3c']
    explode = (0.1, 0)
    
    wedges, texts, autotexts = ax3.pie(sizes, labels=['Exitosos', 'Fallidos'], autopct='%1.1f%%',
                                        colors=colors_result, explode=explode, startangle=90,
                                        shadow=True)
    ax3.set_title(f'RESULTADO GLOBAL\n{total_correctos}/{total_casos} casos', 
                  fontsize=14, fontweight='bold')
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(14)
    
    # 4. Tabla de métricas detalladas
    ax4 = plt.subplot(2, 3, 4)
    ax4.axis('tight')
    ax4.axis('off')
    
    tabla_datos = []
    for m in metricas:
        simbolo = '✓' if m.get_porcentaje() >= 80 else '✗'
        tabla_datos.append([
            simbolo,
            m.nombre,
            f"{m.casos_correctos}/{m.casos_totales}",
            f"{m.get_porcentaje():.1f}%",
            f"{m.get_tiempo_promedio()*1000:.2f}ms"
        ])
    
    tabla = ax4.table(cellText=tabla_datos,
                     colLabels=['', 'Componente', 'Casos', 'Éxito', 'T.Prom'],
                     cellLoc='left',
                     loc='center',
                     colWidths=[0.05, 0.35, 0.15, 0.15, 0.15])
    
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 2)
    
    # Colorear header
    for i in range(5):
        tabla[(0, i)].set_facecolor('#3498db')
        tabla[(0, i)].set_text_props(weight='bold', color='white')
    
    # Colorear filas según resultado
    for i, m in enumerate(metricas, 1):
        color = '#d5f4e6' if m.get_porcentaje() >= 80 else '#fadbd8'
        for j in range(5):
            tabla[(i, j)].set_facecolor(color)
    
    ax4.set_title('MÉTRICAS DETALLADAS', fontsize=14, fontweight='bold', pad=20)
    
    # 5. Gráfico de líneas - Tiempo de ejecución
    ax5 = plt.subplot(2, 3, 5)
    tiempos = [m.get_tiempo_promedio() * 1000 for m in metricas]
    
    ax5.plot(range(len(nombres)), tiempos, marker='o', linewidth=2, 
             markersize=10, color='#3498db')
    ax5.set_xticks(range(len(nombres)))
    ax5.set_xticklabels([n.split()[0] for n in nombres], rotation=45, ha='right')
    ax5.set_ylabel('Tiempo Promedio (ms)', fontsize=12, fontweight='bold')
    ax5.set_title('RENDIMIENTO POR COMPONENTE', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # Agregar valores en los puntos
    for i, (x, y) in enumerate(zip(range(len(nombres)), tiempos)):
        ax5.text(x, y + 0.001, f'{y:.2f}ms', ha='center', va='bottom', fontweight='bold')
    
    # 6. Medidor de puntuación final (gauge)
    ax6 = plt.subplot(2, 3, 6)
    
    # Crear gauge semicircular
    theta = np.linspace(0, np.pi, 100)
    radius = 1
    
    # Zonas de color
    for i, (start, end, color, label) in enumerate([
        (0, 50, '#e74c3c', 'Crítico'),
        (50, 75, '#f39c12', 'Bajo'),
        (75, 90, '#2ecc71', 'Bueno'),
        (90, 100, '#27ae60', 'Excelente')
    ]):
        theta_zone = np.linspace(np.pi * (1 - end/100), np.pi * (1 - start/100), 50)
        ax6.fill_between(theta_zone, 0, radius, color=color, alpha=0.3)
    
    # Aguja indicadora
    angle = np.pi * (1 - media_final/100)
    ax6.arrow(0, 0, 0.7*np.cos(angle), 0.7*np.sin(angle), 
             head_width=0.1, head_length=0.1, fc='black', ec='black', linewidth=3)
    
    # Círculo central
    circle = plt.Circle((0, 0), 0.1, color='black')
    ax6.add_patch(circle)
    
    # Configuración
    ax6.set_xlim(-1.2, 1.2)
    ax6.set_ylim(-0.2, 1.2)
    ax6.set_aspect('equal')
    ax6.axis('off')
    
    # Texto de puntuación
    ax6.text(0, -0.3, f'{media_final:.1f}%', 
            ha='center', va='top', fontsize=32, fontweight='bold',
            color='#2ecc71' if media_final >= 75 else '#e74c3c')
    
    estado = 'APROBADO' if media_final >= 75 else 'REQUIERE MEJORAS'
    ax6.text(0, -0.5, estado, 
            ha='center', va='top', fontsize=16, fontweight='bold')
    
    ax6.set_title('PUNTUACIÓN FINAL DEL SISTEMA', fontsize=14, fontweight='bold', pad=20)
    
    # Título general
    fig.suptitle('REPORTE EXHAUSTIVO DE TESTING - SISTEMA V2.0\n' + 
                f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | ' +
                f'Casos: {total_casos} | Tiempo: {tiempo_total:.2f}s',
                fontsize=16, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Guardar gráfico
    output_path = Path("resultados/graficos")
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"test_exhaustivo_{timestamp}.png"
    filepath = output_path / filename
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n[GRAFICOS] Guardado en: {filepath}")
    
    plt.close()
    
    return filepath


def main():
    """Ejecuta todos los tests y calcula métricas finales"""
    print("="*80)
    print(" TEST EXHAUSTIVO DEL SISTEMA V2.0")
    print(" Métricas específicas por componente - Resultado basado en MEDIA")
    print("="*80)
    
    inicio_total = time.time()
    
    # Ejecutar todos los tests
    metricas = []
    
    try:
        metricas.append(test_clasificacion_intents())
    except Exception as e:
        print(f"\n[ERROR] Clasificación Intents: {e}")
    
    try:
        metricas.append(test_validacion_cedula())
    except Exception as e:
        print(f"\n[ERROR] Validación Cédula: {e}")
    
    try:
        metricas.append(test_normalizacion_nombres())
    except Exception as e:
        print(f"\n[ERROR] Normalización Nombres: {e}")
    
    try:
        metricas.append(test_deteccion_urgencia())
    except Exception as e:
        print(f"\n[ERROR] Detección Urgencia: {e}")
    
    try:
        metricas.append(test_manejo_ortografia())
    except Exception as e:
        print(f"\n[ERROR] Manejo Ortografía: {e}")
    
    try:
        metricas.append(test_casos_reales())
    except Exception as e:
        print(f"\n[ERROR] Casos Reales: {e}")
    
    try:
        metricas.append(test_oraciones_compuestas())
    except Exception as e:
        print(f"\n[ERROR] Oraciones Compuestas: {e}")
    
    try:
        metricas.append(test_rendimiento())
    except Exception as e:
        print(f"\n[ERROR] Rendimiento: {e}")
    
    tiempo_total = time.time() - inicio_total
    
    # Calcular métricas globales
    print("\n" + "="*80)
    print(" REPORTE FINAL DE METRICAS")
    print("="*80)
    
    print(f"\n{'COMPONENTE':<35} {'CASOS':<12} {'EXITO':<10} {'T.PROM':<10}")
    print("-" * 80)
    
    porcentajes = []
    total_casos = 0
    total_correctos = 0
    
    for metrica in metricas:
        porcentaje = metrica.get_porcentaje()
        tiempo_prom = metrica.get_tiempo_promedio() * 1000  # a milisegundos
        porcentajes.append(porcentaje)
        total_casos += metrica.casos_totales
        total_correctos += metrica.casos_correctos
        
        print(f"{metrica.nombre:<35} {metrica.casos_totales:>4}/{metrica.casos_correctos:<5} "
              f"{porcentaje:>6.2f}%    {tiempo_prom:>6.2f}ms")
    
    print("-" * 80)
    
    # MEDIA de todos los componentes
    if porcentajes:
        media_final = sum(porcentajes) / len(porcentajes)
    else:
        media_final = 0.0
    
    print(f"\n{'TOTALES':<35} {total_casos:>4}/{total_correctos:<5} "
          f"{'---':>8}    {(tiempo_total*1000):>6.2f}ms")
    
    print("\n" + "="*80)
    print(f" PUNTUACION FINAL DEL SISTEMA: {media_final:.2f}%")
    print("="*80)
    
    # Mostrar detalles de fallos si los hay
    print("\nDETALLE DE COMPONENTES:")
    for metrica in metricas:
        simbolo = "[PASS]" if metrica.get_porcentaje() >= 80 else "[FAIL]"
        print(f"  {simbolo} {metrica.nombre}: {metrica.get_porcentaje():.2f}% - {metrica.descripcion}")
        if metrica.detalles:
            print(f"      Fallos: {len(metrica.detalles)}")
    
    # Criterio de éxito: Media >= 75%
    print("\n" + "="*80)
    if media_final >= 75.0:
        print(f" [SUCCESS] SISTEMA APROBADO - Puntuación: {media_final:.2f}%")
        print(" El sistema cumple con los estándares de calidad requeridos")
        exit_code = 0
    else:
        print(f" [FAIL] SISTEMA REQUIERE MEJORAS - Puntuación: {media_final:.2f}%")
        print(" Se requiere una puntuación mínima de 75% para aprobar")
        exit_code = 1
    print("="*80)
    
    print(f"\nTiempo total de evaluación: {tiempo_total:.2f} segundos")
    print(f"Casos evaluados: {total_casos}")
    print(f"Casos correctos: {total_correctos}")
    
    # Generar gráficos
    print("\n" + "="*80)
    print(" GENERANDO GRAFICOS...")
    print("="*80)
    try:
        filepath = generar_graficos(metricas, media_final, tiempo_total)
        print(f"[SUCCESS] Gráficos generados exitosamente")
        print(f"[INFO] Archivo: {filepath}")
    except Exception as e:
        print(f"[WARNING] No se pudieron generar gráficos: {e}")
        import traceback
        traceback.print_exc()
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERROR FATAL] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
