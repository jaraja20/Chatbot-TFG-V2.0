"""
TEST FINAL: Oraciones Compuestas y Consultas de Usuarios
Meta: Alcanzar mínimo 90% de éxito
"""
# -*- coding: utf-8 -*-

from orquestador_inteligente import procesar_mensaje_inteligente
import time

session_id = f"test_final_{int(time.time())}"

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

print("="*80)
print(f"{Colors.BOLD}{Colors.CYAN}TEST FINAL: ORACIONES COMPUESTAS Y CONSULTAS DE USUARIOS{Colors.END}")
print("="*80)

casos = [
    # ========== CONSULTAS CON CONTEXTO TEMPORAL ==========
    {
        'mensaje': 'necesito un turno para el lunes, hay disponible?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Temporal + Consulta'
    },
    {
        'mensaje': 'quiero ir mañana, a que hora puedo?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Temporal + Consulta'
    },
    {
        'mensaje': 'para el jueves tienen horarios libres?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Temporal + Consulta'
    },
    {
        'mensaje': 'me gustaria ir la semana que viene, cuando hay turnos?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Temporal + Consulta'
    },
    {
        'mensaje': 'tengo libre el miércoles, hay algo disponible ese dia?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Temporal + Consulta'
    },
    
    # ========== AGENDAMIENTO CON CONDICIONES ==========
    {
        'mensaje': 'quiero agendar un turno pero solo puedo por la tarde',
        'intent': 'agendar_turno',
        'categoria': 'Agendar con Condición'
    },
    {
        'mensaje': 'necesito turno urgente, cuando es lo mas rapido?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Agendar con Condición'
    },
    {
        'mensaje': 'puedo sacar turno para hoy mismo?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Agendar con Condición'
    },
    {
        'mensaje': 'quiero reservar pero no se si tienen lugar',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Agendar con Condición'
    },
    {
        'mensaje': 'necesito agendar para antes del viernes',
        'intent': 'agendar_turno',
        'categoria': 'Agendar con Condición'
    },
    
    # ========== MÚLTIPLES CONSULTAS EN UN MENSAJE ==========
    {
        'mensaje': 'hola, donde quedan y que horarios tienen?',
        'intent': 'consultar_ubicacion',  # Primera consulta tiene prioridad
        'categoria': 'Múltiples Consultas'
    },
    {
        'mensaje': 'cuanto sale y que documentos necesito?',
        'intent': 'consultar_costo',
        'categoria': 'Múltiples Consultas'
    },
    {
        'mensaje': 'que requisitos hay y cuanto cuesta el tramite?',
        'intent': 'consultar_requisitos',
        'categoria': 'Múltiples Consultas'
    },
    {
        'mensaje': 'necesito saber donde estan y si tienen turnos para mañana',
        'intent': 'consultar_ubicacion',
        'categoria': 'Múltiples Consultas'
    },
    {
        'mensaje': 'que dias atienden y hasta que hora estan abiertos?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Múltiples Consultas'
    },
    
    # ========== ORACIONES CON MULETILLAS Y CONECTORES ==========
    {
        'mensaje': 'bueno, entonces, me podes decir que horarios hay?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Con Muletillas'
    },
    {
        'mensaje': 'mira, es que necesito turno para la proxima semana',
        'intent': 'agendar_turno',
        'categoria': 'Con Muletillas'
    },
    {
        'mensaje': 'che, y como hago para llegar hasta alli?',
        'intent': 'consultar_ubicacion',
        'categoria': 'Con Muletillas'
    },
    {
        'mensaje': 'disculpa, pero cuanto me va a salir esto?',
        'intent': 'consultar_costo',
        'categoria': 'Con Muletillas'
    },
    {
        'mensaje': 'ey, una pregunta, que papeles tengo que llevar?',
        'intent': 'consultar_requisitos',
        'categoria': 'Con Muletillas'
    },
    
    # ========== CONSULTAS INDIRECTAS ==========
    {
        'mensaje': 'trabajo hasta las 6, ustedes cierran a esa hora?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Indirecta'
    },
    {
        'mensaje': 'mi hermano saco la cedula ahi, como puedo ir?',
        'intent': 'consultar_ubicacion',
        'categoria': 'Indirecta'
    },
    {
        'mensaje': 'no tengo mucha plata, es muy caro sacar la cedula?',
        'intent': 'consultar_costo',
        'categoria': 'Indirecta'
    },
    {
        'mensaje': 'es mi primer tramite de cedula, que tengo que hacer?',
        'intent': 'consultar_requisitos',
        'categoria': 'Indirecta'
    },
    {
        'mensaje': 'vivo lejos de ciudad del este, vale la pena ir hasta alla?',
        'intent': 'consultar_ubicacion',
        'categoria': 'Indirecta'
    },
    
    # ========== PREGUNTAS CON CONTEXTO PERSONAL ==========
    {
        'mensaje': 'soy de encarnacion, tienen sucursal por aca?',
        'intent': 'consultar_ubicacion',
        'categoria': 'Contexto Personal'
    },
    {
        'mensaje': 'tengo 17 años, puedo sacar la cedula solo?',
        'intent': 'consultar_requisitos',
        'categoria': 'Contexto Personal'
    },
    {
        'mensaje': 'perdi mi cedula, cuanto me cobran por una nueva?',
        'intent': 'consultar_costo',
        'categoria': 'Contexto Personal'
    },
    {
        'mensaje': 'soy extranjero, puedo sacar cedula paraguaya?',
        'intent': 'consultar_requisitos',
        'categoria': 'Contexto Personal'
    },
    {
        'mensaje': 'trabajo en brasil, puedo ir los sabados?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Contexto Personal'
    },
    
    # ========== COMPARACIONES Y OPCIONES ==========
    {
        'mensaje': 'es mejor ir por la mañana o por la tarde?',
        'intent': 'frase_ambigua',
        'categoria': 'Comparación'
    },
    {
        'mensaje': 'que dia hay menos gente, lunes o viernes?',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Comparación'
    },
    {
        'mensaje': 'me conviene sacar turno o ir directo?',
        'intent': 'frase_ambigua',
        'categoria': 'Comparación'
    },
    {
        'mensaje': 'cual es mas rapido, turno online o presencial?',
        'intent': 'frase_ambigua',
        'categoria': 'Comparación'
    },
    
    # ========== NEGACIONES Y CORRECCIONES ==========
    {
        'mensaje': 'no, ese horario no me sirve, tenes otro?',
        'intent': 'negacion',
        'categoria': 'Negación'
    },
    {
        'mensaje': 'esa no es mi cedula, me equivoque',
        'intent': 'negacion',
        'categoria': 'Negación'
    },
    {
        'mensaje': 'mejor lo dejo para otro dia',
        'intent': 'negacion',
        'categoria': 'Negación'
    },
    {
        'mensaje': 'no no, mi nombre esta mal escrito',
        'intent': 'negacion',
        'categoria': 'Negación'
    },
    
    # ========== CONSULTAS CON ERRORES ORTOGRÁFICOS ==========
    {
        'mensaje': 'kiero saver ke orarios ay para la semana ke biene',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Ortografía Extrema'
    },
    {
        'mensaje': 'nesecito sakar turno pero no se kuanto bale',
        'intent': 'agendar_turno',
        'categoria': 'Ortografía Extrema'
    },
    {
        'mensaje': 'onde keda la ofi y ke dias trabahan?',
        'intent': 'consultar_ubicacion',
        'categoria': 'Ortografía Extrema'
    },
    {
        'mensaje': 'k papeles tengo k traer para sakar la sedula?',
        'intent': 'consultar_requisitos',
        'categoria': 'Ortografía Extrema'
    },
    
    # ========== FRASES LARGAS Y DESCRIPTIVAS ==========
    {
        'mensaje': 'hola buenos dias, mira te cuento que necesito sacar mi cedula por primera vez y quisiera saber que dias tienen disponible para ir',
        'intent': 'consultar_disponibilidad',
        'categoria': 'Frase Larga'
    },
    {
        'mensaje': 'buenas tardes, disculpa la molestia pero estoy intentando comunicarme hace rato y necesito agendar un turno para la proxima semana si es posible',
        'intent': 'agendar_turno',
        'categoria': 'Frase Larga'
    },
    {
        'mensaje': 'perdon que te moleste pero es urgente, perdi mi cedula hace poco y necesito saber cuanto me va a costar sacar una nueva y que documentos necesito llevar',
        'intent': 'consultar_costo',
        'categoria': 'Frase Larga'
    },
]

# Ejecutar tests
exitosos = 0
fallidos = 0
errores_por_categoria = {}

for i, caso in enumerate(casos, 1):
    resultado = procesar_mensaje_inteligente(caso['mensaje'], session_id)
    intent_detectado = resultado.get('intent')
    confianza = resultado.get('confidence', 0)
    
    if intent_detectado == caso['intent']:
        print(f"{Colors.GREEN}[*]{Colors.END} [{i}/{len(casos)}] {caso['categoria']}")
        print(f"   Mensaje: {caso['mensaje'][:60]}{'...' if len(caso['mensaje']) > 60 else ''}")
        print(f"   Intent: {intent_detectado} ({confianza:.1%})")
        exitosos += 1
    else:
        print(f"{Colors.RED}[*]{Colors.END} [{i}/{len(casos)}] {caso['categoria']}")
        print(f"   Mensaje: {caso['mensaje'][:60]}{'...' if len(caso['mensaje']) > 60 else ''}")
        print(f"   Esperado: {caso['intent']} | Detectado: {intent_detectado} ({confianza:.1%})")
        fallidos += 1
        
        # Contar errores por categoría
        categoria = caso['categoria']
        if categoria not in errores_por_categoria:
            errores_por_categoria[categoria] = []
        errores_por_categoria[categoria].append(caso['mensaje'])
    
    print()

# RESUMEN
print("="*80)
print(f"{Colors.BOLD}{Colors.CYAN}RESUMEN FINAL{Colors.END}")
print("="*80)

tasa_exito = (exitosos / len(casos)) * 100

print(f"\n{Colors.BOLD}Total de casos probados: {len(casos)}{Colors.END}")
print(f"{Colors.GREEN}[[*]] Casos exitosos: {exitosos}{Colors.END}")
print(f"{Colors.RED}[[*]] Casos fallidos: {fallidos}{Colors.END}")
print(f"\n{Colors.BOLD}Tasa de éxito: {tasa_exito:.1f}%{Colors.END}")

if tasa_exito >= 90:
    print(f"\n{Colors.GREEN}{Colors.BOLD}[*] META ALCANZADA: ≥90% de éxito!{Colors.END}")
elif tasa_exito >= 80:
    print(f"\n{Colors.YELLOW}[WARN]  Cerca de la meta (80-90%), necesita ajustes menores{Colors.END}")
else:
    print(f"\n{Colors.RED}[FAIL] Por debajo de la meta (<80%), requiere optimización{Colors.END}")

# Mostrar errores por categoría
if errores_por_categoria:
    print(f"\n{Colors.YELLOW}Errores por categoría:{Colors.END}")
    for categoria, mensajes in errores_por_categoria.items():
        print(f"  • {categoria}: {len(mensajes)} error(es)")
        for msg in mensajes[:2]:  # Mostrar máximo 2 ejemplos
            print(f"    - {msg[:60]}{'...' if len(msg) > 60 else ''}")

print("\n" + "="*80)
