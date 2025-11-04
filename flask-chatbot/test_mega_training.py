"""
Script MEGA de Testing - Casos Reales con Errores, Ambigüedades y Más
Versión completa para entrenar y evaluar el bot
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

def print_header():
    print("="*100)
    print(f"{Colors.BOLD}{Colors.CYAN}TEST MEGA - ENTRENAMIENTO CON CASOS REALES{Colors.END}")
    print(f"{Colors.WHITE}   Errores ortograficos, frases ambiguas, mal escritas, jerga, etc.{Colors.END}")
    print("="*100)
    print()

def test_casos(casos, categoria):
    """Prueba casos y reporta resultados"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*100}")
    print(f"[*] {categoria}")
    print(f"{'='*100}{Colors.END}\n")
    
    session_id = f"test_{int(time.time())}_{categoria.replace(' ', '_')}"
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
                    status = "✅"
                else:
                    color = Colors.RED
                    status = "❌"
                    errores.append({
                        'mensaje': mensaje,
                        'esperado': intent_esperado,
                        'detectado': intent,
                        'confianza': conf
                    })
            else:
                color = Colors.WHITE
                status = "ℹ️"
            
            print(f"{status} {color}Intent: {intent} ({conf:.2%}){Colors.END}")
            print(f"Bot: {respuesta[:150]}{'...' if len(respuesta) > 150 else ''}")
            print()
            
        except Exception as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.END}\n")
            errores.append({
                'mensaje': mensaje,
                'error': str(e)
            })
    
    return errores

def main():
    print_header()
    
    todos_errores = []
    
    # ==========================================
    # 1. ERRORES ORTOGRÁFICOS
    # ==========================================
    ortografia = [
        {'mensaje': 'ola quisiera agendar un turno', 'intent': 'agendar_turno'},
        {'mensaje': 'kiero sakar un turno', 'intent': 'agendar_turno'},
        {'mensaje': 'nesecito un turno x favor', 'intent': 'agendar_turno'},
        {'mensaje': 'q horarios tienen disponibles?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'ay turnos para mañana?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'k documentos nececito llevar', 'intent': 'consultar_requisitos'},
        {'mensaje': 'cuanto bale sacar la cedula?', 'intent': 'consultar_costo'},
        {'mensaje': 'donde keda la oficina?', 'intent': 'consultar_ubicacion'},
    ]
    
    todos_errores.extend(test_casos(ortografia, "[1] ERRORES ORTOGRAFICOS"))
    
    # ==========================================
    # 2. FRASES AMBIGUAS
    # ==========================================
    ambiguas = [
        {'mensaje': 'necesito para mañana', 'intent': 'agendar_turno'},
        {'mensaje': 'cuando es posible?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'tienen algo libre?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'dame uno', 'intent': 'agendar_turno'},
        {'mensaje': 'para hoy', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'el mejor', 'intent': 'frase_ambigua'},
        {'mensaje': 'lo antes posible', 'intent': 'frase_ambigua'},
        {'mensaje': 'temprano', 'intent': 'frase_ambigua'},
        {'mensaje': 'que me recomiendas?', 'intent': 'frase_ambigua'},
    ]
    
    todos_errores.extend(test_casos(ambiguas, "[2] FRASES AMBIGUAS"))
    
    # ==========================================
    # 3. GRAMÁTICA INCORRECTA
    # ==========================================
    gramatica = [
        {'mensaje': 'yo querer turno', 'intent': 'agendar_turno'},
        {'mensaje': 'que hora hay libre?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'para sacar cedula que necesita?', 'intent': 'consultar_requisitos'},
        {'mensaje': 'hay turno para mi?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'yo poder ir mañana?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'cuanto es costo?', 'intent': 'consultar_costo'},
    ]
    
    todos_errores.extend(test_casos(gramatica, "[3] GRAMATICA INCORRECTA"))
    
    # ==========================================
    # 4. FRASES MUY CORTAS (1 PALABRA)
    # ==========================================
    cortas = [
        {'mensaje': 'turno', 'intent': 'agendar_turno'},
        {'mensaje': 'hoy', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'mañana', 'intent': 'informar_fecha'},
        {'mensaje': 'requisitos', 'intent': 'consultar_requisitos'},
        {'mensaje': 'costo', 'intent': 'consultar_costo'},
        {'mensaje': 'horarios', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'ubicacion', 'intent': 'consultar_ubicacion'},
        {'mensaje': 'documentos', 'intent': 'consultar_requisitos'},
    ]
    
    todos_errores.extend(test_casos(cortas, "[4] FRASES MUY CORTAS (1 PALABRA)"))
    
    # ==========================================
    # 5. JERGA Y COLOQUIALISMOS
    # ==========================================
    jerga = [
        {'mensaje': 'che, tienen lugar para hoy?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'buenas, para cuando hay hueco?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'vieja, necesito sacar turno urgente', 'intent': 'agendar_turno'},
        {'mensaje': 'amigo quiero un turno nomás', 'intent': 'agendar_turno'},
        {'mensaje': 'que onda con los turnos?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'bo, hay turnos?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'mba epa, como hago?', 'intent': 'greet'},  # greet es correcto (equivalente a saludos)
    ]
    
    todos_errores.extend(test_casos(jerga, "[5] JERGA Y COLOQUIALISMOS"))
    
    # ==========================================
    # 6. PREGUNTAS COMPLEJAS
    # ==========================================
    complejas = [
        {'mensaje': 'quiero saber si tienen turnos disponibles para mañana en la mañana temprano porque trabajo en la tarde', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'necesito agendar un turno pero no se que documentos llevar ni cuanto cuesta', 'intent': 'agendar_turno'},
        {'mensaje': 'hola buen día quisiera saber como hago para sacar la cédula por primera vez y que necesito traer', 'intent': 'consultar_requisitos'},
        {'mensaje': 'disculpa, me podrías decir si para el viernes hay horarios libres? es que solo puedo ese día', 'intent': 'consultar_disponibilidad'},
    ]
    
    todos_errores.extend(test_casos(complejas, "[6] PREGUNTAS COMPLEJAS (MULTIPLES INTENTS)"))
    
    # ==========================================
    # 7. CONSULTAS ESPECIALES DE DISPONIBILIDAD
    # ==========================================
    disponibilidad = [
        {'mensaje': 'dame un dia intermedio de la semana', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'que dia esta mas libre?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'hoy no tienen disponible?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'para hoy no están?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'cual es el mejor dia para ir?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'que dia me recomendas?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'cuando hay menos gente?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'que día hay más espacio?', 'intent': 'consultar_disponibilidad'},
    ]
    
    todos_errores.extend(test_casos(disponibilidad, "[7] CONSULTAS ESPECIALES DISPONIBILIDAD"))
    
    # ==========================================
    # 8. MENSAJES INFORMALES
    # ==========================================
    informales = [
        {'mensaje': 'hola quiero un turno', 'intent': 'agendar_turno'},
        {'mensaje': 'necesito turno porfaaa', 'intent': 'agendar_turno'},
        {'mensaje': 'hay para mañana???', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'gracias!!!', 'intent': 'agradecimiento'},
        {'mensaje': 'no hay turnos?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'porfa urgente!!!', 'intent': 'agendar_turno'},
    ]
    
    todos_errores.extend(test_casos(informales, "[8] MENSAJES INFORMALES"))
    
    # ==========================================
    # 9. NEGACIONES Y CORRECCIONES
    # ==========================================
    negaciones = [
        {'mensaje': 'no, esa hora no me sirve', 'intent': 'negacion'},
        {'mensaje': 'no puedo a esa hora', 'intent': 'negacion'},
        {'mensaje': 'mejor otro día', 'intent': 'negacion'},
        {'mensaje': 'no me llamo así', 'intent': 'negacion'},
        {'mensaje': 'no ese no es mi email', 'intent': 'negacion'},
        {'mensaje': 'cancelar', 'intent': 'cancelar'},
    ]
    
    todos_errores.extend(test_casos(negaciones, "[9] NEGACIONES Y CORRECCIONES"))
    
    # ==========================================
    # 10. CONSULTAS POR FRANJA HORARIA
    # ==========================================
    franjas = [
        {'mensaje': 'que horarios hay en la mañana?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'disponibilidad por la tarde?', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'tienen temprano?', 'intent': 'frase_ambigua'},
        {'mensaje': 'solo puedo ir despues del mediodia', 'intent': 'consultar_disponibilidad'},
        {'mensaje': 'antes de las 10', 'intent': 'frase_ambigua'},
    ]
    
    todos_errores.extend(test_casos(franjas, "[10] CONSULTAS POR FRANJA HORARIA"))
    
    # ==========================================
    # RESUMEN FINAL
    # ==========================================
    print("\n" + "="*100)
    print(f"{Colors.BOLD}{Colors.CYAN}[*] RESUMEN FINAL{Colors.END}")
    print("="*100)
    
    total_casos = (len(ortografia) + len(ambiguas) + len(gramatica) + len(cortas) + 
                   len(jerga) + len(complejas) + len(disponibilidad) + len(informales) + 
                   len(negaciones) + len(franjas))
    
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
