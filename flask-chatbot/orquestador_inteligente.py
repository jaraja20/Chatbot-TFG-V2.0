"""
ORQUESTADOR INTELIGENTE MEJORADO V2.0
Integra: LLM + Rasa + Motor Difuso + Base de Datos
Versión optimizada para interpretar cualquier mensaje
"""

import requests
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, date, timedelta
import psycopg2
import re
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN
# =====================================================

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"

# Múltiples URLs del LLM (probar en orden)
LM_STUDIO_URLS = [
    "http://localhost:1234/v1/chat/completions",  # Local primero
    "http://192.168.3.118:1234/v1/chat/completions",  # Red local 1
    "http://192.168.0.218:1234/v1/chat/completions",  # Red local 2
]

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# Importar módulos con manejo de errores
try:
    from motor_difuso import (
        calcular_espera,
        analizar_disponibilidad_dia,
        obtener_mejor_recomendacion,
        generar_respuesta_recomendacion
    )
    MOTOR_DIFUSO_OK = True
    logger.info("✅ Motor difuso importado")
except ImportError as e:
    MOTOR_DIFUSO_OK = False
    logger.warning(f"⚠️ Motor difuso no disponible: {e}")

# =====================================================
# CONTEXTO DE SESIONES
# =====================================================

SESSION_CONTEXTS = {}

class SessionContext:
    """Contexto completo de una sesión de usuario"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.nombre = None
        self.cedula = None
        self.fecha = None
        self.hora = None
        self.email = None
        self.intent_actual = None
        self.ultimo_mensaje = None
        self.conversacion_historial = []
        self.datos_difusos = {}
        self.ultimo_intent_confianza = 0.0
        
    def actualizar(self, **kwargs):
        """Actualiza el contexto con nuevos datos"""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
                logger.info(f"📝 Contexto actualizado: {key} = {value}")
    
    def tiene_datos_completos(self) -> bool:
        """Verifica si tiene todos los datos para agendar"""
        return all([self.nombre, self.cedula, self.fecha, self.hora])
    
    def to_dict(self) -> Dict:
        """Convierte el contexto a diccionario"""
        return {
            'nombre': self.nombre,
            'cedula': self.cedula,
            'fecha': self.fecha,
            'hora': self.hora,
            'email': self.email,
            'intent_actual': self.intent_actual
        }

def get_or_create_context(session_id: str) -> SessionContext:
    """Obtiene o crea contexto de sesión"""
    if session_id not in SESSION_CONTEXTS:
        SESSION_CONTEXTS[session_id] = SessionContext(session_id)
        logger.info(f"🆕 Nuevo contexto creado para: {session_id}")
    return SESSION_CONTEXTS[session_id]

# =====================================================
# CLASIFICADOR DE INTENTS MEJORADO
# =====================================================

class ClasificadorIntentsMejorado:
    """
    Clasifica intents usando múltiples estrategias:
    1. Patrones de palabras clave (rápido y confiable)
    2. LLM cuando está disponible (más inteligente)
    3. Rasa como backup
    """
    
    PATRONES_INTENT = {
        # Agendamiento (ALTA PRIORIDAD)
        'agendar_turno': [
            r'\b(quiero|necesito|deseo|me gustaria)\s+(un\s+)?(turno|cita|hora)\b',
            r'\b(sacar|agendar|reservar|pedir|solicitar)\s+(un\s+)?(turno|cita)\b',
            r'\b(turno|cita)\s+(por favor|porfavor|pls)\b',
            r'\bquiero\s+turno\b',
            r'\bsacar\s+turno\b',
        ],
        
        # Consultas de horarios
        'consultar_disponibilidad': [
            r'\b(que|cuales|qu[eé])\s+(horarios|horas|turnos)\s+(hay|tienen|est[aá]n|disponible)',
            r'\b(horarios|horas)\s+(disponible|libre)',
            r'\bcuando\s+(puedo|hay|tienen|est[aá])\b',
            r'\bque\s+d[ií]as\b',
        ],
        
        'frase_ambigua': [
            r'\b(primera\s+hora|temprano|ma[ñn]ana\s+temprano)\b',
            r'\b(lo\s+antes|cuanto\s+antes|lo\s+m[aá]s\s+pronto)\b',
            r'\b(mejor\s+horario|recomiend|conveniente)\b',
        ],
        
        # Datos personales
        'informar_nombre': [
            r'\b(mi\s+nombre\s+es|me\s+llamo|soy)\s+[A-Z]',
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # Nombre completo
        ],
        
        'informar_cedula': [
            r'\b\d{6,8}\b',  # Número de cédula
            r'\bci\s*:?\s*\d+',
            r'\bcedula\s*:?\s*\d+',
        ],
        
        'informar_fecha': [
            r'\b(ma[ñn]ana|pasado\s+ma[ñn]ana|hoy)\b',
            r'\b(lunes|martes|mi[eé]rcoles|jueves|viernes)\b',
            r'\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b',  # Formato fecha
            r'\bpara\s+el\s+\d+',
        ],
        
        'elegir_horario': [
            r'\b\d{1,2}:\d{2}\b',  # Formato HH:MM
            r'\ba\s+las\s+\d+',
            r'\b\d{1,2}\s*(am|pm|hs|horas)\b',
        ],
        
        # Información
        'consultar_requisitos': [
            r'\b(que|cuales)\s+(requisitos|documentos|necesito|debo)\b',
            r'\brequisitos\b',
            r'\bdocumentos?\b',
        ],
        
        'consultar_ubicacion': [
            r'\b(donde|ubicaci[oó]n|direcci[oó]n|como\s+llego)\b',
            r'\bqueda\b.*\b(oficina|lugar)\b',
        ],
        
        'consultar_costo': [
            r'\b(cuanto|cu[aá]nto)\s+(cuesta|sale|vale)\b',
            r'\b(precio|costo|arancel)\b',
        ],
        
        # Consulta de tiempo de espera
        'consulta_tiempo_espera': [
            r'\b(cuanto|cu[aá]nto)\s+(tiempo|demor[ao]|espera|tarda)\b',
            r'\btiempo\s+de\s+espera\b',
            r'\bcu[aá]nto\s+hay\s+que\s+esperar\b',
        ],
        
        # Saludos y despedidas
        'greet': [
            r'\b(hola|buenas|buen\s+d[ií]a|buenos\s+d[ií]as)\b',
            r'^(hola|hey|hi)$',
        ],
        
        'goodbye': [
            r'\b(chau|adi[oó]s|hasta\s+luego|nos\s+vemos)\b',
            r'^(bye|chao)$',
        ],
        
        # Afirmaciones y negaciones
        'affirm': [
            r'\b(s[ií]|si|ok|okay|dale|perfecto|correcto|exacto|confirmo)\b',
            r'^(si|s[ií])$',
        ],
        
        'deny': [
            r'\b(no|nop|nope|neg|cancelar)\b',
            r'^no$',
        ],
        
        'agradecimiento': [
            r'\b(gracias|muchas\s+gracias|agradezco|grax)\b',
        ],
    }
    
    def __init__(self):
        self.llm_url = self._encontrar_llm_disponible()
        logger.info(f"🔧 Clasificador inicializado (LLM: {self.llm_url or 'No disponible'})")
    
    def _encontrar_llm_disponible(self) -> Optional[str]:
        """Encuentra una URL del LLM que funcione"""
        for url in LM_STUDIO_URLS:
            try:
                response = requests.get(url.replace('/v1/chat/completions', '/v1/models'), timeout=2)
                if response.status_code == 200:
                    logger.info(f"✅ LLM encontrado en: {url}")
                    return url
            except:
                continue
        logger.warning("⚠️ No se encontró LLM Studio disponible")
        return None
    
    def clasificar(self, mensaje: str, contexto: SessionContext) -> Tuple[str, float]:
        """
        Clasifica el intent del mensaje usando múltiples métodos
        
        Returns:
            (intent, confidence)
        """
        mensaje_lower = mensaje.lower().strip()
        
        # 1. MÉTODO RÁPIDO: Patrones de palabras clave
        intent_patron, confianza_patron = self._clasificar_por_patrones(mensaje_lower)
        
        if confianza_patron > 0.8:
            logger.info(f"🎯 Intent detectado por patrón: {intent_patron} ({confianza_patron:.2f})")
            return intent_patron, confianza_patron
        
        # 2. MÉTODO INTELIGENTE: Usar LLM si está disponible
        if self.llm_url:
            try:
                intent_llm, confianza_llm = self._clasificar_con_llm(mensaje, contexto)
                if confianza_llm > 0.7:
                    logger.info(f"🤖 Intent detectado por LLM: {intent_llm} ({confianza_llm:.2f})")
                    return intent_llm, confianza_llm
            except Exception as e:
                logger.warning(f"⚠️ Error en LLM: {e}")
        
        # 3. FALLBACK: Usar el patrón si encontró algo
        if intent_patron and confianza_patron > 0.5:
            logger.info(f"📋 Usando intent de patrón: {intent_patron}")
            return intent_patron, confianza_patron
        
        # 4. ÚLTIMO RECURSO: Intent genérico
        logger.warning(f"❓ No se pudo clasificar: '{mensaje}'")
        return 'nlu_fallback', 0.3
    
    def _clasificar_por_patrones(self, mensaje: str) -> Tuple[str, float]:
        """Clasifica usando patrones de regex"""
        mejor_intent = None
        mejor_score = 0.0
        
        for intent, patrones in self.PATRONES_INTENT.items():
            for patron in patrones:
                if re.search(patron, mensaje, re.IGNORECASE):
                    # Calcular score basado en longitud del match
                    match = re.search(patron, mensaje, re.IGNORECASE)
                    score = len(match.group()) / len(mensaje)
                    score = min(0.95, score + 0.3)  # Boost y cap
                    
                    if score > mejor_score:
                        mejor_score = score
                        mejor_intent = intent
        
        return mejor_intent or 'nlu_fallback', mejor_score
    
    def _clasificar_con_llm(self, mensaje: str, contexto: SessionContext) -> Tuple[str, float]:
        """Clasifica usando LLM (si está disponible)"""
        if not self.llm_url:
            return 'nlu_fallback', 0.0
        
        intents_str = '\n'.join([
            'agendar_turno', 'consultar_disponibilidad', 'frase_ambigua',
            'informar_nombre', 'informar_cedula', 'informar_fecha', 'elegir_horario',
            'consultar_requisitos', 'consultar_ubicacion', 'consultar_costo',
            'consulta_tiempo_espera', 'greet', 'goodbye', 'affirm', 'deny'
        ])
        
        prompt = f"""Eres un clasificador de intents para un chatbot de turnos de cédulas.

Mensaje del usuario: "{mensaje}"

Contexto actual:
- Nombre: {contexto.nombre or 'No proporcionado'}
- Cédula: {contexto.cedula or 'No proporcionada'}
- Fecha: {contexto.fecha or 'No seleccionada'}
- Intent previo: {contexto.intent_actual or 'Ninguno'}

Intents disponibles:
{intents_str}

Responde SOLO con el nombre del intent más apropiado. Sin explicaciones."""

        try:
            response = requests.post(
                self.llm_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                timeout=5
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                intent = content.lower().replace('.', '').strip()
                
                # Validar que el intent sea válido
                if intent in self.PATRONES_INTENT:
                    return intent, 0.85
        
        except Exception as e:
            logger.warning(f"Error en LLM: {e}")
        
        return 'nlu_fallback', 0.0

# =====================================================
# EXTRACTOR DE ENTIDADES
# =====================================================

def extraer_entidades(mensaje: str, intent: str) -> Dict:
    """Extrae entidades del mensaje según el intent"""
    entidades = {}
    mensaje_lower = mensaje.lower()
    
    # Extraer NOMBRE
    if intent == 'informar_nombre' or 'me llamo' in mensaje_lower or 'mi nombre es' in mensaje_lower:
        match = re.search(r'(me\s+llamo|mi\s+nombre\s+es|soy)\s+([A-Z][a-zñáéíóú]+(?:\s+[A-Z][a-zñáéíóú]+)*)', mensaje, re.IGNORECASE)
        if match:
            entidades['nombre'] = match.group(2).title()
        else:
            # Buscar nombre al inicio del mensaje
            match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', mensaje)
            if match:
                entidades['nombre'] = match.group(1)
    
    # Extraer CÉDULA
    cedula_match = re.search(r'\b(\d{6,8})\b', mensaje)
    if cedula_match:
        entidades['cedula'] = cedula_match.group(1)
    
    # Extraer FECHA
    if 'mañana' in mensaje_lower or 'manana' in mensaje_lower:
        fecha = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        entidades['fecha'] = fecha
    elif 'pasado mañana' in mensaje_lower or 'pasado manana' in mensaje_lower:
        fecha = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        entidades['fecha'] = fecha
    elif 'hoy' in mensaje_lower:
        entidades['fecha'] = datetime.now().strftime('%Y-%m-%d')
    else:
        # Buscar formato DD/MM o DD-MM
        fecha_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})([/-](\d{2,4}))?\b', mensaje)
        if fecha_match:
            dia = int(fecha_match.group(1))
            mes = int(fecha_match.group(2))
            anio = int(fecha_match.group(4)) if fecha_match.group(4) else datetime.now().year
            if anio < 100:
                anio += 2000
            try:
                entidades['fecha'] = f"{anio}-{mes:02d}-{dia:02d}"
            except:
                pass
    
    # Extraer HORA
    hora_match = re.search(r'\b(\d{1,2}):(\d{2})\b', mensaje)
    if hora_match:
        entidades['hora'] = f"{int(hora_match.group(1)):02d}:{hora_match.group(2)}"
    else:
        # Buscar formato "a las X" o "X hs"
        hora_match = re.search(r'\b(\d{1,2})\s*(am|pm|hs|horas?)\b', mensaje_lower)
        if hora_match:
            hora = int(hora_match.group(1))
            sufijo = hora_match.group(2)
            if sufijo == 'pm' and hora < 12:
                hora += 12
            entidades['hora'] = f"{hora:02d}:00"
    
    # Extraer EMAIL
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', mensaje)
    if email_match:
        entidades['email'] = email_match.group(0)
    
    if entidades:
        logger.info(f"📦 Entidades extraídas: {entidades}")
    
    return entidades

# =====================================================
# CONSULTAS A BASE DE DATOS
# =====================================================

def obtener_disponibilidad_real(fecha: str = None) -> Dict:
    """Obtiene disponibilidad real de la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        if not fecha:
            fecha = datetime.now().strftime('%Y-%m-%d')
        
        # Contar turnos por hora
        cursor.execute("""
            SELECT 
                DATE_TRUNC('hour', fecha_hora) as hora,
                COUNT(*) as ocupados
            FROM turnos
            WHERE DATE(fecha_hora) = %s
            AND estado = 'activo'
            GROUP BY DATE_TRUNC('hour', fecha_hora)
            ORDER BY hora
        """, (fecha,))
        
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convertir a dict
        ocupacion_por_hora = {}
        for hora, ocupados in resultados:
            hora_str = hora.strftime('%H:00')
            ocupacion_por_hora[hora_str] = ocupados
        
        logger.info(f"📊 Disponibilidad obtenida para {fecha}: {len(ocupacion_por_hora)} horas")
        return ocupacion_por_hora
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo disponibilidad: {e}")
        return {}

# =====================================================
# FUNCIÓN PRINCIPAL: PROCESAR MENSAJE
# =====================================================

clasificador = ClasificadorIntentsMejorado()

def procesar_mensaje_inteligente(user_message: str, session_id: str) -> Dict:
    """
    Función principal que procesa cualquier mensaje del usuario
    
    Args:
        user_message: Mensaje del usuario
        session_id: ID de sesión
        
    Returns:
        Dict con respuesta y metadata
    """
    
    try:
        # 1. Obtener contexto
        contexto = get_or_create_context(session_id)
        contexto.ultimo_mensaje = user_message
        
        # 2. Clasificar intent
        intent, confidence = clasificador.clasificar(user_message, contexto)
        contexto.intent_actual = intent
        contexto.ultimo_intent_confianza = confidence
        
        logger.info(f"🎯 Intent: {intent} | Confianza: {confidence:.2f}")
        
        # 3. Extraer entidades
        entidades = extraer_entidades(user_message, intent)
        contexto.actualizar(**entidades)
        
        # 4. Generar respuesta según intent
        respuesta = generar_respuesta_inteligente(intent, confidence, contexto, user_message)
        
        return {
            'respuesta': respuesta,
            'metadata': {
                'intent': intent,
                'confidence': confidence,
                'entidades': entidades,
                'contexto': contexto.to_dict()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error en procesar_mensaje_inteligente: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'respuesta': (
                "Disculpa, tuve un problema procesando tu mensaje. "
                "¿Podrías reformularlo? Por ejemplo: 'Quiero un turno para mañana'"
            ),
            'metadata': {
                'intent': 'error',
                'confidence': 0.0,
                'error': str(e)
            }
        }

def generar_respuesta_inteligente(intent: str, confidence: float, 
                                  contexto: SessionContext, mensaje: str) -> str:
    """Genera respuesta apropiada según el intent"""
    
    # Intent: AGENDAR TURNO
    if intent == 'agendar_turno':
        if not contexto.nombre:
            return "¡Perfecto! Para agendar tu turno, necesito algunos datos. ¿Cuál es tu nombre completo?"
        elif not contexto.cedula:
            return f"Gracias {contexto.nombre}. ¿Cuál es tu número de cédula?"
        elif not contexto.fecha:
            return "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
        elif not contexto.hora:
            # Mostrar horarios disponibles
            disponibilidad = obtener_disponibilidad_real(contexto.fecha)
            if MOTOR_DIFUSO_OK:
                try:
                    mejor_hora = obtener_mejor_recomendacion(disponibilidad)
                    return f"Para el {contexto.fecha}, te recomiendo {mejor_hora}. ¿Te parece bien esta hora?"
                except:
                    pass
            return "¿A qué hora prefieres? Por ejemplo: 09:00, 14:30, etc."
        else:
            # Todos los datos completos - confirmar
            return (
                f"📋 Resumen de tu turno:\n"
                f"Nombre: {contexto.nombre}\n"
                f"Cédula: {contexto.cedula}\n"
                f"Fecha: {contexto.fecha}\n"
                f"Hora: {contexto.hora}\n\n"
                f"¿Confirmas estos datos? (Responde 'sí' para confirmar)"
            )
    
    # Intent: CONSULTAR DISPONIBILIDAD
    elif intent == 'consultar_disponibilidad':
        fecha = contexto.fecha or datetime.now().strftime('%Y-%m-%d')
        disponibilidad = obtener_disponibilidad_real(fecha)
        
        if MOTOR_DIFUSO_OK and disponibilidad:
            try:
                analisis = analizar_disponibilidad_dia(disponibilidad)
                return generar_respuesta_recomendacion(analisis, fecha)
            except:
                pass
        
        return f"Los horarios disponibles para el {fecha} son de 08:00 a 17:00. ¿A qué hora prefieres?"
    
    # Intent: FRASE AMBIGUA (temprano, lo antes posible, etc.)
    elif intent == 'frase_ambigua':
        fecha = contexto.fecha or datetime.now().strftime('%Y-%m-%d')
        disponibilidad = obtener_disponibilidad_real(fecha)
        
        if MOTOR_DIFUSO_OK:
            try:
                mejor_hora = obtener_mejor_recomendacion(disponibilidad)
                contexto.hora = mejor_hora
                return f"Te recomiendo {mejor_hora} que es el horario con menos espera. ¿Te parece bien?"
            except:
                pass
        
        return "El mejor horario suele ser a las 08:00. ¿Te sirve ese horario?"
    
    # Intent: TIEMPO DE ESPERA
    elif intent == 'consulta_tiempo_espera':
        if MOTOR_DIFUSO_OK:
            try:
                # Obtener datos reales de ocupación
                disponibilidad = obtener_disponibilidad_real()
                hora_actual = datetime.now().hour
                ocupacion = disponibilidad.get(f"{hora_actual:02d}:00", 3) * 20  # Estimar %
                
                tiempo = calcular_espera(ocupacion, urgencia=5)
                return f"El tiempo de espera estimado ahora es de aproximadamente {int(tiempo)} minutos."
            except:
                pass
        
        return "El tiempo de espera promedio es de 15-30 minutos, dependiendo de la hora."
    
    # Intent: INFORMAR DATOS
    elif intent in ['informar_nombre', 'informar_cedula', 'informar_fecha', 'elegir_horario']:
        # Ya se actualizó el contexto, preguntar siguiente dato
        if not contexto.nombre:
            return "¿Cuál es tu nombre completo?"
        elif not contexto.cedula:
            return f"Gracias {contexto.nombre}. ¿Cuál es tu número de cédula?"
        elif not contexto.fecha:
            return "¿Para qué día necesitas el turno?"
        elif not contexto.hora:
            return "¿A qué hora prefieres?"
        else:
            return (
                f"Perfecto. Turno para:\n"
                f"{contexto.nombre} - CI: {contexto.cedula}\n"
                f"{contexto.fecha} a las {contexto.hora}\n"
                f"¿Confirmas? (sí/no)"
            )
    
    # Intent: SALUDOS
    elif intent == 'greet':
        return (
            "¡Hola! Soy el asistente virtual de turnos para cédulas de identidad. "
            "¿En qué puedo ayudarte hoy? Puedes decir cosas como:\n"
            "- 'Quiero sacar un turno'\n"
            "- '¿Qué horarios tienen disponibles?'\n"
            "- '¿Cuánto demora el trámite?'"
        )
    
    # Intent: DESPEDIDA
    elif intent == 'goodbye':
        return "¡Hasta luego! Si necesitas algo más, aquí estaré. 👋"
    
    # Intent: AFIRMAR
    elif intent == 'affirm':
        if contexto.tiene_datos_completos():
            # TODO: Aquí iría la lógica para guardar en BD y enviar QR
            return (
                f"✅ ¡Turno confirmado!\n"
                f"Te llegará un email con el código QR a tu correo.\n"
                f"Recuerda llegar 10 minutos antes. ¡Hasta pronto!"
            )
        return "Perfecto, continuemos. ¿Qué necesitas?"
    
    # Intent: NEGAR
    elif intent == 'deny':
        return "Entendido. ¿Hay algo más en lo que pueda ayudarte?"
    
    # Intent: AGRADECIMIENTO
    elif intent == 'agradecimiento':
        return "¡De nada! Estoy aquí para ayudarte. 😊"
    
    # Intent: FALLBACK - Consultar Rasa
    else:
        try:
            response = requests.post(
                RASA_URL,
                json={"sender": contexto.session_id, "message": mensaje},
                timeout=5
            )
            
            if response.status_code == 200:
                rasa_responses = response.json()
                if rasa_responses:
                    return rasa_responses[0].get('text', 'Lo siento, no entendí.')
        except:
            pass
        
        return (
            "No estoy seguro de entender. ¿Podrías reformular? "
            "Puedo ayudarte con:\n"
            "- Agendar turnos\n"
            "- Consultar horarios\n"
            "- Información sobre requisitos"
        )

# =====================================================
# EXPORTAR FUNCIÓN PRINCIPAL
# =====================================================

__all__ = ['procesar_mensaje_inteligente']