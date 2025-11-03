
"""
COPILOT HANDLER
Gestiona la integración de GitHub Copilot como modelo principal de respuesta
"""

import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, date, timedelta
import psycopg2
import re
from motor_difuso import (
    calcular_espera,
    analizar_disponibilidad_dia,
    obtener_mejor_recomendacion,
    generar_respuesta_recomendacion
)

# Formato de fechas en español
_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

def format_fecha_es(fecha: date, con_anio: bool = False) -> str:
    """Formatea una fecha en español"""
    try:
        dia_nombre = _DIAS_ES[fecha.weekday()]
        mes_nombre = _MESES_ES[fecha.month - 1]
        if con_anio:
            return f"{dia_nombre} {fecha.day} de {mes_nombre} de {fecha.year}"
        return f"{dia_nombre} {fecha.day} de {mes_nombre}"
    except Exception as e:
        logger.error(f"Error formateando fecha {fecha}: {e}")
        return fecha.strftime("%d/%m/%Y")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración BD
DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        return None

def consultar_disponibilidad_real(fecha: date) -> Dict:
    """Consulta la disponibilidad real en la base de datos"""
    conn = get_db_connection()
    if not conn:
        return {"error": "No se pudo conectar a la base de datos"}
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT EXTRACT(HOUR FROM fecha_hora) as hora,
                   COUNT(*) as turnos
            FROM turnos 
            WHERE DATE(fecha_hora) = %s
            AND estado = 'activo'
            GROUP BY EXTRACT(HOUR FROM fecha_hora)
            ORDER BY hora
        """
        cursor.execute(query, (fecha,))
        resultados = cursor.fetchall()
        
        disponibilidad = {
            'fecha': fecha.strftime('%Y-%m-%d'),
            'horarios': {}
        }
        
        for hora, turnos in resultados:
            hora_int = int(hora)
            # Asumiendo un máximo de 20 turnos por hora
            disponibles = 20 - turnos
            disponibilidad['horarios'][hora_int] = {
                'disponibles': disponibles,
                'ocupados': turnos
            }
        
        return disponibilidad
        
    except Exception as e:
        logger.error(f"Error consultando disponibilidad: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

def consultar_turnos_detalle_por_fecha(fecha: date) -> list:
    """Devuelve los detalles de los turnos activos para una fecha dada"""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        query = """
            SELECT fecha_hora, nombre, cedula, codigo
            FROM turnos
            WHERE DATE(fecha_hora) = %s AND estado = 'activo'
            ORDER BY fecha_hora
        """
        cursor.execute(query, (fecha,))
        resultados = cursor.fetchall()
        turnos = []
        for fecha_hora, nombre, cedula, codigo in resultados:
            turnos.append({
                'fecha_hora': fecha_hora.strftime('%Y-%m-%d %H:%M'),
                'nombre': nombre,
                'cedula': cedula,
                'codigo': codigo
            })
        return turnos
    except Exception as e:
        logger.error(f"Error consultando detalles de turnos: {e}")
        return []
    finally:
        conn.close()

def detectar_intent(mensaje: str) -> Tuple[str, float]:
    """Detecta el intent del mensaje basado en patrones"""
    mensaje_lower = mensaje.lower()
    
    patrones = {
        'greet': [r'\b(hola|buenas|buen[ao]s?\s*(días|tardes|noches)|qué\s*tal|saludos)\b'],
        'goodbye': [r'\b(chau|adiós|hasta\s*luego|nos\s*vemos|bye)\b'],
        'agendar_turno': [r'\b(quiero|necesito|deseo)\s*(sacar|agendar|solicitar)\s*(un)?\s*turno\b',
                         r'\b(turno|cita|hora)\b'],
        'consultar_disponibilidad': [r'\b(disponibilidad|horarios?|días?|fechas?)\s*(libres?|disponibles?)\b',
                                   r'\bcuando\s*(hay|tienen|existe)\s*(turno|disponibilidad)\b'],
        'informar_nombre': [r'me\s*llamo\s*\w+', r'mi\s*nombre\s*es\s*\w+'],
        'informar_cedula': [r'\b\d{1,8}\b', r'primera\s*vez'],
        'consultar_requisitos': [r'\b(requisitos?|documentos?|necesito|debo)\s*(llevar|presentar|tener)\b'],
        'frase_ambigua': [r'\b(mejor|recomendado|ideal|conveniente)\s*(horario|momento|día)\b']
    }
    
    mejor_intent = 'nlu_fallback'
    mejor_confianza = 0.0
    
    for intent, patterns in patrones.items():
        for patron in patterns:
            if re.search(patron, mensaje_lower):
                confianza = 0.8
                if confianza > mejor_confianza:
                    mejor_intent = intent
                    mejor_confianza = confianza
    
    return mejor_intent, mejor_confianza

class ConversationContext:
    def __init__(self):
        self.current_intent = None
        self.slots = {
            'nombre': None,
            'cedula': None,
            'fecha': None,
            'hora': None,
            'email': None
        }
        self.last_message = None
        self.corrections = []

CONTEXTS = {}

def get_or_create_context(session_id: str) -> ConversationContext:
    if session_id not in CONTEXTS:
        CONTEXTS[session_id] = ConversationContext()
    return CONTEXTS[session_id]

def obtener_fecha_desde_texto(texto: str) -> Optional[date]:
    """Extrae una fecha desde el texto del usuario"""
    texto_lower = texto.lower()
    hoy = date.today()
    
    try:
        # Próxima semana
        if "proxima semana" in texto_lower or "siguiente semana" in texto_lower:
            # Calcular el próximo lunes
            dias_hasta_lunes = (7 - hoy.weekday()) % 7
            if dias_hasta_lunes == 0:
                dias_hasta_lunes = 7  # Si hoy es lunes, ir al próximo lunes
            return hoy + timedelta(days=dias_hasta_lunes)
        
        # Esta semana
        if "esta semana" in texto_lower:
            # Si es fin de semana, ir al lunes siguiente
            if hoy.weekday() >= 5:
                dias_hasta_lunes = (7 - hoy.weekday()) % 7
                return hoy + timedelta(days=dias_hasta_lunes)
            return hoy + timedelta(days=1)
        
        # Mañana
        if "mañana" in texto_lower:
            manana = hoy + timedelta(days=1)
            # Si mañana es fin de semana, ir al lunes
            if manana.weekday() >= 5:
                dias_hasta_lunes = (7 - manana.weekday()) % 7
                return manana + timedelta(days=dias_hasta_lunes)
            return manana
        
        # Por defecto, próximo día hábil
        siguiente_dia = hoy + timedelta(days=1)
        while siguiente_dia.weekday() >= 5:  # Si es fin de semana
            siguiente_dia += timedelta(days=1)
        return siguiente_dia
        
    except Exception as e:
        logger.error(f"Error procesando fecha: {e}")
        # En caso de error, retornar el próximo día hábil
        siguiente_dia = hoy + timedelta(days=1)
        while siguiente_dia.weekday() >= 5:
            siguiente_dia += timedelta(days=1)
        return siguiente_dia

def aprender_de_correccion(mensaje: str, contexto: ConversationContext):
    """Aprende de las correcciones del usuario"""
    if "debes responder" in mensaje.lower() or "tienes que decir" in mensaje.lower():
        correccion = mensaje.lower().split("responder")[-1].strip()
        if correccion:
            contexto.corrections.append({
                'intent': contexto.current_intent,
                'mensaje_original': contexto.last_message,
                'correccion': correccion
            })

def procesar_mensaje_copilot(mensaje: str, session_id: str, context: Dict = None) -> Dict:
    """
    Procesa un mensaje utilizando GitHub Copilot como modelo principal
    Integra con la base de datos real y el motor difuso para respuestas precisas
    """
    try:
        # Obtener o crear contexto de la conversación
        contexto = get_or_create_context(session_id)
        contexto.last_message = mensaje
        mensaje_lower = mensaje.lower()

        # Procesar posibles correcciones
        if "debes responder" in mensaje_lower or "tienes que decir" in mensaje_lower:
            aprender_de_correccion(mensaje, contexto)
            return {
                "response": "¡Gracias por la corrección! La tendré en cuenta para futuras respuestas."
            }

        # Detectar consultas de disponibilidad
        if any(palabra in mensaje_lower for palabra in ["disponible", "libre", "turno", "marcar", "agendar", "sacar"]):
            fecha_consulta = obtener_fecha_desde_texto(mensaje)
            logger.info(f"🔎 Consultando disponibilidad para la fecha: {fecha_consulta}")
            try:
                disponibilidad = consultar_disponibilidad_real(fecha_consulta)
                logger.info(f"🔎 Resultado de disponibilidad: {disponibilidad}")
                if not disponibilidad or 'error' in disponibilidad or 'horarios' not in disponibilidad:
                    logger.error(f"Error en la consulta de disponibilidad: {disponibilidad.get('error', 'Sin detalles')}")
                    return {
                        "response": "Tuve un problema al consultar la disponibilidad. ¿Podrías intentarlo de nuevo?"
                    }

                # Obtener recomendación difusa para la fecha
                resultado_recomendacion = obtener_mejor_recomendacion(fecha_consulta)
                mejor_franja = resultado_recomendacion[0]
                mejor_horario = resultado_recomendacion[1]

                horarios_disponibles = []
                for hora, info in disponibilidad['horarios'].items():
                    if info['disponibles'] > 0:
                        # calcular_espera espera (ocupacion_percent, urgencia, hora)
                        try:
                            ocupacion_percent = (info['ocupados'] / 20.0) * 100.0
                        except Exception:
                            ocupacion_percent = 50.0
                        espera_min = calcular_espera(ocupacion_percent, 5, float(hora))
                        horarios_disponibles.append({
                            'hora': hora,
                            'espera_min': espera_min,
                            'ocupados': info.get('ocupados', 0),
                            'disponibles': info.get('disponibles', 0)
                        })

                if horarios_disponibles:
                    respuesta = f"📅 Para el {format_fecha_es(fecha_consulta)} tenemos estos horarios:\n\n"
                    for h in horarios_disponibles:
                        # Clasificar por tiempo de espera estimado
                        if h['espera_min'] < 20:
                            estado = "🟢 Poco movimiento"
                        elif h['espera_min'] < 40:
                            estado = "🟡 Movimiento moderado"
                        else:
                            estado = "🔴 Mucho movimiento"
                        respuesta += f"• {h['hora']}:00 - {estado} (≈ {h['espera_min']} min)\n"
                    respuesta += f"\n💡 Recomendación: Te sugiero la franja {mejor_franja} ({mejor_horario.get('rango','--')}) que suele tener menor tiempo de espera."
                    respuesta += "\n\n¿Te gustaría agendar un turno en alguno de estos horarios?"
                else:
                    respuesta = f"Lo siento, no hay turnos disponibles para el {format_fecha_es(fecha_consulta)}. ¿Te gustaría consultar otra fecha?"
                return {
                    "response": respuesta,
                    "availability": disponibilidad,
                    "recommendation": mejor_horario
                }
            except Exception as e:
                logger.error(f"Error consultando disponibilidad: {e}")
                return {
                    "response": "Tuve un problema al consultar la disponibilidad. ¿Podrías intentarlo de nuevo?"
                }

        # Saludos y consultas generales
        if any(saludo in mensaje_lower for saludo in ['hola', 'buenas', 'buen', 'que tal']):
            return {
                "response": "¡Hola! 👋 ¿En qué puedo ayudarte hoy? Puedo informarte sobre turnos disponibles, requisitos para el trámite, o resolver cualquier otra duda que tengas."
            }

        # Consultas sobre requisitos
        if any(palabra in mensaje_lower for palabra in ['requisito', 'necesito', 'llevar', 'documento']):
            return {
                "response": "📋 Para el trámite necesitás:\n\n" +
                          "Si es renovación:\n" +
                          "• Cédula anterior (original)\n" +
                          "• Comprobante de pago\n\n" +
                          "Si es primera vez:\n" +
                          "• Certificado de nacimiento original\n" +
                          "• Comprobante de pago\n" +
                          "• Presencia de padres o tutor\n\n" +
                          "¿Te gustaría agendar un turno?"
            }

        # Respuesta por defecto más contextual
        return {
            "response": "Entiendo que necesitas ayuda. ¿Me podrías decir específicamente qué información necesitás? " +
                      "Puedo ayudarte con:\n" +
                      "• Consultar turnos disponibles\n" +
                      "• Informarte sobre los requisitos\n" +
                      "• Agendar un turno\n" +
                      "• Resolver otras dudas sobre el trámite"
        }

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return {
            "response": "Disculpa, tuve un inconveniente al procesar tu consulta. ¿Podrías reformularla de otra manera?",
            "error": str(e)
        }
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return {
            "response": "Lo siento, hubo un error al procesar tu mensaje. ¿Podrías intentarlo de nuevo?",
            "error": str(e)
        }