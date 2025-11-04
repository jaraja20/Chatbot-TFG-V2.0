"""
Test de Validación con NUEVAS variaciones
Para verificar que el bot realmente aprendió (no solo memorizó)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente
from datetime import datetime
import time

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def test_casos(casos, categoria):
    """Prueba casos y reporta resultados"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*100}")
    print(f"[*] {categoria}")
    print(f"{'='*100}{Colors.END}\n")
    
    session_id = f"test_validacion_{int(time.time())}_{categoria.replace(' ', '_')}"
    errores = []
    
    for i, caso in enumerate(casos, 1):
        mensaje = caso['mensaje']
        intent_esperado = caso.get('intent', 'N/A')
        
        print(f"{Colors.YELLOW}[{i}/{len(casos)}] Usuario:{Colors.END} {mensaje}")
        
        try:
            resultado = procesar_mensaje_inteligente(mensaje, session_id)
            
            intent = resultado.get('intent', 'unknown')
            respuesta = resultado.get('text', str(resultado))
            conf = resultado.get('confidence', 0.0)
            
            # Color según resultado
            if intent_esperado != 'N/A':
                if intent == intent_esperado:
                    color = Colors.GREEN
                    status = "[OK]"
                else:
                    color = Colors.RED
                    status = "[X]"
                    errores.append({
                        'mensaje': mensaje,
                        'esperado': intent_esperado,
                        'detectado': intent,
                        'confianza': conf
                    })
            else:
                color = Colors.WHITE
                status = "[i]"
            
            print(f"{status} {color}Intent: {intent} ({conf:.2%}){Colors.END}")
            print(f"Bot: {respuesta[:120]}{'...' if len(respuesta) > 120 else ''}")
            print()
            
        except Exception as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.END}\n")
            errores.append({
                'mensaje': mensaje,
                'error': str(e)
            })
    
    return errores

def main():
    print("="*100)
    print(f"{Colors.BOLD}{Colors.CYAN}TEST DE VALIDACION - NUEVAS VARIACIONES{Colors.END}")
    print(f"{Colors.WHITE}   Probando con palabras DIFERENTES a las del entrenamiento{Colors.END}")
    print("="*100)
    print()
    
    todos_errores = []
    
    # ==========================================
    # 1. VARIACIONES ORTOGRÁFICAS NUEVAS
    # ==========================================
    ortografia_nuevas = [
        {'mensaje': 'ola kmo estas', 'intent': 'greet'},
        {'mensaje': 'kieroo un turno plss', 'intent': 'agendar_turno'},
        {'mensaje': 'nesesito sakar un turno', 'intent': 'agendar_turno'},
        {'mensaje': 'qe papeles tengo ke traer?', 'intent': 'consultar_requisitos'},
        {'mensaje': 'kuanto kuesta el tramite?', 'intent': 'consultar_costo'},
        {'mensaje': 'adonde keda la ofi?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'ai horarios para pasado mañana?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'ke dias trabajan?', 'intent': 'consultar_disponibilidad'},
    ]
    
    todos_errores.extend(test_casos(ortografia_nuevas, "[1] VARIACIONES ORTOGRAFICAS NUEVAS"))
    
    # ==========================================
    # 2. SINÓNIMOS Y PALABRAS SIMILARES
    # ==========================================
    sinonimos = [
        {'mensaje': 'reservar una cita', 'intent': 'agendar_turno'},
        {'mensaje': 'apartar un horario', 'intent': 'agendar_turno'},
        {'mensaje': 'conseguir un cupo', 'intent': 'agendar_turno'},
        {'mensaje': 'solicitar un turno', 'intent': 'agendar_turno'},
        {'mensaje': 'que horas están libres?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'que franjas horarias tienen?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'a que hora abren?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'en que lugar se encuentran?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'cual es la direccion exacta?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'cuanto me sale el tramite?', 'intent': 'consultar_costo'},
        {'mensaje': 'que precio tiene?', 'intent': 'consultar_costo'},
    ]
    
    todos_errores.extend(test_casos(sinonimos, "[2] SINONIMOS Y PALABRAS SIMILARES"))
    
    # ==========================================
    # 3. ESTRUCTURAS GRAMATICALES DIFERENTES
    # ==========================================
    gramatica_diferente = [
        {'mensaje': 'podria agendar para la proxima semana?', 'intent': 'agendar_turno'},
        {'mensaje': 'me gustaria saber si hay disponibilidad', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'sera posible ir el jueves?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'tengo que llevar algun documento?', 'intent': 'consultar_requisitos'},
        {'mensaje': 'debo pagar algo?', 'intent': 'consultar_costo'},
        {'mensaje': 'como puedo llegar hasta alli?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'hay algun telefono de contacto?', 'intent': 'consultar_ubicacion'},
    ]
    
    todos_errores.extend(test_casos(gramatica_diferente, "[3] ESTRUCTURAS GRAMATICALES DIFERENTES"))
    
    # ==========================================
    # 4. PREGUNTAS INDIRECTAS Y CONTEXTUALES
    # ==========================================
    indirectas = [
        {'mensaje': 'trabajo hasta las 5, puedo ir despues?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'estudio por la mañana, tienen por la tarde?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'vivo lejos, donde quedan?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'no tengo mucho dinero, es caro?', 'intent': 'consultar_costo'},
        {'mensaje': 'es mi primer tramite, que necesito?', 'intent': 'consultar_requisitos'},
        {'mensaje': 'nunca fui, como hago?', 'intent': 'consultar_requisitos'},
    ]
    
    todos_errores.extend(test_casos(indirectas, "[4] PREGUNTAS INDIRECTAS Y CONTEXTUALES"))
    
    # ==========================================
    # 5. COMBINACIONES COMPLEJAS NUEVAS
    # ==========================================
    complejas_nuevas = [
        {'mensaje': 'buenas tardes, quisiera informacion sobre los turnos disponibles esta semana', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'me urge sacar la cedula, cuando es lo mas pronto que puedo ir?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'disculpe la molestia, podria decirme cuales son los requisitos?', 'intent': 'consultar_requisitos'},
        {'mensaje': 'perdon, no se donde queda la oficina, me das la direccion?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'hola! necesito agendar pero no se cuanto cuesta ni que documentos llevar', 'intent': 'agendar_turno'},
    ]
    
    todos_errores.extend(test_casos(complejas_nuevas, "[5] COMBINACIONES COMPLEJAS NUEVAS"))
    
    # ==========================================
    # 6. JERGA Y EXPRESIONES LOCALES NUEVAS
    # ==========================================
    jerga_nueva = [
        {'mensaje': 'ndeee, tenes turno disponible?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'ey amigo dame un horario', 'intent': 'agendar_turno'},
        {'mensaje': 'epa hermano, donde estan ubicados?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'cuanto me cobran luego?', 'intent': 'consultar_costo'},
        {'mensaje': 'que papeles luego necesito?', 'intent': 'consultar_requisitos'},
    ]
    
    todos_errores.extend(test_casos(jerga_nueva, "[6] JERGA Y EXPRESIONES LOCALES NUEVAS"))
    
    # ==========================================
    # 7. ABREVIACIONES Y LENGUAJE INFORMAL
    # ==========================================
    informal = [
        {'mensaje': 'q onda, hay turnos?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'ncs turno xfa', 'intent': 'agendar_turno'},
        {'mensaje': 'info x favor', 'intent': 'consultar_requisitos'},
        {'mensaje': 'cuant sale?', 'intent': 'consultar_costo'},
        {'mensaje': 'dnd quedan?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'tlf de contacto?', 'intent': 'consultar_ubicacion'},
    ]
    
    todos_errores.extend(test_casos(informal, "[7] ABREVIACIONES Y LENGUAJE INFORMAL"))
    
    # ==========================================
    # 8. NEGACIONES Y CORRECCIONES VARIADAS
    # ==========================================
    negaciones_nuevas = [
        {'mensaje': 'ese horario no me viene bien', 'intent': 'negacion'},
        {'mensaje': 'prefiero otro dia', 'intent': 'negacion'},
        {'mensaje': 'no es mi nombre correcto', 'intent': 'negacion'},
        {'mensaje': 'equivocaste mi email', 'intent': 'negacion'},
        {'mensaje': 'mejor lo cancelo', 'intent': 'cancelar'},
        {'mensaje': 'ya no quiero el turno', 'intent': 'cancelar'},
    ]
    
    todos_errores.extend(test_casos(negaciones_nuevas, "[8] NEGACIONES Y CORRECCIONES VARIADAS"))
    
    # ==========================================
    # 9. CONSULTAS AMBIGUAS EXTREMAS
    # ==========================================
    ambiguas_extremas = [
        {'mensaje': 'cual seria?', 'intent': 'frase_ambigua'},
        {'mensaje': 'ese mismo', 'intent': 'frase_ambigua'},
        {'mensaje': 'lo que tengan', 'intent': 'frase_ambigua'},
        {'mensaje': 'el que sea', 'intent': 'frase_ambigua'},
        {'mensaje': 'cualquiera me sirve', 'intent': 'frase_ambigua'},
    ]
    
    todos_errores.extend(test_casos(ambiguas_extremas, "[9] CONSULTAS AMBIGUAS EXTREMAS"))
    
    # ==========================================
    # 10. CONSULTAS SOBRE CONTACTO
    # ==========================================
    contacto = [
        {'mensaje': 'tienen telefono?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'numero de contacto?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'como los puedo contactar?', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'tienen whatsapp?', 'intent': 'consultar_ubicacion'},
    ]
    
    todos_errores.extend(test_casos(contacto, "[10] CONSULTAS SOBRE CONTACTO"))
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "="*100)
    print(f"{Colors.BOLD}{Colors.CYAN}[*] RESUMEN FINAL - TEST DE VALIDACION{Colors.END}")
    print("="*100)
    
    total_casos = (len(ortografia_nuevas) + len(sinonimos) + len(gramatica_diferente) + 
                   len(indirectas) + len(complejas_nuevas) + len(jerga_nueva) + 
                   len(informal) + len(negaciones_nuevas) + len(ambiguas_extremas) + len(contacto))
    
    total_errores = len([e for e in todos_errores if 'esperado' in e])
    tasa_exito = ((total_casos - total_errores) / total_casos * 100) if total_casos > 0 else 0
    
    print(f"\n{Colors.WHITE}Total de casos probados: {Colors.BOLD}{total_casos}{Colors.END}")
    print(f"{Colors.GREEN}[OK] Casos exitosos: {Colors.BOLD}{total_casos - total_errores}{Colors.END}")
    print(f"{Colors.RED}[X] Casos con errores: {Colors.BOLD}{total_errores}{Colors.END}")
    print(f"{Colors.CYAN}Tasa de exito: {Colors.BOLD}{tasa_exito:.1f}%{Colors.END}\n")
    
    if total_errores > 0:
        print(f"{Colors.YELLOW}{'='*100}")
        print(f"[!] CASOS QUE FALLARON:{Colors.END}")
        print("="*100)
        
        for i, error in enumerate([e for e in todos_errores if 'esperado' in e], 1):
            print(f"\n{Colors.RED}[{i}]{Colors.END} {error['mensaje']}")
            print(f"    {Colors.YELLOW}Esperado:{Colors.END} {error['esperado']}")
            print(f"    {Colors.RED}Detectado:{Colors.END} {error['detectado']} ({error['confianza']:.2%})")
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[!] TODOS LOS CASOS PASARON CORRECTAMENTE!{Colors.END}")
    
    print("\n" + "="*100 + "\n")

if __name__ == "__main__":
    main()
