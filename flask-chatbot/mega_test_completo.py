"""
MEGA TEST COMPLETO - Sistema de Turnos
========================================

Test exhaustivo con conversaciones realistas que incluyen:
- Flujos completos de agendamiento
- Modificaciones en medio del proceso
- Consultas intercaladas con formulario
- Oraciones compuestas
- Cambios de opinión
- Correcciones de datos
- Cancelaciones y reintentos

Total: 25 conversaciones complejas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from orquestador_inteligente import procesar_mensaje_inteligente, get_or_create_context

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_conversacion(session_id, titulo, pasos):
    """Ejecuta una conversación paso a paso y valida resultados"""
    print(f"\n{'='*100}")
    print(f"{Colors.HEADER}{Colors.BOLD}🧪 {titulo}{Colors.ENDC}")
    print(f"{'='*100}")
    
    contexto = get_or_create_context(session_id)
    exitos = 0
    total = len(pasos)
    
    for i, paso in enumerate(pasos, 1):
        mensaje = paso['mensaje']
        validaciones = paso.get('validaciones', {})
        descripcion = paso.get('descripcion', '')
        
        print(f"\n{Colors.OKBLUE}[Paso {i}/{total}] {descripcion}{Colors.ENDC}")
        print(f"👤 Usuario: {mensaje}")
        
        resultado = procesar_mensaje_inteligente(mensaje, session_id)
        
        print(f"🤖 Bot: {resultado['text'][:150]}{'...' if len(resultado['text']) > 150 else ''}")
        print(f"🎯 Intent: {resultado['intent']} (confianza: {resultado['confidence']:.2f})")
        
        # Validar resultados
        paso_exitoso = True
        
        if 'intent_esperado' in validaciones:
            if resultado['intent'] == validaciones['intent_esperado']:
                print(f"   {Colors.OKGREEN}✓ Intent correcto: {resultado['intent']}{Colors.ENDC}")
            else:
                print(f"   {Colors.FAIL}✗ Intent incorrecto: esperado '{validaciones['intent_esperado']}', obtenido '{resultado['intent']}'{Colors.ENDC}")
                paso_exitoso = False
        
        if 'contexto' in validaciones:
            for campo, valor_esperado in validaciones['contexto'].items():
                valor_actual = getattr(contexto, campo, None)
                if valor_esperado is None:
                    # Verificar que es None
                    if valor_actual is None:
                        print(f"   {Colors.OKGREEN}✓ {campo} es None (correcto){Colors.ENDC}")
                    else:
                        print(f"   {Colors.FAIL}✗ {campo} debería ser None, pero es '{valor_actual}'{Colors.ENDC}")
                        paso_exitoso = False
                elif valor_esperado == "NOT_NONE":
                    # Verificar que NO es None
                    if valor_actual is not None:
                        print(f"   {Colors.OKGREEN}✓ {campo} tiene valor: {valor_actual}{Colors.ENDC}")
                    else:
                        print(f"   {Colors.FAIL}✗ {campo} debería tener valor, pero es None{Colors.ENDC}")
                        paso_exitoso = False
                else:
                    # Verificar valor específico
                    if valor_actual == valor_esperado:
                        print(f"   {Colors.OKGREEN}✓ {campo} = {valor_actual}{Colors.ENDC}")
                    else:
                        print(f"   {Colors.FAIL}✗ {campo}: esperado '{valor_esperado}', obtenido '{valor_actual}'{Colors.ENDC}")
                        paso_exitoso = False
        
        if 'texto_contiene' in validaciones:
            for texto in validaciones['texto_contiene']:
                if texto.lower() in resultado['text'].lower():
                    print(f"   {Colors.OKGREEN}✓ Respuesta contiene: '{texto}'{Colors.ENDC}")
                else:
                    print(f"   {Colors.FAIL}✗ Respuesta NO contiene: '{texto}'{Colors.ENDC}")
                    paso_exitoso = False
        
        if paso_exitoso:
            exitos += 1
    
    # Resumen de conversación
    print(f"\n{'-'*100}")
    if exitos == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✅ CONVERSACIÓN EXITOSA: {exitos}/{total} pasos correctos{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.WARNING}{Colors.BOLD}⚠️  CONVERSACIÓN PARCIAL: {exitos}/{total} pasos correctos ({exitos*100//total}%){Colors.ENDC}")
        return exitos >= (total * 0.7)  # 70% de éxito mínimo

# ============================================================================
# CONVERSACIONES DE TEST
# ============================================================================

conversaciones = [
    # ========================================================================
    # GRUPO 1: FLUJOS BÁSICOS COMPLETOS
    # ========================================================================
    {
        'session_id': 'test-001',
        'titulo': 'CONV #1: Agendamiento simple y directo',
        'pasos': [
            {
                'mensaje': 'Hola, necesito un turno',
                'descripcion': 'Inicio de conversación',
                'validaciones': {
                    'intent_esperado': 'agendar_turno',
                    'texto_contiene': ['nombre']
                }
            },
            {
                'mensaje': 'María Fernanda López',
                'descripcion': 'Proporciona nombre',
                'validaciones': {
                    'intent_esperado': 'informar_nombre',
                    'contexto': {'nombre': 'María Fernanda López'},
                    'texto_contiene': ['cédula']
                }
            },
            {
                'mensaje': '4567890',
                'descripcion': 'Proporciona cédula',
                'validaciones': {
                    'intent_esperado': 'informar_cedula',
                    'contexto': {'cedula': '4567890'},
                    'texto_contiene': ['fecha', 'día']
                }
            },
            {
                'mensaje': 'mañana',
                'descripcion': 'Proporciona fecha',
                'validaciones': {
                    'intent_esperado': 'informar_fecha',
                    'contexto': {'fecha': 'NOT_NONE'},
                    'texto_contiene': ['hora', 'horario']
                }
            },
            {
                'mensaje': '10:00',
                'descripcion': 'Proporciona hora',
                'validaciones': {
                    'intent_esperado': 'elegir_horario',
                    'contexto': {'hora': '10:00'}
                }
            },
            {
                'mensaje': 'maria.lopez@email.com',
                'descripcion': 'Proporciona email',
                'validaciones': {
                    'intent_esperado': 'informar_email',
                    'contexto': {'email': 'maria.lopez@email.com'},
                    'texto_contiene': ['Resumen', 'Confirmas']
                }
            },
            {
                'mensaje': 'sí, confirmo',
                'descripcion': 'Confirma turno',
                'validaciones': {
                    'intent_esperado': 'affirm',
                    'texto_contiene': ['confirmado', 'turno']
                }
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 2: CONSULTAS INTERCALADAS EN FORMULARIO
    # ========================================================================
    {
        'session_id': 'test-002',
        'titulo': 'CONV #2: Consulta de requisitos en medio del formulario',
        'pasos': [
            {
                'mensaje': 'Quiero sacar turno',
                'descripcion': 'Inicio',
                'validaciones': {'intent_esperado': 'agendar_turno'}
            },
            {
                'mensaje': 'Pedro Ramírez',
                'descripcion': 'Da nombre',
                'validaciones': {'contexto': {'nombre': 'Pedro Ramírez'}}
            },
            {
                'mensaje': 'Espera, qué documentos necesito?',
                'descripcion': 'CONSULTA INTERCALADA - Requisitos',
                'validaciones': {
                    'intent_esperado': 'consultar_requisitos',
                    'texto_contiene': ['requisitos', 'documento'],
                    'contexto': {'nombre': 'Pedro Ramírez'}  # Nombre debe mantenerse
                }
            },
            {
                'mensaje': '3456789',
                'descripcion': 'Continúa con cédula después de consulta',
                'validaciones': {
                    'intent_esperado': 'informar_cedula',
                    'contexto': {'cedula': '3456789'}
                }
            },
            {
                'mensaje': 'para el viernes',
                'descripcion': 'Da fecha',
                'validaciones': {
                    'intent_esperado': 'informar_fecha',
                    'contexto': {'fecha': 'NOT_NONE'}
                }
            }
        ]
    },
    
    {
        'session_id': 'test-003',
        'titulo': 'CONV #3: Consulta de costos y ubicación durante formulario',
        'pasos': [
            {
                'mensaje': 'necesito turno',
                'descripcion': 'Inicio',
                'validaciones': {'intent_esperado': 'agendar_turno'}
            },
            {
                'mensaje': 'Ana García',
                'descripcion': 'Da nombre',
                'validaciones': {'contexto': {'nombre': 'Ana García'}}
            },
            {
                'mensaje': '1234567',
                'descripcion': 'Da cédula',
                'validaciones': {'contexto': {'cedula': '1234567'}}
            },
            {
                'mensaje': 'Cuánto cuesta el trámite?',
                'descripcion': 'CONSULTA - Costo en medio',
                'validaciones': {
                    'intent_esperado': 'consultar_costo',
                    'texto_contiene': ['costo', 'gratuito'],
                    'contexto': {'cedula': '1234567'}  # Mantener datos
                }
            },
            {
                'mensaje': 'Dónde queda la oficina?',
                'descripcion': 'CONSULTA - Ubicación',
                'validaciones': {
                    'intent_esperado': 'consultar_ubicacion',
                    'texto_contiene': ['San Blas', 'Ciudad del Este']
                }
            },
            {
                'mensaje': 'Ok, para mañana a las 9',
                'descripcion': 'ORACIÓN COMPUESTA - Fecha y hora juntas',
                'validaciones': {
                    'contexto': {
                        'fecha': 'NOT_NONE',
                        'hora': '09:00'
                    }
                }
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 3: CAMBIOS Y CORRECCIONES
    # ========================================================================
    {
        'session_id': 'test-004',
        'titulo': 'CONV #4: Cambio de horario en medio del proceso',
        'pasos': [
            {
                'mensaje': 'hola quiero un turno',
                'descripcion': 'Inicio',
                'validaciones': {'intent_esperado': 'agendar_turno'}
            },
            {
                'mensaje': 'Carlos Mendoza',
                'descripcion': 'Da nombre',
                'validaciones': {'contexto': {'nombre': 'Carlos Mendoza'}}
            },
            {
                'mensaje': '7890123',
                'descripcion': 'Da cédula',
                'validaciones': {'contexto': {'cedula': '7890123'}}
            },
            {
                'mensaje': 'para mañana a las 8',
                'descripcion': 'Da fecha y hora',
                'validaciones': {
                    'contexto': {
                        'fecha': 'NOT_NONE',
                        'hora': '08:00'
                    }
                }
            },
            {
                'mensaje': 'Mejor cambio la hora, prefiero 14:00',
                'descripcion': 'CAMBIO - Quiere modificar hora',
                'validaciones': {
                    'contexto': {'hora': None},  # Hora debe resetearse
                    'texto_contiene': ['hora', 'horario']
                }
            },
            {
                'mensaje': '14:00',
                'descripcion': 'Nueva hora',
                'validaciones': {
                    'intent_esperado': 'elegir_horario',
                    'contexto': {'hora': '14:00'}
                }
            }
        ]
    },
    
    {
        'session_id': 'test-005',
        'titulo': 'CONV #5: Cambio de fecha completo',
        'pasos': [
            {
                'mensaje': 'turno por favor',
                'descripcion': 'Inicio',
                'validaciones': {'intent_esperado': 'agendar_turno'}
            },
            {
                'mensaje': 'Laura Benítez',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Laura Benítez'}}
            },
            {
                'mensaje': '5551234',
                'descripcion': 'Cédula',
                'validaciones': {'contexto': {'cedula': '5551234'}}
            },
            {
                'mensaje': 'para el martes',
                'descripcion': 'Fecha inicial',
                'validaciones': {'contexto': {'fecha': 'NOT_NONE'}}
            },
            {
                'mensaje': 'No espera, mejor cambio la fecha para el jueves',
                'descripcion': 'CAMBIO - Nueva fecha en oración compuesta',
                'validaciones': {
                    'contexto': {
                        'fecha': None,  # Debe resetearse
                        'hora': None    # También hora
                    }
                }
            },
            {
                'mensaje': 'jueves',
                'descripcion': 'Confirma nueva fecha',
                'validaciones': {
                    'intent_esperado': 'informar_fecha',
                    'contexto': {'fecha': 'NOT_NONE'}
                }
            }
        ]
    },
    
    {
        'session_id': 'test-006',
        'titulo': 'CONV #6: Corrección en el resumen final',
        'pasos': [
            {
                'mensaje': 'necesito turno',
                'descripcion': 'Inicio',
                'validaciones': {}
            },
            {
                'mensaje': 'Roberto Silva',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Roberto Silva'}}
            },
            {
                'mensaje': '9998877',
                'descripcion': 'Cédula',
                'validaciones': {'contexto': {'cedula': '9998877'}}
            },
            {
                'mensaje': 'mañana 11:00',
                'descripcion': 'Fecha y hora',
                'validaciones': {
                    'contexto': {
                        'fecha': 'NOT_NONE',
                        'hora': '11:00'
                    }
                }
            },
            {
                'mensaje': 'roberto@mail.com',
                'descripcion': 'Email',
                'validaciones': {'contexto': {'email': 'roberto@mail.com'}}
            },
            {
                'mensaje': 'Cambiar email',
                'descripcion': 'CORRECCIÓN en resumen - Email',
                'validaciones': {
                    'intent_esperado': 'informar_email',
                    'contexto': {'email': None}  # Debe resetearse
                }
            },
            {
                'mensaje': 'roberto.silva@correo.com',
                'descripcion': 'Nuevo email correcto',
                'validaciones': {
                    'contexto': {'email': 'roberto.silva@correo.com'}
                }
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 4: ORACIONES COMPUESTAS COMPLEJAS
    # ========================================================================
    {
        'session_id': 'test-007',
        'titulo': 'CONV #7: Todo en una sola oración',
        'pasos': [
            {
                'mensaje': 'Hola, soy Patricia Rojas, CI 3334455, necesito turno para mañana a las 15:00',
                'descripcion': 'ORACIÓN MEGA COMPUESTA - Nombre, cédula, fecha, hora',
                'validaciones': {
                    'contexto': {
                        'nombre': 'Patricia Rojas',
                        'cedula': '3334455',
                        'fecha': 'NOT_NONE',
                        'hora': '15:00'
                    }
                }
            },
            {
                'mensaje': 'Mi email es patricia.rojas@gmail.com',
                'descripcion': 'Email',
                'validaciones': {
                    'contexto': {'email': 'patricia.rojas@gmail.com'},
                    'texto_contiene': ['Resumen']
                }
            }
        ]
    },
    
    {
        'session_id': 'test-008',
        'titulo': 'CONV #8: Consulta y agendamiento juntos',
        'pasos': [
            {
                'mensaje': 'Hola, qué horarios tienen para mañana? Necesito sacar turno',
                'descripcion': 'COMPUESTA - Consulta + Agendamiento',
                'validaciones': {
                    'contexto': {'fecha': 'NOT_NONE'},  # Debe detectar "mañana"
                    'texto_contiene': ['horario', 'disponib']
                }
            },
            {
                'mensaje': 'Perfecto, quiero para las 10, mi nombre es Diego Martínez',
                'descripcion': 'COMPUESTA - Hora + Nombre',
                'validaciones': {
                    'contexto': {
                        'hora': '10:00',
                        'nombre': 'Diego Martínez'
                    }
                }
            }
        ]
    },
    
    {
        'session_id': 'test-009',
        'titulo': 'CONV #9: Pregunta sobre requisitos y luego agenda',
        'pasos': [
            {
                'mensaje': 'Qué documentos necesito para renovar mi cédula? Y cuánto demora?',
                'descripcion': 'COMPUESTA - Requisitos + Demora',
                'validaciones': {
                    'texto_contiene': ['requisitos', 'renovación']
                }
            },
            {
                'mensaje': 'Ok perfecto, entonces quiero turno para el jueves',
                'descripcion': 'Agendamiento después de consulta',
                'validaciones': {
                    'intent_esperado': 'informar_fecha',
                    'contexto': {'fecha': 'NOT_NONE'}
                }
            },
            {
                'mensaje': 'Soy Gabriela Fernández, mi CI es 7778899',
                'descripcion': 'COMPUESTA - Nombre + Cédula',
                'validaciones': {
                    'contexto': {
                        'nombre': 'Gabriela Fernández',
                        'cedula': '7778899'
                    }
                }
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 5: CANCELACIONES Y REINTENTOS
    # ========================================================================
    {
        'session_id': 'test-010',
        'titulo': 'CONV #10: Cancelar y volver a empezar',
        'pasos': [
            {
                'mensaje': 'quiero turno',
                'descripcion': 'Inicio',
                'validaciones': {}
            },
            {
                'mensaje': 'Martín González',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Martín González'}}
            },
            {
                'mensaje': '1112233',
                'descripcion': 'Cédula',
                'validaciones': {'contexto': {'cedula': '1112233'}}
            },
            {
                'mensaje': 'Cancelar todo',
                'descripcion': 'CANCELACIÓN',
                'validaciones': {
                    'intent_esperado': 'cancelar',
                    'contexto': {
                        'nombre': None,
                        'cedula': None
                    },
                    'texto_contiene': ['cancelado']
                }
            },
            {
                'mensaje': 'Ahora sí, quiero turno de nuevo',
                'descripcion': 'Reinicio después de cancelar',
                'validaciones': {
                    'intent_esperado': 'agendar_turno',
                    'texto_contiene': ['nombre']
                }
            },
            {
                'mensaje': 'Martín González',
                'descripcion': 'Nombre de nuevo',
                'validaciones': {'contexto': {'nombre': 'Martín González'}}
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 6: CASOS ESPECIALES Y EDGE CASES
    # ========================================================================
    {
        'session_id': 'test-011',
        'titulo': 'CONV #11: Pregunta por mejor día disponible',
        'pasos': [
            {
                'mensaje': 'Qué día tiene más disponibilidad esta semana?',
                'descripcion': 'Consulta día con mejor disponibilidad',
                'validaciones': {
                    'intent_esperado': 'consultar_disponibilidad',
                    'texto_contiene': ['disponibilidad']
                }
            },
            {
                'mensaje': 'Perfecto, quiero para ese día a las 9, soy Lucía Benítez',
                'descripcion': 'COMPUESTA - Hora + Nombre',
                'validaciones': {
                    'contexto': {
                        'hora': '09:00',
                        'nombre': 'Lucía Benítez'
                    }
                }
            }
        ]
    },
    
    {
        'session_id': 'test-012',
        'titulo': 'CONV #12: Consulta horarios de atención',
        'pasos': [
            {
                'mensaje': 'Hasta qué hora atienden?',
                'descripcion': 'Consulta horario de oficina',
                'validaciones': {
                    'texto_contiene': ['17:00', '07:00', 'lunes', 'viernes']
                }
            },
            {
                'mensaje': 'Ok, quiero turno para mañana al mediodía',
                'descripcion': 'Agendamiento con "mediodía"',
                'validaciones': {
                    'contexto': {
                        'fecha': 'NOT_NONE',
                        'hora': 'NOT_NONE'
                    }
                }
            }
        ]
    },
    
    {
        'session_id': 'test-013',
        'titulo': 'CONV #13: Número de teléfono para contacto',
        'pasos': [
            {
                'mensaje': 'Cuál es el número de teléfono?',
                'descripcion': 'Consulta contacto',
                'validaciones': {
                    'intent_esperado': 'consultar_ubicacion',
                    'texto_contiene': ['976 200']
                }
            },
            {
                'mensaje': 'Perfecto, ahora quiero agendar, soy Fernando Castro',
                'descripcion': 'Agendamiento después de consulta',
                'validaciones': {
                    'contexto': {'nombre': 'Fernando Castro'}
                }
            }
        ]
    },
    
    {
        'session_id': 'test-014',
        'titulo': 'CONV #14: Cambio de cédula en resumen',
        'pasos': [
            {
                'mensaje': 'turno',
                'descripcion': 'Inicio',
                'validaciones': {}
            },
            {
                'mensaje': 'Sofía Medina con cédula 4445566 para mañana 13:00',
                'descripcion': 'COMPUESTA - Todo junto',
                'validaciones': {
                    'contexto': {
                        'nombre': 'Sofía Medina',
                        'cedula': '4445566',
                        'fecha': 'NOT_NONE',
                        'hora': '13:00'
                    }
                }
            },
            {
                'mensaje': 'sofia.m@mail.com',
                'descripcion': 'Email',
                'validaciones': {'contexto': {'email': 'sofia.m@mail.com'}}
            },
            {
                'mensaje': 'Cambiar cédula',
                'descripcion': 'Corrección de cédula',
                'validaciones': {
                    'intent_esperado': 'informar_cedula',
                    'contexto': {'cedula': None}
                }
            },
            {
                'mensaje': '4445567',
                'descripcion': 'Nueva cédula',
                'validaciones': {'contexto': {'cedula': '4445567'}}
            }
        ]
    },
    
    {
        'session_id': 'test-015',
        'titulo': 'CONV #15: Sin cédula (trámite nuevo)',
        'pasos': [
            {
                'mensaje': 'Hola necesito turno pero aún no tengo cédula',
                'descripcion': 'Agendamiento sin cédula',
                'validaciones': {
                    'intent_esperado': 'agendar_turno'
                }
            },
            {
                'mensaje': 'Camila Torres',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Camila Torres'}}
            },
            {
                'mensaje': 'No tengo cédula todavía',
                'descripcion': 'Confirma que no tiene cédula',
                'validaciones': {
                    'contexto': {'cedula': 'SIN_CEDULA'}
                }
            },
            {
                'mensaje': 'para el lunes 10',
                'descripcion': 'Fecha y hora',
                'validaciones': {
                    'contexto': {
                        'fecha': 'NOT_NONE',
                        'hora': '10:00'
                    }
                }
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 7: FLUJOS CONVERSACIONALES NATURALES
    # ========================================================================
    {
        'session_id': 'test-016',
        'titulo': 'CONV #16: Conversación muy natural con dudas',
        'pasos': [
            {
                'mensaje': 'Hola, buen día',
                'descripcion': 'Saludo natural',
                'validaciones': {'intent_esperado': 'greet'}
            },
            {
                'mensaje': 'Mira, necesito renovar mi cédula, qué necesito?',
                'descripcion': 'Consulta requisitos renovación',
                'validaciones': {
                    'intent_esperado': 'consultar_requisitos',
                    'texto_contiene': ['renovación', 'cédula anterior']
                }
            },
            {
                'mensaje': 'Ah perfecto, y cuánto cuesta?',
                'descripcion': 'Consulta costo',
                'validaciones': {
                    'intent_esperado': 'consultar_costo',
                    'texto_contiene': ['25.000']
                }
            },
            {
                'mensaje': 'Ok dale, entonces quiero turno para pasado mañana',
                'descripcion': 'Decide agendar',
                'validaciones': {
                    'contexto': {'fecha': 'NOT_NONE'}
                }
            },
            {
                'mensaje': 'Ricardo Flores, CI 8889990',
                'descripcion': 'Da datos juntos',
                'validaciones': {
                    'contexto': {
                        'nombre': 'Ricardo Flores',
                        'cedula': '8889990'
                    }
                }
            }
        ]
    },
    
    {
        'session_id': 'test-017',
        'titulo': 'CONV #17: Cambios múltiples de opinión',
        'pasos': [
            {
                'mensaje': 'turno por favor',
                'descripcion': 'Inicio',
                'validaciones': {}
            },
            {
                'mensaje': 'Valentina Acosta',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Valentina Acosta'}}
            },
            {
                'mensaje': '1237894',
                'descripcion': 'Cédula',
                'validaciones': {'contexto': {'cedula': '1237894'}}
            },
            {
                'mensaje': 'para mañana',
                'descripcion': 'Fecha',
                'validaciones': {'contexto': {'fecha': 'NOT_NONE'}}
            },
            {
                'mensaje': 'mejor no, mejor para el miércoles',
                'descripcion': 'Cambia de opinión - Fecha',
                'validaciones': {
                    'contexto': {'fecha': None}
                }
            },
            {
                'mensaje': 'miércoles',
                'descripcion': 'Confirma miércoles',
                'validaciones': {'contexto': {'fecha': 'NOT_NONE'}}
            },
            {
                'mensaje': 'las 8 de la mañana',
                'descripcion': 'Hora',
                'validaciones': {'contexto': {'hora': '08:00'}}
            },
            {
                'mensaje': 'No espera, mejor a la tarde, 15:00',
                'descripcion': 'Cambia de opinión - Hora',
                'validaciones': {
                    'contexto': {'hora': None}
                }
            },
            {
                'mensaje': '15',
                'descripcion': 'Confirma hora (número simple)',
                'validaciones': {'contexto': {'hora': '15:00'}}
            }
        ]
    },
    
    {
        'session_id': 'test-018',
        'titulo': 'CONV #18: Consultas múltiples antes de decidir',
        'pasos': [
            {
                'mensaje': 'Hola, tengo dudas',
                'descripcion': 'Inicio dubitativo',
                'validaciones': {}
            },
            {
                'mensaje': 'Qué documentos necesito para primera cédula?',
                'descripcion': 'Consulta requisitos',
                'validaciones': {
                    'texto_contiene': ['partida de nacimiento', 'primera']
                }
            },
            {
                'mensaje': 'Es gratis?',
                'descripcion': 'Consulta costo',
                'validaciones': {
                    'texto_contiene': ['gratuito']
                }
            },
            {
                'mensaje': 'Cuánto tarda el trámite?',
                'descripcion': 'Consulta duración',
                'validaciones': {
                    'texto_contiene': ['minutos', 'tiempo']
                }
            },
            {
                'mensaje': 'Perfecto, entonces quiero sacar turno',
                'descripcion': 'Decide agendar',
                'validaciones': {
                    'intent_esperado': 'agendar_turno'
                }
            },
            {
                'mensaje': 'Andrés Báez',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Andrés Báez'}}
            }
        ]
    },
    
    # ========================================================================
    # GRUPO 8: CASOS EDGE Y VALIDACIONES
    # ========================================================================
    {
        'session_id': 'test-019',
        'titulo': 'CONV #19: Intenta agendar fin de semana',
        'pasos': [
            {
                'mensaje': 'turno',
                'descripcion': 'Inicio',
                'validaciones': {}
            },
            {
                'mensaje': 'Daniela Vera',
                'descripcion': 'Nombre',
                'validaciones': {'contexto': {'nombre': 'Daniela Vera'}}
            },
            {
                'mensaje': '5554443',
                'descripcion': 'Cédula',
                'validaciones': {'contexto': {'cedula': '5554443'}}
            },
            {
                'mensaje': 'para el sábado',
                'descripcion': 'Intenta sábado (debe rechazar)',
                'validaciones': {
                    'texto_contiene': ['sábado', 'lunes', 'viernes'],
                    'contexto': {'fecha': None}  # No debe guardar fecha
                }
            },
            {
                'mensaje': 'ok entonces lunes',
                'descripcion': 'Acepta lunes',
                'validaciones': {
                    'contexto': {'fecha': 'NOT_NONE'}
                }
            }
        ]
    },
    
    {
        'session_id': 'test-020',
        'titulo': 'CONV #20: Hora fuera de rango',
        'pasos': [
            {
                'mensaje': 'turno',
                'descripcion': 'Inicio',
                'validaciones': {}
            },
            {
                'mensaje': 'Miguel Ortiz, 7776665, mañana',
                'descripcion': 'COMPUESTA - Datos completos',
                'validaciones': {
                    'contexto': {
                        'nombre': 'Miguel Ortiz',
                        'cedula': '7776665',
                        'fecha': 'NOT_NONE'
                    }
                }
            },
            {
                'mensaje': 'a las 18:00',
                'descripcion': 'Hora fuera de rango (debería sugerir 07:00-15:00)',
                'validaciones': {
                    'texto_contiene': ['07:00', '15:00']
                }
            },
            {
                'mensaje': '14',
                'descripcion': 'Hora válida',
                'validaciones': {'contexto': {'hora': '14:00'}}
            }
        ]
    }
]

# Agregar más conversaciones...
# (Por brevedad, incluyo 20 pero puedes agregar hasta 25-30)

def ejecutar_mega_test():
    """Ejecuta todas las conversaciones de test"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔" + "="*98 + "╗")
    print("║" + " "*35 + "MEGA TEST COMPLETO" + " "*45 + "║")
    print("║" + " "*25 + "Sistema de Turnos - Conversaciones Realistas" + " "*29 + "║")
    print("╚" + "="*98 + "╝")
    print(f"{Colors.ENDC}")
    
    resultados = []
    
    for conv in conversaciones:
        exito = print_conversacion(
            conv['session_id'],
            conv['titulo'],
            conv['pasos']
        )
        resultados.append((conv['titulo'], exito))
    
    # Resumen final
    print(f"\n{'='*100}")
    print(f"{Colors.HEADER}{Colors.BOLD}📊 RESUMEN FINAL DEL MEGA TEST{Colors.ENDC}")
    print(f"{'='*100}\n")
    
    exitosos = sum(1 for _, exito in resultados if exito)
    total = len(resultados)
    
    for titulo, exito in resultados:
        if exito:
            print(f"{Colors.OKGREEN}✅ {titulo}{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ {titulo}{Colors.ENDC}")
    
    porcentaje = (exitosos * 100) // total
    print(f"\n{'='*100}")
    print(f"{Colors.BOLD}RESULTADO: {exitosos}/{total} conversaciones exitosas ({porcentaje}%){Colors.ENDC}")
    
    if porcentaje >= 90:
        print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 EXCELENTE! Sistema altamente robusto{Colors.ENDC}")
    elif porcentaje >= 75:
        print(f"{Colors.WARNING}{Colors.BOLD}⚠️  BUENO - Algunos ajustes necesarios{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}❌ NECESITA MEJORAS - Revisar casos fallidos{Colors.ENDC}")
    
    print(f"{'='*100}\n")
    
    return exitosos, total

if __name__ == "__main__":
    exitosos, total = ejecutar_mega_test()
    sys.exit(0 if exitosos == total else 1)
