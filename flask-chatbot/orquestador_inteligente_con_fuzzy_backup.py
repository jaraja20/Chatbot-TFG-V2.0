"""
ORQUESTADOR INTELIGENTE MEJORADO V4.0
Sistema Unificado con Lógica Difusa Integral
Integra: Contexto + Regex + LLM + Razonamiento Difuso como un solo ente
"""

import requests
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, date, timedelta
import psycopg2
import re
import traceback
import os
import random
import string
from dotenv import load_dotenv
from copilot_handler import procesar_mensaje_copilot

# NUEVO: Imports del motor de lógica difusa
from razonamiento_difuso import (
    clasificar_con_logica_difusa, 
    obtener_membresias_difusas,
    agregar_scores_difusos
)
from clasificador_hibrido import clasificar_con_fusion_difusa

# Cargar variables de entorno desde .env
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN
# =====================================================

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"  # Fallback
USE_COPILOT = True  # Usar GitHub Copilot como modelo principal

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
        self.tipo_tramite = None  # 'primera_vez', 'perdida', 'renovacion', 'extranjero'
        self.fecha = None
        self.franja_horaria = None  # 'manana', 'tarde'
        self.hora = None
        self.hora_recomendada = None  # Guardar última hora recomendada
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
        return all([self.nombre, self.cedula, self.fecha, self.hora, self.email])
    
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
# GENERADOR DE CÓDIGO ÚNICO
# =====================================================

def generar_codigo_turno() -> str:
    """
    Genera un código único alfanumérico de 5 caracteres
    Formato: Mayúsculas y números (ej: A3X9K, B7Y2M)
    """
    caracteres = string.ascii_uppercase + string.digits
    codigo = ''.join(random.choices(caracteres, k=5))
    logger.info(f"🎫 Código generado: {codigo}")
    return codigo

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
            r'\b(quiero|kiero|kero|kieroo|necesito|nesecito|nesesito|deseo|me gustaria)\s+(un\s+)?(turno|cita|hora)\b',
            r'\b(sacar|sakar|agendar|agend|ajendar|amrcar|reservar|apartar|conseguir|pedir|solicitar)\s+(un\s+|una\s+)?(turno|cita|horario|cupo)\b',
            r'^\s*reservar\s+(un\s+|una\s+)?(turno|cita)\s*$',
            r'\b(turno|cita)\s+(por favor|x favor|xfa|porfavor|pls|plss|porfa|porfaa+)\b',
            r'\b(quiero|kiero|kero|kieroo)\s+turno\b',
            r'\b(sacar|sakar)\s+turno\b',
            r'^\s*turno\s*$',  # Solo la palabra "turno"
            r'\bquiero\s+(sacar|sakar|un)\s+turno\b',
            r'\b(necesito|nesecito|nesesito)\s+turno\b',
            r'\bturno\s+(urgente|rapido|rápido)\b',
            r'\b(podria|podría|quisiera)\s+(agendar|reservar)\b',
            r'\bquiero\s+agendar\s+para\b',
            r'\bnecesito\s+agendar\s+(pero|para)\b',
            r'\b(dame|damelo|dame\s+un)\s+(horario|turno)\b',
            r'\bquiero\s+reservar\b',
            r'\bagendar\s+(para\s+)?antes\s+de(l)?\b',
            # Frases largas descriptivas
            r'\b(necesito|estoy\s+intentando).*\bagendar\s+un\s+turno\b',
            r'\bcomunicarme.*\bagendar\s+un\s+turno\b',
            r'\b(vieja|che|amigo|bo)\s*,?\s*(necesito|quiero|kiero)\s+turno\b',
            r'\bnecesito\s+para\s+(ma[ñn]ana|hoy|el\s+(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes))\b',
            r'\b(porfa|porfaa+)\s+(urgente|rapido|rápido)\b',
            r'\b(yo|tu|el|ella)\s+(querer|necesitar|poder)\s+turno\b',
            r'\b(che|vieja|amigo|bo)\s*,?\s+(tienen|hay)\s+(lugar|turno|espacio)\b(?!.*\bhoy\b)',  # No si pregunta por HOY
            r'\bnecesito\s+agendar\s+un\s+turno\s+pero\b',
            r'\bdame\s+uno\b',
        ],
        
        # Consultas de horarios
        'consultar_disponibilidad': [
            r'\b(que|cuales|cu[aá]les|cual|cu[aá]l|qu[eé]|k|q|ke|qe)\s+(horarios|horas|hora|turnos|franjas|d[ií]as)\s+(hay|tienen|est[aá]n|son|disponible|libre|trabajan|atienden)',
            r'\b(que|qu[eé])\s+tal\s+(la\s+)?(disponibilidad|horarios|turnos|esta\s+semana|para\s+la\s+pr[oó]xima|semana)\b',
            r'\by\s+la\s+pr[oó]xima\s+semana\b',
            r'\by\s+para\s+la\s+pr[oó]xima\b',
            r'\bque\s+tal\s+para\s+la\s+pr[oó]xima\b',
            r'\b(cual|cu[aá]l)\s+(es|ser[aá])\s+(la\s+)?(disponibilidad|horarios|turnos)\b',
            r'\b(que|qu[eé]|cual|cu[aá]l)\s+(dia|d[ií]a)\s+(est[aá]|esta|hay|tienen)\s+(m[aá]s|mas)\s+(cerca|cercano|pr[oó]ximo|disponible)\b',
            r'\b(el\s+)?(dia|d[ií]a)\s+(m[aá]s|mas)\s+(cerca|cercano|pr[oó]ximo)\s+(disponible|para\s+marcar)\b',
            r'\b(ke|qe|que)\s+d[ií]as\s+trabajan\b',
            r'\b(horarios|horas|franjas\s+horarias)\s+(disponible|libre|tienen)',
            r'\bcuando\s+(puedo|hay|tienen|est[aá]|es\s+posible)\b',
            r'\bque\s+d[ií]as\s+(trabajan|atienden)?\b',
            r'\bhay\s+(turnos|horarios|lugar|hueco|espacio|turno)\b',
            r'\b(tienen|hay)\s+(algo|algun|alguno|lugar)\s+(libre|disponible)\b',
            r'\bhay\s+turno\s+para\s+(mi|m[ií])\b',
            r'\b(yo|tu)\s+(poder|puedo|puede)\s+(ir|venir)\b',
            r'\b(a\s+que|que)\s+hora\s+abren\b',
            r'\b(me\s+gustaria|quisiera)\s+saber.*\bdisponibilidad\b',
            r'\bser[aá]\s+posible\s+ir\b',
            r'\btrabajo.*\bpuedo\s+ir\s+(despues|despu[eé]s)\b',
            r'\bestudio.*\btienen\s+por\s+(la\s+)?(tarde|ma[ñn]ana)\b',
            r'\binformaci[oó]n\s+sobre.*\bturnos\b',
            r'\bcuando\s+es\s+lo\s+mas\s+pronto\b',
            r'\b(nde+|ndee+)\s*,?\s+(tenes|tienen)\s+turno\b',
            # Patrones existentes de consultas ambiguas
            r'\b(que|cual)\s+d[ií]a\s+(est[aá]|tiene|hay)\s+(m[aá]s)?\s*(libre|disponible|mejor)',
            r'\bd[ií]a\s+(intermedio|de\s+la\s+semana|medio)',
            r'\b(cuando|cu[aá]ndo)\s+hay\s+(menos\s+gente|m[aá]s\s+espacio)\b',
            r'\b(mejor|cu[aá]l\s+es\s+el\s+mejor)\s+d[ií]a\b',
            r'\bque\s+d[ií]a\s+(me\s+)?(recomiend|suger)',
            r'\b(recomiend|suger|dime|dame)\s*[aá]?\s*me\s+(un\s+)?(d[ií]a|horario|turno)\b',
            r'\b(recomiend|suger)\s*[aá]?\s*(un\s+)?(d[ií]a|horario|fecha)\b',
            r'\bdisponibilidad\s+(por\s+la\s+)?(ma[ñn]ana|tarde)\b',
            r'\bhoy\s+no\s+tienen\s+disponible\b',
            r'\bpara\s+hoy\s+no\s+est[aá]n\b',
            r'\b(ay|ai|hai|hay)\s+(turnos|horarios|orarios)\s+(para\s+)?(pasado\s+)?ma[ñn]ana\b',
            r'\bhay\s+para\s+ma[ñn]ana\b',
            r'\bpara\s+(ma[ñn]ana|hoy|el\s+\w+)\s+(a\s+la\s+|de\s+la\s+|por\s+la\s+)?(ma[ñn]ana|tarde)\s+(puedo|pued|tiene|hay)\b',
            r'\bpuedo\s+marcar\s+para\s+(ma[ñn]ana|hoy|el\s+\w+)\s+(a\s+la\s+|de\s+la\s+|por\s+la\s+)?(ma[ñn]ana|tarde)\b',
            # Ortografía extrema
            r'\b(kiero|nesecito)\s+(saver|saber)\s+(ke|que)\s+(orarios|horarios)\s+(ay|hay)\b',
            r'\b(ke|que)\s+(orarios|horarios)\s+(ay|hay)\s+para\s+(la\s+)?semana\s+(ke|que)\s+(biene|viene)\b',
            # Patrones para "próxima semana" + consulta
            r'\b(quiero|necesito)\s+(para\s+)?la\s+pr[oó]xima\s+semana.*\b(que|qu[eé]|cual)\s+d[ií]a\b',
            r'\bpr[oó]xima\s+semana.*\b(que|qu[eé])\s+d[ií]a.*\b(hay|tienen|tenes|disponible)\b',
            r'\bpara.*pr[oó]xima\s+semana.*\b(hay|tienen|disponible)\b',
            r'\bque\s+d[ií]a.*\bpr[oó]xima\s+semana\b',
            # Consultas con día específico + pregunta
            r'\bpara\s+(el\s+)?(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes).*\bhay\s+disponible\b',
            r'\bturno\s+para\s+(el\s+)?(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes).*\bhay\b',
            r'\b(quiero|necesito)\s+ir\s+(ma[ñn]ana|hoy|pasado\s+ma[ñn]ana).*\b(que|a\s+que)\s+hora\b',
            r'\b(me\s+gustaria|quisiera)\s+ir.*\bcuando\s+hay\s+turnos\b',
            r'\b(semana\s+que\s+viene|la\s+que\s+viene).*\bcuando\s+hay\b',
            # Preguntas sobre disponibilidad con contexto
            r'\bpuedo\s+(ir|venir|sacar\s+turno)\s+(para\s+)?(hoy|ma[ñn]ana|pasado)\b',
            r'\btengo\s+libre\s+(el\s+)?(lunes|martes|miercoles|mi[eé]rcoles|jueves|viernes).*\bhay\b',
            # Urgencias
            r'\bturno\s+urgente.*\bcuando\s+es\s+lo\s+mas\s+(rapido|r[aá]pido|pronto)\b',
            # Consultas indirectas sobre horarios
            r'\b(trabajo|estudio|salgo).*\b(cierran|abren|atienden|est[aá]n)\b',
            r'\b(puedo|podre|podr[eé])\s+(sacar|ir|venir).*\bsabados\b',
            r'\b(que|k)\s+onda\s+con\s+(los\s+)?(turnos|horarios)\b',
            r'\bcuando\s+hay\s+menos\s+gente\b',
            r'\bque\s+d[ií]a\s+hay\s+(m[aá]s|mas|menos)\s+(espacio|gente)\b',
            r'\bsolo\s+puedo\s+(ir|venir)\s+(despues|despu[eé]s)\b',
            r'\b(che|vieja|bo)\s*,?\s+tienen\s+lugar\s+(para\s+)?hoy\b',
            r'\b(tienen|hay)\s+algo\s+(libre|disponible)\b',
            r'\byo\s+(poder|puedo|puede)\s+ir\s+ma[ñn]ana\b',
            # Consultas condicionales
            r'\b(reservar|agendar).*\b(no\s+se|no\s+s[eé])\s+si\s+(tienen|hay)\s+(lugar|turnos|espacio)\b',
            r'\b(lunes|viernes)\s+o\s+(lunes|viernes)\b',
            r'\bcuando\s+hay\s+(menos|m[aá]s)\s+gente\b',
            # Frases largas descriptivas
            r'\bquisiera\s+saber\s+que\s+d[ií]as\s+tienen\s+disponible\b',
            r'\bnecesito\s+sacar.*\bquisiera\s+saber.*\bd[ií]as\s+(tienen|hay)\b',
            r'\b(quiero|necesito)\s+saber\s+si\s+tienen\s+(turnos|horarios)\b',
            r'\b(disculpa|perdona|perdon)\s*,?\s+.*(hay|tienen)\s+(horarios|turnos)\b',
        ],
        
        'frase_ambigua': [
            r'\b(primera\s+hora|temprano|ma[ñn]ana\s+temprano)\b',
            r'\b(lo\s+antes|cuanto\s+antes|lo\s+m[aá]s\s+pronto)\b',
            r'\b(mejor\s+horario|recomiend|conveniente)\b',
            r'\bque\s+me\s+recomiendas\b',
            r'\bdame\s+uno\b',
            r'\bes\s+mejor.*\bo\s+',  # Comparaciones: "es mejor X o Y"
            r'\b(cual|cu[aá]l)\s+es\s+mas\s+(rapido|r[aá]pido|conveniente)\b',
            r'\bme\s+conviene\s+(sacar|ir|hacer)\b',
        ],
        
        # Datos personales
        'informar_nombre': [
            r'\b(mi\s+nombre\s+es|me\s+llamo|soy)\s+[A-Za-z]',
            # Removido patrón estricto de mayúsculas - se maneja con detección contextual
        ],
        
        'informar_cedula': [
            r'\b\d{1,2}\.\d{3}\.\d{3}\b',  # Formato con puntos: XX.XXX.XXX
            r'\b\d{5,8}\b',  # Número de cédula (5-8 dígitos sin puntos)
            r'\bci\s*:?\s*\d+',
            r'\bcedula\s*:?\s*\d+',
        ],
        
        'informar_email': [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email válido
            r'\bcorreo\s*:?\s*[A-Za-z0-9._%+-]+@',
            r'\bemail\s*:?\s*[A-Za-z0-9._%+-]+@',
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
            r'\b(ese|esa|el|la)\s+(horario|hora)\s+(recomendad|sugerid|est[aá]\s+bien|me\s+gusta)\b',
            r'\b(si|vale|perfecto|ok|bien),?\s+(ese|esa|el|la)\s+(horario|hora)\b',
            r'\b(horario|hora)\s+(recomendad|que\s+me\s+recomendaste)\b',
            r'\bme\s+gusta\s+(ese|el)\s+horario\b',
            r'\beste\s+horario\s+(esta|está)\s+bien\b',
        ],
        
        # Información
        'consultar_requisitos': [
            r'\brequisitos\b',
            r'\bdocumentos?\b',
            r'\b(que|qu[eé]|k|ke|qe|cuales|cu[aá]les)\s+(requisitos|documentos|papeles)\b',
            r'\b(que|qu[eé]|k|ke|qe)\s+(necesito|nececito|nesecito|tengo\s+que\s+llevar|traer)\b',
            r'\b(que|qu[eé]|k|ke|qe)\s+debo\s+(traer|llevar|presentar)\b',
            r'\b(que|qu[eé]|k|ke|qe)\s+(documentos|requisitos|papeles)\s+(necesito|nececito|nesecito|llevar|traer)\b',
            r'\bpara\s+sacar\s+(cedula|cédula|sedula)\s+(que|qu[eé]|k)\s+necesita',
            r'\b(como|c[oó]mo|komo)\s+hago\s+para\s+sacar\s+(la\s+)?(cedula|cédula|sedula)\b',
            r'\bquisiera\s+saber\s+(como|c[oó]mo)\s+hago\s+para\s+sacar\b',
            r'\btengo\s+que\s+llevar\s+(alg[uú]n|alguno)\s+(documento|papel)\b',
            r'\b(es\s+mi\s+primer|primera|primer)\s+(cedula|cédula|sedula|tramite|trámite|vez).*\b(que|qu[eé]|k)\s+(necesito|tengo\s+que\s+hacer)\b',
            r'\bnunca\s+fui\s*,?\s+(como|c[oó]mo)\s+hago\b',
            r'\b(disculpe|perd[oó]n)\s+.*\bcu[aá]les\s+son\s+los\s+requisitos\b',
            r'\b(podria|podr[ií]a)\s+decirme.*\brequisitos\b',
            r'\binfo(rmaci[oó]n)?\s+(x\s+favor|por\s+favor|xfa|pls)?\b',
            r'\b(tengo|soy).*\bpuedo\s+sacar\s+(la\s+)?(cedula|sedula)\b',
            r'\bsoy\s+(extranjero|menor).*\bpuedo\s+sacar\b',
            # Ortografía extrema
            r'\b(k|ke)\s+(papeles|documentos)\s+(tengo|tenemos)\s+(k|ke)\s+(traer|llevar)\b',
            r'\bpara\s+(sakar|sacar)\s+(la\s+)?sedula\b',
        ],
        
        'consultar_ubicacion': [
            # Números de contacto / teléfono (ALTA PRIORIDAD)
            r'\b(hay|tienen|tenes|tenés)\s+(alg[uú]n|algun|un)?\s*n[uú]mero\b',
            r'\bn[uú]mero\s+(de\s+)?(contacto|tel[eé]fono|telefono)\b',
            r'\b(tienen|tenes|tenés|hay)\s+(un\s+)?(tel[eé]fono|telefono|contacto|n[uú]mero)\b',
            r'\b(puedo|pwedo)\s+llamar\b',
            r'\b(tienen|hay)\s+(un\s+)?n[uú]mero\s+(que|para)\s+(pueda|poder)\s+llamar\b',
            r'^\s*(hay|tienen)\s+(numero|número)\s*\??\s*$',
            # Contacto humano / hablar con persona
            r'\b(quiero|kiero|necesito|nesecito)\s+(hablar|ablar)\s+con\s+(alguien|una\s+persona|un\s+humano)\b',
            r'\b(puedo|pwedo)\s+(hablar|ablar)\s+con\s+(alguien|una\s+persona|un\s+operador)\b',
            r'\b(contacto|kontacto)\s+(humano|con\s+persona)\b',
            r'\b(hablar|ablar)\s+con\s+(un\s+)?(operador|persona|humano|alguien)\b',
            r'\b(me\s+)?(comunico|comunicarme)\s+con\s+(alguien|una\s+persona)\b',
            # Múltiples consultas: priorizar cuando "donde" aparece primero
            r'^(hola\s*,?\s*)?(donde|dónde|d[oó]nde)\s+(quedan|queda|keda|est[aá]n|estan).*\by\s+(que|qu[eé])\s+(horarios|d[ií]as)',
            r'\b(donde|dónde|adonde|ad[oó]nde|dnd|ubicaci[oó]n|direcci[oó]n|como\s+llego)\b',
            r'\b(queda|keda|kedan|quedan)\b.*\b(oficina|lugar|ofi)\b',
            r'\b(adonde|ad[oó]nde)\s+(queda|keda|kedan|quedan)\s+(la\s+)?(ofi|oficina)',
            r'\b(donde|dónde|d[oó]nde)\s+(queda|keda|quedan|kedan|esta|está|est[aá]n)\b',
            r'\b(tel[eé]fono|telefono|celular|contacto|n[uú]mero|numero|whatsapp|tlf)\b',
            r'\b(como|c[oó]mo|komo)\s+(los\s+)?(puedo\s+|puedes\s+)?(contactar|llamar|comunicar|llegar)',
            r'\b(como|c[oó]mo)\s+hago\s+para\s+llegar\b',
            r'\bhay\s+(alg[uú]n|alguno)\s+(tel[eé]fono|telefono|contacto|n[uú]mero)\b',
            r'\b(en\s+que|que)\s+lugar\s+se\s+encuentran\b',
            r'\bcu[aá]l\s+es\s+la\s+direcci[oó]n\b',
            r'\bcomo\s+puedo\s+(ir|llegar)\s+(hasta\s+)?all[ií]\b',
            r'\bvivo\s+lejos.*\b(donde|vale\s+la\s+pena)\b',
            r'\b(epa|ey)\s+(hermano|amigo).*\bdonde\s+est[aá]n\s+ubicados\b',
            r'\b(soy\s+de|vengo\s+de).*\btienen\s+sucursal\b',
            r'\b(necesito|quiero)\s+saber\s+donde\s+(est[aá]n|quedan)\b',
            r'\bdonde\s+(est[aá]n|quedan).*\b(si\s+)?tienen\s+turnos\b',
            r'\b(mi\s+hermano|mi\s+amigo).*\b(ahi|all[ií]).*\bcomo\s+puedo\s+ir\b',
            r'^\s*tlf\s+(de\s+)?contacto\s*\??\s*$',
        ],
        
        'consultar_costo': [
            # Múltiples consultas: priorizar cuando "cuanto" aparece primero
            r'^(hola\s*,?\s*)?(cuanto|cu[aá]nto|kuanto)\s+(sale|cuesta|vale|bale).*\by\s+(que|qu[eé])\s+(documentos|requisitos|papeles)',
            r'\b(cuanto|cu[aá]nto|kuanto|kwanto|cuant)\s+(cuesta|kuesta|sale|vale|bale|me\s+sale|cobran)\b',
            r'\b(precio|costo|arancel)\b',
            r'\b(cuanto|cu[aá]nto|kuanto)\s+es\s+(el\s+)?(costo|precio)\b',
            r'\bpara\s+sacar\s+(la\s+)?(cedula|cédula)\s+(cuanto|cu[aá]nto)\b',
            r'\b(me\s+sale|sale|salir)\s+(el\s+)?(tramite|trámite|esto)\b',
            r'\b(que\s+)?precio\s+tiene\b',
            r'\bdebo\s+pagar\s+algo\b',
            r'\bno\s+tengo\s+mucho.*\b(es\s+)?caro\b',
            r'\bperdi\s+mi\s+cedula.*\bcuanto\s+me\s+cobran\b',
            r'\bcuanto\s+me\s+(va\s+a\s+)?salir\b',
            r'\bes\s+(muy\s+)?caro\s+sacar\b',
            # Frases largas descriptivas
            r'\bnecesito\s+saber\s+cuanto.*\b(costar|cobran|sale)\b',
            r'\bperdi\s+mi\s+cedula.*\bcuanto\s+me\s+(va\s+a\s+)?costar\b',
        ],
        
        # Consulta de tiempo de espera
        'consulta_tiempo_espera': [
            r'\b(cuanto|cu[aá]nto)\s+(tiempo|demor[ao]|espera|tarda)\b',
            r'\btiempo\s+de\s+espera\b',
            r'\bcu[aá]nto\s+hay\s+que\s+esperar\b',
            r'\bcu[aá]nto\s+(voy\s+a|tengo\s+que)\s+esperar\b',
            r'\bvoy\s+a\s+esperar\s+mucho\b',
            r'\bcu[aá]nto\s+(me\s+)?(demora|tarda)\b',
        ],
        
        # Saludos y despedidas
        'greet': [
            r'\b(hola|ola|buenas|buen\s+d[ií]a|buenos\s+d[ií]as|buenas\s+tardes)\b',
            r'^(hola|ola|hey|hi)$',
            r'\b(mba\s+epa)\b',
            r'\b(che|que\s+onda)\b.*\b(como|que|komo)\s+(hago|puedo)\b',
            r'\b(ola|hola)\s+(kmo|como|k)\s+(estas|est[aá]s)\b',
        ],
        
        'goodbye': [
            r'\b(chau|adi[oó]s|hasta\s+luego|nos\s+vemos)\b',
            r'^(bye|chao)$',
        ],
        
        # Afirmaciones y negaciones (solo frases cortas para evitar falsos positivos)
        'affirm': [
            r'^(s[ií]|si|ok|okay|dale|perfecto|correcto|exacto|confirmo)\s*$',
            r'^\s*(si|s[ií])\s+(por favor|porfavor|porfa|esta bien|está bien)\s*$',
            r'\b(ese|esa|eso)\s+(d[ií]a|horario|hora)\s+(est[aá]|esta)\s+(bien|perfecto|ok)\b',
            r'\b(ese|esa|eso)\s+(d[ií]a|horario|hora|mismo|misma)\b',
            r'\bel\s+(horario|d[ií]a|hora)\s+que\s+me\s+(recomendaste|dijiste|sugeriste)\b',
            r'\bme\s+(sirve|conviene|viene\s+bien|parece\s+bien)\b',
        ],
        
        'negacion': [
            r'\b(no|nop|nope)\s+(me\s+sirve|puedo|me\s+llamo|es\s+mi|es\s+el)\b',
            r'\bno\s+ese\s+no\s+(es|está|esta)\b',
            r'\bmejor\s+(otro|otra|lo\s+dejo)\s+(dia|día|hora|horario|para)\b',
            r'\bprefiero\s+(otro|otra)\s+(dia|día|hora|horario)\b',
            r'\bno\s+(me\s+)?(sirve|conviene|puedo|va|viene\s+bien)\b',
            r'\bno\s+me\s+llamo\s+(as[ií]|asi)\b',
            r'\bno\s+(ese|esa)\s+no\s+es\s+mi\s+(email|correo|nombre|cedula|cédula)\b',
            r'\bequivocaste\s+mi\s+(email|correo|nombre)\b',
            r'\b(ese|esa)\s+horario\s+no\s+me\s+viene\s+bien\b',
            r'\bno\s+(es|esta|está)\s+mi\s+nombre\s+(correcto|bien)\b',
            r'\bno\s+no\s*,?\s+mi\s+nombre\s+(esta|está)\s+mal\b',
            r'\bmi\s+(nombre|email|cedula|cédula)\s+(esta|está)\s+mal\b',
            r'\b(ese|esa)\s+(no\s+es|no\s+era)\s+mi\s+(nombre|email|cedula)\b',
            r'\bme\s+equivoqu[eé]\b',
        ],
        
        'cancelar': [
            r'\bcancelar\b',
            r'\bcancelo\b',
            r'\bmejor\s+lo\s+cancel',
            r'\bya\s+no\s+quiero\s+(el\s+)?turno\b',
            r'\bno\s+quiero\s+el\s+turno\b',
            r'\banular\b',
            r'\bno\s+quiero\s+(m[aá]s|seguir)\b',
        ],
        
        'deny': [
            r'^\s*no\s*$',  # Solo "no"
            r'\b(nop|nope|neg)\b',
        ],
        
        # Modo desarrollador (acceso al dashboard)
        'modo_desarrollador': [
            r'\bmodo\s+desarrollador\b',
            r'\bdev\s+mode\b',
            r'\bdashboard\b',
            r'\bpanel\s+admin\b',
            r'\badministrador\b',
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
        
        # ========================================================
        # DETECCIÓN PRIORITARIA: Comandos de administrador
        # ========================================================
        comandos_admin = [
            'modo desarrollador', 'modo dev', 'dashboard', 
            'panel admin', 'administrador', 'panel de control',
            'admin panel', 'dev mode', 'admin'
        ]
        
        if mensaje_lower in comandos_admin:
            logger.info(f"🔧 Comando de administrador detectado: '{mensaje_lower}'")
            return ("modo_desarrollador", 0.99)
        
        # DETECCIÓN ESPECIAL: Frases muy cortas ambiguas (1-3 palabras)
        frases_cortas_ambiguas = {
            'hoy': 'consultar_disponibilidad',
            'que hay hoy': 'consultar_disponibilidad',
            'que hay hoy?': 'consultar_disponibilidad',
            'hay para hoy': 'consultar_disponibilidad',
            'hay para hoy?': 'consultar_disponibilidad',
            'hay horarios disponibles de tarde?': 'consultar_disponibilidad',
            'de tarde hay?': 'consultar_disponibilidad',
            'de tarde hay': 'consultar_disponibilidad',
            'hay horarios disponibles de tarde': 'consultar_disponibilidad',
            'que costo tiene?': 'consultar_costo',
            'que costo tiene': 'consultar_costo',
            'cuanto cuesta?': 'consultar_costo',
            'cuanto cuesta': 'consultar_costo',
            'mañana': 'informar_fecha',
            'para hoy': 'consultar_disponibilidad',
            'dame uno': 'agendar_turno',  # Usuario pidiendo turno (cualquiera)
            'el mejor': 'frase_ambigua',
            'el que sea': 'frase_ambigua',
            'cual seria': 'frase_ambigua',
            'cual seria?': 'frase_ambigua',
            'ese mismo': 'frase_ambigua',
            'lo que tengan': 'frase_ambigua',
            'cualquiera me sirve': 'frase_ambigua',
            'lo antes posible': 'frase_ambigua',
            'temprano': 'frase_ambigua',
            'que me recomiendas': 'frase_ambigua',
            'que me recomiendas?': 'frase_ambigua',
            'antes de las 10': 'frase_ambigua',
            'mba epa, como hago': 'greet',
            'mba epa, como hago?': 'greet',
            'ola kmo estas': 'greet',
            'para hoy no estan': 'consultar_disponibilidad',
            'para hoy no están': 'consultar_disponibilidad',
            'para hoy no estan?': 'consultar_disponibilidad',
            'para hoy no están?': 'consultar_disponibilidad',
            'que dia me recomendas': 'consultar_disponibilidad',
            'que dia me recomendas?': 'consultar_disponibilidad',
            'q onda, hay turnos?': 'consultar_disponibilidad',
            'q onda hay turnos': 'consultar_disponibilidad',
            'ncs turno xfa': 'agendar_turno',
            'info x favor': 'consultar_requisitos',
            'reservar una cita': 'agendar_turno',
            'tlf de contacto?': 'consultar_ubicacion',
            'tlf de contacto': 'consultar_ubicacion',
            'a que numero puedo llamar?': 'consultar_ubicacion',
            'a que numero puedo llamar': 'consultar_ubicacion',
            'cual es numero de contacto?': 'consultar_ubicacion',
            'cual es numero de contacto': 'consultar_ubicacion',
            'tienen numero de contacto?': 'consultar_ubicacion',
            'tienen numero de contacto': 'consultar_ubicacion',
            'numero de contacto?': 'consultar_ubicacion',
            'numero de contacto': 'consultar_ubicacion',
            'numero de telefono?': 'consultar_ubicacion',
            'numero de telefono': 'consultar_ubicacion',
            'hay algun numero de contacto?': 'consultar_ubicacion',
            'hay algun numero de contacto': 'consultar_ubicacion',
            'tienen un numero de contacto?': 'consultar_ubicacion',
            'tienen un numero de contacto': 'consultar_ubicacion',
            'puedo llamar?': 'consultar_ubicacion',
            'puedo llamar': 'consultar_ubicacion',
            'tienen un numero que pueda llamar?': 'consultar_ubicacion',
            'tienen un numero que pueda llamar': 'consultar_ubicacion',
            'hay numero?': 'consultar_ubicacion',
            'hay numero': 'consultar_ubicacion',
            'tienen numero?': 'consultar_ubicacion',
            'tienen numero': 'consultar_ubicacion',
        }
        
        if mensaje_lower in frases_cortas_ambiguas:
            intent_especial = frases_cortas_ambiguas[mensaje_lower]
            logger.info(f"🎯 Frase corta ambigua detectada: {intent_especial} (0.93)")
            return (intent_especial, 0.93)
        
        # =================================================================
        # DETECCIONES CONTEXTUALES Y PATRONES IMPORTANTES
        # =================================================================
        
        # Detectar correcciones de datos ("mi nombre esta mal, es...", "dije para las X")
        if any(frase in mensaje_lower for frase in ['esta mal', 'está mal', 'es incorrecto', 'no es correcto']):
            # Verificar si menciona nombre/email/cedula y luego da un valor
            if ('mi nombre' in mensaje_lower or 'mi email' in mensaje_lower or 'mi cedula' in mensaje_lower or 'mi cédula' in mensaje_lower):
                logger.info(f"🎯 [CONTEXTO] Usuario corrige datos → negacion")
                return ("negacion", 0.96)
        
        # Detectar corrección explícita ("dije para...", "yo dije...")
        if any(frase in mensaje_lower for frase in ['dije', 'yo dije', 'habia dicho', 'había dicho']):
            # Verificar si da una hora o fecha nueva
            import re
            if re.search(r'\b\d{1,2}(:\d{2})?(\s+(y\s+media|y\s+cuarto))?\b', mensaje):
                logger.info(f"🎯 [CONTEXTO] Usuario corrige hora → negacion")
                return ("negacion", 0.96)
        
        # Detectar EMAIL cuando el sistema lo pidió
        if contexto.fecha and contexto.hora and not contexto.email:
            import re
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', mensaje):
                logger.info(f"🎯 [CONTEXTO] Usuario proporciona email → informar_email")
                return ("informar_email", 0.98)
        
        # Detectar ACEPTACIÓN de hora recomendada (ANTES de confirmación final)
        if contexto.hora_recomendada and not contexto.hora:
            # Frases de aceptación de recomendación
            if any(frase in mensaje_lower for frase in [
                'esta bien', 'está bien', 'ok', 'vale', 'acepto', 'perfecto',
                'me parece bien', 'si esa', 'sí esa', 'esa hora',
                'la hora que recomiendas', 'la que recomiendas'
            ]):
                logger.info(f"🎯 [CONTEXTO] Usuario acepta hora recomendada → elegir_horario")
                return ("elegir_horario", 0.97)
        
        # Detectar "perfecto" cuando tiene hora_recomendada Y fecha
        if contexto.hora_recomendada and contexto.fecha and not contexto.hora:
            if mensaje_lower.strip() in ['perfecto', 'ok', 'vale', 'bien', 'si', 'sí', 'acepto']:
                logger.info(f"🎯 [CONTEXTO] Usuario acepta recomendación simple → elegir_horario")
                return ("elegir_horario", 0.97)
            # Detectar "ya me recomendaste" como aceptación implícita
            if any(frase in mensaje_lower for frase in ['ya me recomendaste', 'ya me dijiste', 'ya me diste', 'tu recomendacion', 'tu recomendación']):
                logger.info(f"🎯 [CONTEXTO] Usuario acepta recomendación implícitamente → elegir_horario")
                return ("elegir_horario", 0.96)
        
        # Detectar CAMBIO de hora cuando YA tiene hora asignada
        if contexto.hora:
            # Frases que indican cambiar/modificar hora
            if any(frase in mensaje_lower for frase in [
                'cambiar de horario', 'cambiar el horario', 'cambiar la hora',
                'cambiar de hora', 'modificar', 'actualizar',
                'quiero cambiar', 'puedo cambiar', 'mejor para las'
            ]):
                # Y tiene una hora en el mensaje
                import re
                if re.search(r'\b([0-9]{1,2}):?([0-9]{2})?\b', mensaje):
                    logger.info(f"🎯 [CONTEXTO] Usuario cambia hora existente → elegir_horario")
                    return ("elegir_horario", 0.96)
        
        # Detectar CAMBIO de fecha cuando YA tiene fecha asignada
        if contexto.fecha:
            # Frases que indican cambiar fecha
            if any(frase in mensaje_lower for frase in [
                'cambiar mi turno para', 'cambiar para',
                'mejor para el', 'prefiero el',
                'puedo cambiar para', 'mover para'
            ]):
                # Y tiene un día de la semana o fecha
                if any(dia in mensaje_lower for dia in ['lunes', 'martes', 'miercoles', 'miércoles', 'jueves', 'viernes', 'sabado', 'sábado']):
                    logger.info(f"🎯 [CONTEXTO] Usuario cambia fecha existente → consultar_disponibilidad")
                    return ("consultar_disponibilidad", 0.96)
        
        # Detectar confirmación simple cuando tiene fecha+hora+email (datos completos)
        if contexto.nombre and contexto.fecha and contexto.hora and contexto.email:
            mensaje_limpio = mensaje_lower.strip()
            if mensaje_limpio in ['esta bien', 'está bien', 'ok', 'vale', 'si', 'sí', 'perfecto', 'de acuerdo', 'confirmo', 'confirmado', 'confirm', 'acepto', 'acepto']:
                logger.info(f"🎯 [CONTEXTO] Usuario confirma turno completo → confirmar (msg: '{mensaje_limpio}')")
                return ("confirmar", 0.97)
            # También detectar frases de confirmación
            if any(frase in mensaje_lower for frase in ['si confirmo', 'sí confirmo', 'si acepto', 'sí acepto', 'todo bien', 'esta todo bien', 'está todo bien']):
                logger.info(f"🎯 [CONTEXTO] Usuario confirma turno con frase → confirmar")
                return ("confirmar", 0.97)
        
        # Detectar cambio de hora cuando ya tiene fecha PERO NO hora
        if contexto.fecha and not contexto.hora:
            # Frases que indican elegir/cambiar hora
            if any(palabra in mensaje_lower for palabra in ['cambiar', 'mejor', 'prefiero', 'quiero']):
                # Y tiene una hora en el mensaje
                import re
                if re.search(r'\b([0-9]{1,2}):?([0-9]{2})?\b', mensaje):
                    logger.info(f"🎯 [CONTEXTO] Usuario elige/cambia hora → elegir_horario")
                    return ("elegir_horario", 0.96)
        
        # Detectar hora aislada cuando esperamos hora
        if contexto.fecha and not contexto.hora:
            # Si el mensaje es solo una hora o "para/a las X"
            import re
            if re.match(r'^(para\s+)?(a\s+)?las?\s+[0-9]{1,2}(:[0-9]{2})?$', mensaje_lower) or \
               re.match(r'^[0-9]{1,2}(:[0-9]{2})?$', mensaje_lower):
                logger.info(f"🎯 [CONTEXTO] Usuario da hora directamente → elegir_horario")
                return ("elegir_horario", 0.97)
        
        # Detectar tipo de trámite cuando pregunta por cédula
        if contexto.nombre and not contexto.cedula:
            # Primera vez / no tengo cédula
            if any(frase in mensaje_lower for frase in ['primera vez', '1ra vez', 'primer tramite', 'no tengo cedula', 'no tengo cédula', 'todavia no tengo', 'todavía no tengo', 'aun no tengo', 'aún no tengo']):
                logger.info(f"🎯 [CONTEXTO] Tipo de trámite detectado: primera_vez")
                contexto.tipo_tramite = 'primera_vez'
                return ("informar_tipo_tramite", 0.96)
            
            # Pérdida/Robo
            if any(frase in mensaje_lower for frase in ['se me perdio', 'se me perdió', 'perdi', 'perdí', 'me la robaron', 'me robaron', 'se me extravió', 'se me extravi', 'extravio', 'extravío', 'robo']):
                logger.info(f"🎯 [CONTEXTO] Tipo de trámite detectado: perdida")
                contexto.tipo_tramite = 'perdida'
                return ("informar_tipo_tramite", 0.96)
            
            # Extranjero
            if any(frase in mensaje_lower for frase in ['soy extranjero', 'extranjera', 'no soy paraguayo', 'no soy paraguaya', 'extranjeria']):
                logger.info(f"🎯 [CONTEXTO] Tipo de trámite detectado: extranjero")
                contexto.tipo_tramite = 'extranjero'
                return ("informar_tipo_tramite", 0.96)
        
        # Detectar negación sin cédula (sin importar contexto) - SOLO si no detectamos tipo arriba
        palabras_negacion_sin_cedula = [
            'se me perdio', 'se me perdió', 'perdi mi cedula', 'perdí mi cédula',
            'no tengo cedula', 'no tengo cédula', 'sin cedula', 'sin cédula',
            'no la tengo', 'me la robaron', 'se me extravió', 'se me extravi',
            'todavia no tengo', 'todavía no tengo', 'aun no tengo', 'aún no tengo'
        ]
        
        if any(neg in mensaje_lower for neg in palabras_negacion_sin_cedula):
            logger.info(f"🎯 [PATRON] negacion_sin_cedula (0.95)")
            return ("negacion_sin_cedula", 0.95)
        
        # SOLO detectar "no tengo" SI estamos esperando cédula
        if contexto.nombre and not contexto.cedula:
            if mensaje_lower in ['no tengo', 'no tengo nada', 'nada']:
                logger.info(f"🎯 [CONTEXTO] negacion_sin_cedula (0.98)")
                return ("negacion_sin_cedula", 0.98)
        
        # Palabras clave de intents de ACCIÓN (no son nombres)
        palabras_accion = ['agendar', 'turno', 'cita', 'horario', 'disponibilidad', 
                          'requisitos', 'ubicacion', 'ubicación', 'direccion', 'dirección',
                          'costo', 'precio', 'cuanto', 'cuánto', 'pagar',
                          'consultar', 'ver', 'necesito', 'información', 'informacion',
                          'oficina', 'ofi', 'queda', 'keda', 'esta', 'esta ubicada', 'como llego',
                          'ayuda', 'ayudar', 'puedes', 'necesitas', 'hacer',
                          'tienen', 'hay', 'libre', 'disponible', 'gente', 'espacio',
                          'recomendas', 'recomiendas', 'asi', 'así', 'llamo', 'poder', 'cuando',
                          'adonde', 'donde', 'contactar', 'cancelar', 'cancelo']
        
        # Si el mensaje contiene palabras de acción, NO validar como nombre
        es_accion = any(palabra in mensaje_lower for palabra in palabras_accion)
        
        # Lista de palabras comunes que NO son nombres (más específica)
        # Solo palabras que definitivamente NO pueden ser parte de un nombre
        palabras_prohibidas = {
            'yo', 'tu', 'el', 'ella', 'nosotros', 'ustedes', 'ellos',
            'no', 'nada', 'algo', 'todo', 'nadie', 'alguien',
            'se', 'me', 'te', 'le', 'nos', 'les', 'lo', 'la', 'los', 'las',
            'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
            'muy', 'mucho', 'poco', 'mas', 'menos', 'bien', 'mal',
            'loco', 'loca', 'tonto', 'tonta', 'raro', 'rara',
            'cosa', 'cosas', 'malo', 'mala', 
            'macaco', 'mono', 'gorila', 'gorilla', 'animal', 'volador', 'voladora',
            'idiota', 'estupido', 'estúpido', 'bobo', 'boba', 'insano', 'insana',
            'payaso', 'ridiculo', 'ridículo', 'absurdo', 'absurda',
            'gaga', 'total', 'pepe', 'test', 'prueba', 'fake', 'falso'
        }
        
        # DETECCIÓN DE NOMBRES CONTEXTUAL (SIMPLIFICADA)
        # Si NO tenemos nombre y el mensaje es 1-4 palabras solo con letras, es probable que sea un nombre
        if not contexto.nombre and not es_accion:
            palabras = mensaje.split()
            if 1 <= len(palabras) <= 4:
                palabras_lower = [p.lower() for p in palabras]
                
                # Verificar que NO contengan palabras prohibidas
                if any(p in palabras_prohibidas for p in palabras_lower):
                    pass  # No es nombre, seguir con clasificación normal
                # Verificar que sean palabras válidas (al menos 2 letras cada una, solo letras)
                elif all(len(p) >= 2 and p.isalpha() for p in palabras):
                    # Es un nombre válido
                    logger.info(f"🎯 Intent detectado por contexto: informar_nombre (0.92)")
                    return ("informar_nombre", 0.92)
        
        # CONTEXTO: Si ya tenemos nombre pero no cédula, y el mensaje son solo números
        if contexto.nombre and not contexto.cedula:
            if re.match(r'^\d{5,8}$', mensaje.strip()):
                logger.info(f"🎯 Intent detectado por contexto: informar_cedula (0.98)")
                return ("informar_cedula", 0.98)
        
        # CONTEXTO: Si ya tenemos fecha pero no hora, y el mensaje habla de hora ESPECÍFICA
        if contexto.fecha and not contexto.hora:
            # Detectar frases como "las 8", "para las 7", "a las 10", "8 está bien"
            # PERO NO frases sobre consulta de horarios ("que horarios", "cierran", "abren", "atienden", "hay")
            if re.search(r'\b(las|para\s+las|a\s+las)\s*\d{1,2}\b', mensaje_lower) and \
               not re.search(r'\b(que|qu[eé]|cuales|cu[aá]les|cual|cu[aá]l)\s+(horarios|horas|hora)\b', mensaje_lower) and \
               not re.search(r'\b(cierran|abren|atienden|trabajan|est[aá]n|hay|tienen)\b', mensaje_lower):
                logger.info(f"🎯 Intent detectado por contexto: elegir_horario (0.98)")
                return ("elegir_horario", 0.98)
        
        # ========================================================================
        # PIPELINE DE CLASIFICACIÓN UNIFICADA CON LÓGICA DIFUSA
        # ========================================================================
        
        # 1. CLASIFICACIÓN POR PATRONES (Regex)
        intent_patron, confianza_patron = self._clasificar_por_patrones(mensaje_lower)
        
        # CONTEXTO: Si el patrón dice "informar_nombre" pero ya tenemos nombre, buscar cédula
        if intent_patron == 'informar_nombre' and contexto.nombre and not contexto.cedula:
            # Verificar si el mensaje contiene números (probablemente cédula)
            if re.search(r'\d{5,8}', mensaje):
                logger.info(f"🎯 Intent corregido por contexto: informar_cedula (0.95)")
                return ("informar_cedula", 0.95)
        
        # 2. CLASIFICACIÓN CON LLM
        intent_llm = 'nlu_fallback'
        confianza_llm = 0.0
        
        if self.llm_url:
            try:
                intent_llm, confianza_llm = self._clasificar_con_llm(mensaje, contexto)
            except Exception as e:
                logger.warning(f"⚠️ Error en LLM: {e}")
        
        # 3. CLASIFICACIÓN CON LÓGICA DIFUSA (solo para análisis, no afecta decisión final todavía)
        intent_fuzzy, confianza_fuzzy = clasificar_con_logica_difusa(mensaje, threshold=0.3)
        logger.info(f"🌟 [FUZZY] Clasificación difusa: {intent_fuzzy} ({confianza_fuzzy:.2f})")
        
        # 4. DETERMINAR SCORE DE CONTEXTO (si aplicamos detección contextual arriba)
        # Para contexto, usamos 0 si no se aplicó nada, o alta confianza si se detectó contextualmente
        score_contexto = 0.0
        intent_contexto = ''
        
        # Si patrón tiene MUY ALTA confianza (>0.92), asumimos que fue detección contextual prioritaria
        if confianza_patron > 0.92:
            score_contexto = confianza_patron
            intent_contexto = intent_patron
            logger.info(f"� Detección contextual prioritaria: {intent_contexto} ({score_contexto:.2f})")
            # Retornar directamente, es una detección super confiable
            return intent_contexto, score_contexto
        
        # 5. FUSIÓN DIFUSA: Combinar las 4 fuentes
        logger.info(f"\n🔀 FUSIÓN DIFUSA DE CLASIFICADORES:")
        logger.info(f"   📊 Contexto: {intent_contexto or 'N/A'} ({score_contexto:.2f})")
        logger.info(f"   🔍 Regex:    {intent_patron} ({confianza_patron:.2f})")
        logger.info(f"   🤖 LLM:      {intent_llm} ({confianza_llm:.2f})")
        logger.info(f"   � Fuzzy:    {intent_fuzzy} ({confianza_fuzzy:.2f})")
        
        intent_final, confianza_final, detalles = clasificar_con_fusion_difusa(
            mensaje,
            score_contexto, intent_contexto,
            confianza_patron, intent_patron,
            confianza_llm, intent_llm
        )
        
        logger.info(f"✨ RESULTADO FINAL: {intent_final} ({confianza_final:.2f}) [fuente: {detalles.get('source')}]")
        
        # 6. VALIDACIÓN FINAL: Si confianza es muy baja, fallback
        if confianza_final < 0.3:
            logger.warning(f"❓ Confianza muy baja, usando fallback")
            return 'nlu_fallback', confianza_final
        
        return intent_final, confianza_final
    
    def _clasificar_por_patrones(self, mensaje: str) -> Tuple[str, float]:
        """Clasifica usando patrones de regex"""
        
        # PALABRAS CLAVE ÚNICAS (match exacto, alta confianza)
        palabras_exactas = {
            'requisitos': 'consultar_requisitos',
            'documentos': 'consultar_requisitos',
            'ubicacion': 'consultar_ubicacion',
            'ubicación': 'consultar_ubicacion',
            'direccion': 'consultar_ubicacion',
            'dirección': 'consultar_ubicacion',
            'telefono': 'consultar_ubicacion',
            'teléfono': 'consultar_ubicacion',
            'contacto': 'consultar_ubicacion',
            'whatsapp': 'consultar_ubicacion',
            'numero': 'consultar_ubicacion',
            'número': 'consultar_ubicacion',
            'costo': 'consultar_costo',
            'precio': 'consultar_costo',
            'turno': 'agendar_turno',
            'horarios': 'consultar_disponibilidad',
            'disponibilidad': 'consultar_disponibilidad',
        }
        
        # Si el mensaje es solo 1-2 palabras, verificar match exacto
        palabras_mensaje = mensaje.strip().split()
        if len(palabras_mensaje) <= 2:
            for palabra in palabras_mensaje:
                palabra_lower = palabra.lower().strip('¿?¡!.,')
                if palabra_lower in palabras_exactas:
                    return palabras_exactas[palabra_lower], 0.96
        
        # Si el mensaje es MUY corto (1 palabra) y contiene "hoy", priorizar disponibilidad
        if len(palabras_mensaje) == 1 and palabras_mensaje[0].lower() == 'hoy':
            return 'consultar_disponibilidad', 0.93
        
        # VERIFICACIÓN PRIORITARIA: modo_desarrollador debe verificarse PRIMERO
        # para evitar que se confunda con nombre
        intents_prioritarios = ['modo_desarrollador', 'informar_email', 'informar_cedula', 
                               'elegir_horario', 'affirm', 'deny', 'negacion', 'cancelar']
        
        # Primero verificar intents prioritarios
        for intent in intents_prioritarios:
            if intent in self.PATRONES_INTENT:
                for patron in self.PATRONES_INTENT[intent]:
                    if re.search(patron, mensaje, re.IGNORECASE):
                        match = re.search(patron, mensaje, re.IGNORECASE)
                        score = len(match.group()) / len(mensaje)
                        score = min(0.95, score + 0.5)  # Boost alto para prioritarios
                        return intent, score
        
        # Luego verificar el resto
        mejor_intent = None
        mejor_score = 0.0
        
        for intent, patrones in self.PATRONES_INTENT.items():
            if intent in intents_prioritarios:
                continue  # Ya verificado
                
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
            logger.info("⚠️ LLM no disponible, saltando clasificación LLM")
            return 'nlu_fallback', 0.0
        
        logger.info(f"🤖 Consultando LLM para: '{mensaje[:50]}...'")
        
        # Construir contexto para el LLM
        contexto_str = ""
        if contexto.nombre and not contexto.cedula:
            contexto_str = " [CONTEXTO: Ya tenemos nombre, ahora esperamos cédula]"
        elif contexto.nombre and contexto.cedula and not contexto.fecha:
            contexto_str = " [CONTEXTO: Ya tenemos nombre y cédula, ahora esperamos fecha]"
        elif contexto.fecha and not contexto.hora:
            contexto_str = " [CONTEXTO: Ya tenemos fecha, ahora esperamos hora]"
        
        prompt = f"""Clasifica esta frase en UNO de estos intents. Responde SOLO el nombre del intent, sin explicaciones.

FRASE: "{mensaje}"{contexto_str}

INTENTS VÁLIDOS:
- informar_nombre: Solo dice su nombre (1-4 palabras, como "Juan Pérez", "María", "Carlos González López")
- informar_cedula: Solo dice números de cédula (5-8 dígitos)
- informar_fecha: Solo dice una fecha (mañana, lunes, 15 de noviembre, etc)
- informar_email: Solo dice un email
- agendar_turno: Quiere agendar/sacar/reservar turno o cita
- consultar_disponibilidad: Pregunta por horarios, disponibilidad, qué días hay, qué hay hoy
- consultar_requisitos: Pregunta qué necesita, documentos, requisitos
- consultar_ubicacion: Pregunta dónde queda, dirección, teléfono, contacto
- consultar_costo: Pregunta cuánto cuesta, precio, si es gratis
- negacion_sin_cedula: Dice que NO tiene cédula o se le perdió
- negacion: Dice que NO le sirve un horario, quiere cambiar algo, o se queja ("ya te dije...")
- cancelar: Quiere cancelar el turno
- greet: Saluda (hola, buenas, etc)
- goodbye: Se despide
- affirm: Confirma algo (sí, ok, dale, ese día está bien, me sirve, ya te lo dije)
- deny: Niega (no)

IMPORTANTE: Responde SOLO una palabra (el nombre del intent), SIN puntos, SIN explicaciones, SIN mayúsculas innecesarias.

Ejemplos:
- "Juan Pérez" [esperando nombre] → informar_nombre
- "jhonatan" [esperando nombre] → informar_nombre
- "1234567" [esperando cédula] → informar_cedula
- "no tengo" [esperando cédula] → negacion_sin_cedula
- "quiero sacar turno" → agendar_turno
- "ese día está bien" → affirm
- "ese horario me sirve" → affirm
- "ya te dije mi cédula" → affirm
- "ya lo puse" → affirm
- "que hay hoy?" → consultar_disponibilidad
- "hay horarios para mañana?" → consultar_disponibilidad
- "que documentos necesito" → consultar_requisitos

Tu respuesta (SOLO el intent):"""

        try:
            response = requests.post(
                self.llm_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # Muy baja para respuestas directas sin explicaciones
                    "max_tokens": 10  # Solo necesitamos el nombre del intent (1-2 tokens)
                },
                timeout=5
            )
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                
                # Limpiar respuesta: tomar solo la primera línea, quitar puntos, minúsculas
                intent = content.split('\n')[0].lower()
                intent = intent.replace('.', '').replace(',', '').replace(':', '').strip()
                
                # Extraer intent si está en formato "→ intent" o "- intent"
                if '→' in intent:
                    intent = intent.split('→')[-1].strip()
                elif '-' in intent and not intent.startswith('-'):
                    intent = intent.split('-')[0].strip()
                
                # Quitar palabras comunes al inicio
                for prefix in ['respuesta', 'intent', 'el intent es', 'clasificación']:
                    if intent.startswith(prefix):
                        intent = intent[len(prefix):].strip()
                
                logger.info(f"✅ LLM respondió: '{intent}' (raw: '{content[:100]}...')")
                
                # Validar que el intent sea válido
                if intent in self.PATRONES_INTENT:
                    logger.info(f"🎯 LLM clasificó como: {intent} (confianza: 0.85)")
                    return intent, 0.85
                else:
                    logger.warning(f"⚠️ LLM devolvió intent inválido: '{intent}'")
        
        except Exception as e:
            logger.error(f"❌ Error en LLM: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        return 'nlu_fallback', 0.0

# =====================================================
# EXTRACTOR DE ENTIDADES
# =====================================================

def extraer_entidades(mensaje: str, intent: str) -> Dict:
    """Extrae entidades del mensaje según el intent"""
    entidades = {}
    mensaje_lower = mensaje.lower()
    
    # Palabras comunes que NO son nombres
    palabras_prohibidas = {
        'yo', 'tu', 'el', 'ella', 'nosotros', 'ustedes', 'ellos',
        'no', 'nada', 'algo', 'todo', 'nadie', 'alguien',
        'se', 'me', 'te', 'le', 'nos', 'les', 'lo', 'la', 'los', 'las',
        'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'muy', 'mucho', 'poco', 'mas', 'menos', 'bien', 'mal',
        'loco', 'loca', 'tonto', 'tonta', 'raro', 'rara',
        'cosa', 'cosas', 'malo', 'mala',
        'macaco', 'mono', 'gorila', 'gorilla', 'animal', 'volador', 'voladora',
        'idiota', 'estupido', 'estúpido', 'bobo', 'boba', 'insano', 'insana',
        'payaso', 'ridiculo', 'ridículo', 'absurdo', 'absurda',
        'gaga', 'total', 'pepe', 'test', 'prueba', 'fake', 'falso'
    }
    
    # Extraer NOMBRE - MEJORADO con validación de palabras prohibidas
    if intent == 'informar_nombre' or 'me llamo' in mensaje_lower or 'mi nombre es' in mensaje_lower:
        # 1. Buscar con "me llamo" o "mi nombre es"
        match = re.search(r'(me\s+llamo|mi\s+nombre\s+es|soy)\s+(.+)', mensaje, re.IGNORECASE)
        if match:
            nombre = match.group(2).strip()
            # Limpiar el nombre (quitar puntos, comas al final)
            nombre = re.sub(r'[.,!?]$', '', nombre).strip()
            
            # Verificar que no contenga palabras prohibidas
            palabras_nombre = [p.lower() for p in nombre.split()]
            if not any(p in palabras_prohibidas for p in palabras_nombre):
                entidades['nombre'] = nombre.title()
        else:
            # 2. Si el intent es informar_nombre, tomar TODO el mensaje como nombre
            # (asumiendo que solo escribieron su nombre)
            nombre = mensaje.strip()
            palabras_nombre = [p.lower() for p in nombre.split()]
            
            # Verificar que no contenga palabras prohibidas
            if not any(p in palabras_prohibidas for p in palabras_nombre):
                if len(nombre.split()) >= 2:  # Al menos 2 palabras (nombre y apellido)
                    entidades['nombre'] = nombre.title()
                # Si solo tiene 1 palabra, NO la aceptamos (la validación en informar_nombre la rechazará)
    
    # Extraer CÉDULA (con o sin puntos)
    # 1. Primero buscar "mi cedula es NUMERO" o "cedula: NUMERO"
    cedula_match = re.search(r'(?:mi\s+)?c[eé]dula\s+(?:es|:)?\s*(\d{3,8})', mensaje_lower)
    if cedula_match:
        entidades['cedula'] = cedula_match.group(1)
    else:
        # 2. Intentar con puntos: XX.XXX.XXX
        cedula_match = re.search(r'\b(\d{1,2}\.\d{3}\.\d{3})\b', mensaje)
        if cedula_match:
            # Remover los puntos para almacenar solo números
            entidades['cedula'] = cedula_match.group(1).replace('.', '')
        else:
            # 3. Si no tiene puntos, buscar 5-8 dígitos aislados
            cedula_match = re.search(r'\b(\d{5,8})\b', mensaje)
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
    elif any(frase in mensaje_lower for frase in ['proxima semana', 'próxima semana', 'siguiente semana', 'semana que viene']):
        # Para "próxima semana", sugerir lunes de la próxima semana
        hoy = datetime.now()
        dias_hasta_lunes = (7 - hoy.weekday()) % 7
        if dias_hasta_lunes == 0:  # Si hoy es lunes
            dias_hasta_lunes = 7
        fecha_proxima_semana = hoy + timedelta(days=dias_hasta_lunes)
        entidades['fecha'] = fecha_proxima_semana.strftime('%Y-%m-%d')
    else:
        # Reconocer días de la semana (lunes, martes, etc.)
        dias_semana = {
            'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
            'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
        }
        
        for dia_nombre, dia_num in dias_semana.items():
            if dia_nombre in mensaje_lower:
                # Encontrar el día de la semana
                hoy = datetime.now()
                dia_actual = hoy.weekday()
                dias_hasta = (dia_num - dia_actual) % 7
                
                # Si es hoy (dias_hasta == 0), usar hoy
                # Si el día ya pasó (dias_hasta < 0), ir a la próxima semana
                # Si el día está adelante (dias_hasta > 0), usar esta semana
                if dias_hasta == 0:
                    # Es hoy, usar hoy
                    fecha_dia = hoy
                elif dias_hasta < 0 or (dias_hasta == 0 and hoy.hour >= 17):
                    # Ya pasó o es muy tarde, ir a la próxima semana
                    dias_hasta = 7 + dias_hasta
                    fecha_dia = hoy + timedelta(days=dias_hasta)
                else:
                    # Está adelante esta semana
                    fecha_dia = hoy + timedelta(days=dias_hasta)
                
                entidades['fecha'] = fecha_dia.strftime('%Y-%m-%d')
                break
        
        # Si no encontró día de semana, buscar formato DD/MM o DD-MM
        if 'fecha' not in entidades:
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
        # Buscar "X y media", "X y cuarto"
        hora_match = re.search(r'(?:para\s+)?(?:a\s+)?las\s+(\d{1,2})\s+y\s+(media|cuarto)', mensaje_lower)
        if hora_match:
            hora = int(hora_match.group(1))
            fraccion = hora_match.group(2)
            # Asumir AM/PM basado en el número
            if hora < 7:  # Si es menor a 7, probablemente sea PM (tarde)
                hora += 12
            # Agregar minutos
            minutos = "30" if fraccion == "media" else "15"
            entidades['hora'] = f"{hora:02d}:{minutos}"
        else:
            # Buscar formato "a las X", "las X", "para las X" o "X hs"
            hora_match = re.search(r'(?:para\s+)?(?:a\s+)?las\s+(\d{1,2})', mensaje_lower)
            if hora_match:
                hora = int(hora_match.group(1))
                # Asumir AM/PM basado en el número
                if hora < 7:  # Si es menor a 7, probablemente sea PM (tarde)
                    hora += 12
                entidades['hora'] = f"{hora:02d}:00"
            else:
                # Buscar formato "X hs", "X am", "X pm"
                hora_match = re.search(r'\b(\d{1,2})\s*(am|pm|hs|horas?)\b', mensaje_lower)
                if hora_match:
                    hora = int(hora_match.group(1))
                    sufijo = hora_match.group(2)
                    if sufijo == 'pm' and hora < 12:
                        hora += 12
                    entidades['hora'] = f"{hora:02d}:00"
    
    # Extraer FRANJA HORARIA (mañana/tarde)
    if any(palabra in mensaje_lower for palabra in ['mañana', 'manana', 'temprano', 'por la mañana', 'de mañana', 'a la mañana']):
        entidades['franja_horaria'] = 'manana'
    elif any(palabra in mensaje_lower for palabra in ['tarde', 'por la tarde', 'de tarde', 'a la tarde', 'despues del mediodia', 'después del mediodía']):
        entidades['franja_horaria'] = 'tarde'
    
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
    """
    Obtiene disponibilidad real de la base de datos.
    Retorna dict con ocupación por hora: {'08:00': 2, '09:00': 5, ...}
    Si una hora no aparece, significa que está disponible (0 turnos)
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        if not fecha:
            fecha = datetime.now().strftime('%Y-%m-%d')
        
        # Contar turnos por hora
        cursor.execute("""
            SELECT 
                TO_CHAR(fecha_hora, 'HH24:MI') as hora,
                COUNT(*) as ocupados
            FROM turnos
            WHERE DATE(fecha_hora) = %s
            AND estado = 'activo'
            GROUP BY TO_CHAR(fecha_hora, 'HH24:MI')
            ORDER BY hora
        """, (fecha,))
        
        resultados = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Crear estructura completa de horarios (7:00 AM a 3:00 PM = 15:00)
        # 2 turnos cada media hora: 7:00, 7:30, 8:00, 8:30 ... 14:30, 15:00
        horarios_completos = {}
        for hora in range(7, 16):  # 7:00 a 15:00
            for minuto in [0, 30]:
                if hora == 15 and minuto == 30:  # No incluir 15:30
                    break
                hora_str = f"{hora:02d}:{minuto:02d}"
                horarios_completos[hora_str] = 0  # Por defecto, disponible
        
        # Actualizar con ocupación real
        for hora_str, ocupados in resultados:
            if hora_str in horarios_completos:
                horarios_completos[hora_str] = ocupados
        
        # Contar cuántos horarios tienen disponibilidad (máximo 2 personas por turno)
        horarios_disponibles = sum(1 for ocupacion in horarios_completos.values() if ocupacion < 2)
        
        logger.info(f"📊 {fecha}: {horarios_disponibles}/{len(horarios_completos)} horarios disponibles")
        return horarios_completos
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo disponibilidad: {e}")
        # Si hay error, asumir que hay disponibilidad
        horarios_default = {}
        for hora in range(7, 16):  # 7:00 a 15:00
            for minuto in [0, 30]:
                if hora == 15 and minuto == 30:  # No incluir 15:30
                    break
                horarios_default[f"{hora:02d}:{minuto:02d}"] = 0
        return horarios_default

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
        
        # 3.5. VALIDAR FECHA: No permitir fin de semana
        if entidades.get('fecha'):
            fecha_obj = datetime.strptime(entidades['fecha'], '%Y-%m-%d')
            if fecha_obj.weekday() >= 5:  # Sábado (5) o Domingo (6)
                dia_nombre = 'sábado' if fecha_obj.weekday() == 5 else 'domingo'
                # Buscar el próximo lunes
                dias_hasta_lunes = (7 - fecha_obj.weekday()) % 7
                if dias_hasta_lunes == 0:
                    dias_hasta_lunes = 1
                proximo_lunes = fecha_obj + timedelta(days=dias_hasta_lunes)
                
                # Limpiar la fecha del contexto (no es válida)
                contexto.fecha = None
                
                return {
                    'text': f"😔 Lo siento, no atendemos los {dia_nombre}s. Nuestro horario es de lunes a viernes, 07:00 a 17:00. ¿Prefieres agendar para el lunes {proximo_lunes.strftime('%d/%m')}?",
                    'intent': intent,
                    'confidence': confidence,
                    'entidades': entidades,
                    'contexto': contexto.to_dict()
                }
        
        # 4. Generar respuesta según intent
        respuesta = generar_respuesta_inteligente(intent, confidence, contexto, user_message)
        
        # Si la respuesta es un diccionario (ej: modo_desarrollador con botón), 
        # combinar con los datos base
        if isinstance(respuesta, dict):
            resultado = {
                'text': respuesta.get('text', ''),
                'intent': intent,
                'confidence': confidence,
                'entidades': entidades,
                'contexto': contexto.to_dict()
            }
            # Agregar campos adicionales del diccionario (como show_dashboard_button)
            for key, value in respuesta.items():
                if key not in resultado:
                    resultado[key] = value
            return resultado
        else:
            # Respuesta simple (string)
            return {
                'text': respuesta,  # ← app.py espera 'text'
                'intent': intent,
                'confidence': confidence,
                'entidades': entidades,
                'contexto': contexto.to_dict()
            }
        
    except Exception as e:
        logger.error(f"❌ Error en procesar_mensaje_inteligente: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'text': (
                "Disculpa, tuve un problema procesando tu mensaje. "
                "¿Podrías reformularlo? Por ejemplo: 'Quiero un turno para mañana'"
            ),
            'intent': 'error',
            'confidence': 0.0,
            'error': str(e)
        }

def generar_respuesta_inteligente(intent: str, confidence: float, 
                                  contexto: SessionContext, mensaje: str) -> str:
    """Genera respuesta apropiada según el intent"""
    
    # Intent: DESCONOCIDO - Cuando detectamos que el mensaje no es válido
    if intent == 'desconocido' or confidence < 0.3:
        # Si estábamos esperando un nombre específicamente
        if not contexto.nombre:
            return (
                "Disculpa, no entendí bien. Por favor, indícame tu nombre completo "
                "(nombre y apellido). Por ejemplo: Juan Pérez"
            )
        # Si estábamos esperando cédula
        elif contexto.nombre and not contexto.cedula:
            return "Por favor, indícame tu número de cédula (entre 5 y 8 dígitos)."
        # Si estábamos esperando fecha
        elif contexto.nombre and contexto.cedula and not contexto.fecha:
            return "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
        # Si estábamos esperando hora
        elif contexto.fecha and not contexto.hora:
            return "¿A qué hora prefieres tu turno? Por ejemplo: '9 de la mañana' o '14:00'"
        # En cualquier otro caso
        else:
            return (
                "No estoy seguro de entender. ¿Podrías reformular? "
                "Puedo ayudarte con:\n"
                "- Agendar turnos\n"
                "- Consultar horarios\n"
                "- Información sobre requisitos"
            )
    
    # Intent: INFORMAR TIPO DE TRÁMITE - Usuario indica tipo específico con requisitos
    if intent == 'informar_tipo_tramite':
        contexto.cedula = "SIN_CEDULA"  # No tiene cédula todavía
        
        if contexto.tipo_tramite == 'primera_vez':
            return (
                "📋 **Primera cédula - Requisitos:**\n\n"
                "✅ **Documentos necesarios:**\n"
                "• Acta de nacimiento original (emitida por Registro Civil)\n"
                "• Si eres menor de edad: presencia de padre/madre o tutor\n"
                "• Certificado de estudios (solo si eres estudiante)\n\n"
                "💰 **Costo:** GRATUITO ✅\n\n"
                "⏰ **Tiempo de espera:** 5-10 días hábiles\n\n"
                "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
            )
        
        elif contexto.tipo_tramite == 'perdida':
            return (
                "📋 **Pérdida/Robo de cédula - Requisitos:**\n\n"
                "✅ **Documentos necesarios:**\n"
                "• Denuncia policial (si fue robo/extravío)\n"
                "• Acta de nacimiento original\n"
                "• Certificado de denuncia del Registro Civil\n\n"
                "💰 **Costo:** Gs. 50.000\n\n"
                "⏰ **Tiempo de espera:** 10-15 días hábiles\n\n"
                "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
            )
        
        elif contexto.tipo_tramite == 'extranjero':
            return (
                "📋 **Cédula para extranjeros - Requisitos:**\n\n"
                "✅ **Documentos necesarios:**\n"
                "• Pasaporte vigente\n"
                "• Certificado de residencia permanente o radicación\n"
                "• Acta de nacimiento apostillada del país de origen\n"
                "• Comprobante de domicilio en Paraguay\n\n"
                "💰 **Costo:** Gs. 100.000\n\n"
                "⏰ **Tiempo de espera:** 15-20 días hábiles\n\n"
                "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
            )
        
        else:
            # Fallback si no detectamos el tipo
            contexto.cedula = "SIN_CEDULA"
            return "Entendido. ¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
    
    # Intent: NEGACIÓN SIN CÉDULA
    if intent == 'negacion_sin_cedula':
        # Registrar que no tiene cédula (usar un valor especial)
        contexto.cedula = "SIN_CEDULA"
        return "Entendido, sin problema. Continuamos con el agendamiento. ¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
    
    # Intent: INFORMAR NOMBRE - Guardar nombre y continuar flujo
    if intent == 'informar_nombre':
        if contexto.nombre:
            # Validar que tenga al menos nombre + apellido (2 palabras)
            palabras = contexto.nombre.split()
            if len(palabras) < 2:
                return "Por favor, necesito tu nombre completo (nombre y apellido) para evitar confusiones. Por ejemplo: Juan Pérez"
            
            # Palabras comunes que NO son nombres
            palabras_prohibidas = {
                'yo', 'tu', 'el', 'ella', 'nosotros', 'ustedes', 'ellos',
                'no', 'nada', 'algo', 'todo', 'nadie', 'alguien',
                'se', 'me', 'te', 'le', 'nos', 'les', 'lo', 'la', 'los', 'las',
                'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
                'muy', 'mucho', 'poco', 'mas', 'menos', 'bien', 'mal',
                'loco', 'loca', 'tonto', 'tonta', 'raro', 'rara',
                'cosa', 'cosas', 'malo', 'mala',
                'macaco', 'mono', 'gorila', 'gorilla', 'animal', 'volador', 'voladora',
                'idiota', 'estupido', 'estúpido', 'bobo', 'boba', 'insano', 'insana',
                'payaso', 'ridiculo', 'ridículo', 'absurdo', 'absurda',
                'gaga', 'total', 'pepe', 'test', 'prueba', 'fake', 'falso'
            }
            
            # Verificar que no contenga palabras prohibidas
            palabras_lower = [p.lower() for p in palabras]
            if any(p in palabras_prohibidas for p in palabras_lower):
                contexto.nombre = None  # Limpiar el nombre inválido
                return "Disculpa, parece que eso no es un nombre. Por favor, indícame tu nombre y apellido completo. Por ejemplo: Juan Pérez"
            
            # Ya tenemos el nombre completo, preguntar cédula
            return f"Perfecto, {contexto.nombre}. ¿Cuál es tu número de cédula?"
        else:
            # Algo salió mal, volver a preguntar
            return "¿Cuál es tu nombre completo? (nombre y apellido)"
    
    # Intent: INFORMAR CÉDULA - Guardar cédula y continuar flujo
    if intent == 'informar_cedula':
        if contexto.cedula:
            # Ya tenemos la cédula, preguntar fecha
            return "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
        else:
            # Algo salió mal
            return "¿Cuál es tu número de cédula?"
    
    # Intent: AGENDAR TURNO
    if intent == 'agendar_turno':
        if not contexto.nombre:
            return "¡Perfecto! Para agendar tu turno, necesito algunos datos. ¿Cuál es tu nombre completo?"
        elif not contexto.cedula:
            return f"Gracias {contexto.nombre}. ¿Cuál es tu número de cédula?"
        elif not contexto.fecha:
            return "¿Para qué día necesitas el turno? Puedes decir 'mañana' o una fecha específica."
        elif not contexto.hora:
            # Mostrar horarios disponibles sin motor difuso (simplificado)
            return "¿A qué hora prefieres? Por ejemplo: 09:00, 14:30, etc."
        elif not contexto.email:
            # Pedir email antes de confirmar
            return "Perfecto! Para enviarte la confirmación y el código QR, ¿cuál es tu email?"
        else:
            # Todos los datos completos - mostrar resumen y pedir confirmación
            resumen = f"📋 Perfecto! Resumen de tu turno:\n"
            resumen += f"Nombre: {contexto.nombre}\n"
            
            # Solo mostrar cédula si tiene una válida
            if contexto.cedula and contexto.cedula != "SIN_CEDULA":
                resumen += f"Cédula: {contexto.cedula}\n"
            else:
                resumen += f"Cédula: Sin cédula (trámite nuevo)\n"
            
            resumen += f"Fecha: {contexto.fecha}\n"
            resumen += f"Hora: {contexto.hora}\n"
            resumen += f"Email: {contexto.email}\n\n"
            resumen += f"¿Confirmas estos datos? (Responde 'sí' para confirmar)"
            
            return resumen
    
    # Intent: ELEGIR HORARIO
    elif intent == 'elegir_horario':
        if not contexto.nombre:
            return "Primero necesito que me digas tu nombre completo."
        elif not contexto.cedula:
            return f"Gracias {contexto.nombre}. ¿Cuál es tu número de cédula?"
        elif not contexto.fecha:
            return "¿Para qué día necesitas el turno?"
        elif not contexto.email:
            # Pedir email antes de confirmar
            return "Perfecto! Para enviarte la confirmación y el código QR, ¿cuál es tu email?"
        elif contexto.hora:
            # Ya tenemos todo incluyendo email, confirmar datos
            resumen = f"📋 Perfecto! Resumen de tu turno:\n"
            resumen += f"Nombre: {contexto.nombre}\n"
            
            if contexto.cedula and contexto.cedula != "SIN_CEDULA":
                resumen += f"Cédula: {contexto.cedula}\n"
            else:
                resumen += f"Cédula: Sin cédula (trámite nuevo)\n"
            
            resumen += f"Fecha: {contexto.fecha}\n"
            resumen += f"Hora: {contexto.hora}\n"
            resumen += f"Email: {contexto.email}\n\n"
            resumen += f"¿Confirmas estos datos? (Responde 'sí' para confirmar)"
            
            return resumen
        else:
            # Si no tenemos hora pero tenemos hora_recomendada, usar esa
            if contexto.hora_recomendada:
                contexto.hora = contexto.hora_recomendada
                
                # Verificar si tenemos email
                if not contexto.email:
                    return "Perfecto! Para enviarte la confirmación y el código QR, ¿cuál es tu email?"
                
                # Confirmar datos con email
                resumen = f"📋 Perfecto! Resumen de tu turno:\n"
                resumen += f"Nombre: {contexto.nombre}\n"
                
                if contexto.cedula and contexto.cedula != "SIN_CEDULA":
                    resumen += f"Cédula: {contexto.cedula}\n"
                else:
                    resumen += f"Cédula: Sin cédula (trámite nuevo)\n"
                
                resumen += f"Fecha: {contexto.fecha}\n"
                resumen += f"Hora: {contexto.hora}\n"
                resumen += f"Email: {contexto.email}\n\n"
                resumen += f"¿Confirmas estos datos? (Responde 'sí' para confirmar)"
                
                return resumen
            else:
                # Algo salió mal
                return "¿A qué hora prefieres el turno? Por ejemplo: 09:00, 14:30, etc."
    
    # Intent: CONSULTAR DISPONIBILIDAD
    elif intent == 'consultar_disponibilidad':
        mensaje_lower = mensaje.lower()
        
        # IMPORTANTE: Si el usuario tiene nombre y cédula, PERMITIR consultar disponibilidad
        # (ya está en el flujo de agendamiento, solo falta fecha/hora)
        # SOLO pedir datos si NO tiene NADA (consulta desde cero)
        
        # Si NO tiene nombre NI cédula, es una consulta desde cero
        if not contexto.nombre and not contexto.cedula:
            return (
                "Me encantaría mostrarte los horarios disponibles, pero primero necesito "
                "algunos datos para agendar tu turno.\n\n"
                "¿Cuál es tu nombre completo?"
            )
        
        # Si SOLO tiene nombre pero NO cédula, pedir cédula
        elif contexto.nombre and not contexto.cedula:
            return (
                f"Perfecto {contexto.nombre}, para mostrarte la disponibilidad necesito "
                "completar tus datos.\n\n"
                "¿Cuál es tu número de cédula?"
            )
        
        # Ya tenemos nombre y cédula, podemos mostrar disponibilidad
        
        # ==========================================
        # DETECTAR CONSULTAS ESPECIALES
        # ==========================================
        
        # Detectar consulta por "hoy"
        consulta_hoy = any(palabra in mensaje_lower for palabra in ['hoy', 'para hoy', 'de hoy'])
        
        # Detectar consulta por franja horaria (mañana/tarde)
        consulta_manana = any(palabra in mensaje_lower for palabra in ['mañana', 'manana', 'temprano', 'por la mañana', 'por la manana'])
        consulta_tarde = any(palabra in mensaje_lower for palabra in ['tarde', 'por la tarde', 'despues del mediodia', 'después del mediodía'])
        
        # Detectar "día más libre" o "día intermedio"
        consulta_mejor_dia = any(frase in mensaje_lower for frase in [
            'día libre', 'dia libre', 'día disponible', 'dia disponible',
            'día intermedio', 'dia intermedio', 'mejor día', 'mejor dia',
            'qué día', 'que dia', 'cual dia', 'cuál día'
        ])
        
        # ==========================================
        # MANEJAR CONSULTA DE "HOY"
        # ==========================================
        if consulta_hoy:
            hoy = datetime.now().strftime('%Y-%m-%d')
            hora_actual = datetime.now().hour
            
            # Verificar si ya cerró la oficina (después de las 15:00)
            if hora_actual >= 15:
                # Calcular próximo día hábil (mañana si no es viernes)
                manana = datetime.now() + timedelta(days=1)
                # Saltar fines de semana
                while manana.weekday() >= 5:  # 5=sábado, 6=domingo
                    manana += timedelta(days=1)
                
                manana_str = manana.strftime('%Y-%m-%d')
                dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'][manana.weekday()]
                
                return (
                    f"🕐 **Ya cerramos por hoy** (horario de atención: 07:00 - 15:00).\n\n"
                    f"✅ Puedo ofrecerte turnos para **mañana {dia_nombre} {manana_str}**.\n\n"
                    f"¿Te gustaría ver los horarios disponibles para mañana?"
                )
            
            # Aún está abierto, mostrar disponibilidad
            try:
                disponibilidad = obtener_disponibilidad_real(hoy)
                # Filtrar solo horarios futuros (después de la hora actual)
                horarios_disponibles = {h: o for h, o in disponibilidad.items() 
                                       if o < 2 and int(h.split(':')[0]) > hora_actual}
                
                # Filtrar por franja horaria si se especificó
                if consulta_tarde:
                    # Horarios de tarde: 12:00+
                    horarios_disponibles = {h: o for h, o in horarios_disponibles.items() 
                                          if int(h.split(':')[0]) >= 12}
                elif consulta_manana:
                    # Horarios de mañana: <12:00
                    horarios_disponibles = {h: o for h, o in horarios_disponibles.items() 
                                          if int(h.split(':')[0]) < 12}
                
                if horarios_disponibles:
                    franja_str = ""
                    if consulta_tarde:
                        franja_str = " de tarde"
                    elif consulta_manana:
                        franja_str = " de mañana"
                    
                    lista_horarios = ', '.join(sorted(horarios_disponibles.keys()))
                    return (
                        f"✅ **Disponibilidad{franja_str} para HOY ({hoy}):**\n\n"
                        f"Tenemos {len(horarios_disponibles)} horarios disponibles:\n"
                        f"📋 {lista_horarios}\n\n"
                        f"¿A qué hora prefieres tu turno?"
                    )
                elif consulta_tarde:
                    # Consultó tarde pero no hay
                    return (
                        f"😔 Lo siento, para HOY ({hoy}) no hay horarios disponibles **de tarde** (después de las 12:00).\n\n"
                        f"Nuestro horario de atención es de 07:00 a 15:00.\n\n"
                        f"✅ ¿Te gustaría ver los horarios de mañana disponibles?"
                    )
                else:
                    # No hay horarios disponibles para hoy
                    manana = datetime.now() + timedelta(days=1)
                    while manana.weekday() >= 5:
                        manana += timedelta(days=1)
                    manana_str = manana.strftime('%Y-%m-%d')
                    dia_nombre = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'][manana.weekday()]
                    
                    return (
                        f"😔 Lo siento, para HOY ({hoy}) ya no hay horarios disponibles.\n\n"
                        f"✅ ¿Te gustaría ver la disponibilidad para mañana {dia_nombre} ({manana_str})?"
                    )
            except Exception as e:
                logger.error(f"Error consultando disponibilidad de hoy: {e}")
                return "Hubo un error al consultar la disponibilidad. ¿Podrías intentar de nuevo?"
        
        # ==========================================
        # MANEJAR CONSULTA DE "MEJOR DÍA" / "DÍA MÁS LIBRE"
        # ==========================================
        if consulta_mejor_dia:
            hoy = datetime.now()
            mejor_dia = None
            max_disponibilidad = 0
            
            # Revisar próximos 7 días
            for i in range(7):
                fecha_revisar = hoy + timedelta(days=i)
                if fecha_revisar.weekday() < 5:  # Solo días laborables
                    fecha_str = fecha_revisar.strftime('%Y-%m-%d')
                    try:
                        disponibilidad = obtener_disponibilidad_real(fecha_str)
                        horarios_disponibles = len([h for h, o in disponibilidad.items() if o < 2])
                        
                        if horarios_disponibles > max_disponibilidad:
                            max_disponibilidad = horarios_disponibles
                            mejor_dia = fecha_revisar
                    except:
                        continue
            
            if mejor_dia:
                dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                dia_nombre = dias_nombres[mejor_dia.weekday()]
                fecha_str = mejor_dia.strftime('%Y-%m-%d')
                
                # Obtener disponibilidad completa
                disponibilidad = obtener_disponibilidad_real(fecha_str)
                horarios_disponibles = {h: o for h, o in disponibilidad.items() if o < 2}
                lista_horarios = ', '.join(sorted(list(horarios_disponibles.keys())[:5]))  # Primeros 5
                
                # Sugerir horario con menos espera (ocupación más baja)
                mejor_horario = min(horarios_disponibles.items(), key=lambda x: x[1])[0]
                
                # GUARDAR hora recomendada para usar después
                contexto.hora_recomendada = mejor_horario
                
                return (
                    f"✅ **Muy buena disponibilidad para el {fecha_str}** ({dia_nombre}).\n\n"
                    f"🌟 Te recomiendo las **{mejor_horario}** (menor tiempo de espera).\n\n"
                    f"Otros horarios disponibles: {lista_horarios}\n\n"
                    f"¿A qué hora prefieres?"
                )
            else:
                return (
                    "😔 Lo siento, los próximos días tienen disponibilidad limitada.\n\n"
                    "¿Prefieres que revise la disponibilidad de una semana específica?"
                )
        
        # ==========================================
        # DETECTAR CONSULTA POR FRANJA HORARIA ESPECÍFICA
        # ==========================================
        consulta_manana = any(palabra in mensaje_lower for palabra in ['mañana', 'manana', 'temprano', 'madrugada', 'antes del mediodia', 'antes del mediodía'])
        consulta_tarde = any(palabra in mensaje_lower for palabra in ['tarde', 'después del mediodía', 'despues del mediodia', 'mediodia', 'mediodía'])
        
        # Usar franja del contexto si está guardada
        if contexto.franja_horaria:
            if contexto.franja_horaria == 'manana':
                consulta_manana = True
                consulta_tarde = False
            elif contexto.franja_horaria == 'tarde':
                consulta_tarde = True
                consulta_manana = False
        
        # Detectar si tiene fecha específica en el contexto
        fecha_contexto = contexto.fecha
        
        if (consulta_manana or consulta_tarde) and fecha_contexto:
            # Consulta personalizada por franja horaria
            try:
                disponibilidad = obtener_disponibilidad_real(fecha_contexto)
                
                if consulta_manana:
                    # Filtrar horarios de mañana: 7:00 - 11:30
                    horarios_manana = {h: o for h, o in disponibilidad.items() 
                                      if h >= "07:00" and h <= "11:30" and o < 2}
                    
                    if horarios_manana:
                        lista_horarios = ', '.join(sorted(horarios_manana.keys()))
                        respuesta = (
                            f"🌅 **Disponibilidad en la mañana del {fecha_contexto}:**\n\n"
                            f"Tenemos {len(horarios_manana)} horarios disponibles de 7:00 AM a 11:30 AM:\n"
                            f"📋 {lista_horarios}\n\n"
                            f"¿A qué hora prefieres tu turno?"
                        )
                    else:
                        respuesta = (
                            f"😔 Lo siento, no hay horarios disponibles en la mañana del {fecha_contexto}.\n\n"
                            f"¿Te gustaría revisar los horarios de la tarde (12:00 - 15:00) o elegir otro día?"
                        )
                    return respuesta
                
                elif consulta_tarde:
                    # Filtrar horarios de tarde: 12:00 - 15:00
                    horarios_tarde = {h: o for h, o in disponibilidad.items() 
                                     if h >= "12:00" and h <= "15:00" and o < 2}
                    
                    if horarios_tarde:
                        lista_horarios = ', '.join(sorted(horarios_tarde.keys()))
                        respuesta = (
                            f"🌆 **Disponibilidad en la tarde del {fecha_contexto}:**\n\n"
                            f"Tenemos {len(horarios_tarde)} horarios disponibles de 12:00 PM a 3:00 PM:\n"
                            f"📋 {lista_horarios}\n\n"
                            f"¿A qué hora prefieres tu turno?"
                        )
                    else:
                        respuesta = (
                            f"😔 Lo siento, no hay horarios disponibles en la tarde del {fecha_contexto}.\n\n"
                            f"¿Te gustaría revisar los horarios de la mañana (7:00 - 11:30) o elegir otro día?"
                        )
                    return respuesta
                    
            except Exception as e:
                logger.error(f"Error consultando disponibilidad por franja: {e}")
        
        # ==========================================
        # CONSULTAS GENERALES (sin especificar franja)
        # ==========================================
        # Detectar si pregunta por "esta semana" o "próxima semana"
        if any(frase in mensaje_lower for frase in ['esta semana', 'semana actual']):
            # Mostrar disponibilidad del resto de esta semana (desde hoy hasta viernes)
            hoy = datetime.now()
            respuesta = "📅 **Disponibilidad para esta semana:**\n\n"
            
            dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
            
            # Empezar desde hoy hasta viernes
            dia_actual = hoy.weekday()  # 0=lunes, 4=viernes
            if dia_actual >= 5:  # Si es sábado o domingo, mostrar próxima semana
                dias_hasta_lunes = (7 - dia_actual) % 7
                if dias_hasta_lunes == 0:
                    dias_hasta_lunes = 7
                lunes_proxima = hoy + timedelta(days=dias_hasta_lunes)
                
                for i, dia_nombre in enumerate(dias_nombres):
                    fecha_dia = lunes_proxima + timedelta(days=i)
                    fecha_str = fecha_dia.strftime('%Y-%m-%d')
                    disponibilidad = obtener_disponibilidad_real(fecha_str)
                    horarios_disponibles = [h for h, o in disponibilidad.items() if o < 2]
                    
                    if horarios_disponibles:
                        respuesta += f"✅ **{dia_nombre} {fecha_dia.strftime('%d/%m')}**: {len(horarios_disponibles)} horarios disponibles\n"
                    else:
                        respuesta += f"❌ **{dia_nombre} {fecha_dia.strftime('%d/%m')}**: Sin disponibilidad\n"
            else:
                # Mostrar desde hoy hasta viernes
                dias_hasta_viernes = 4 - dia_actual  # 4 = viernes
                for i in range(dias_hasta_viernes + 1):
                    fecha_dia = hoy + timedelta(days=i)
                    dia_nombre = dias_nombres[fecha_dia.weekday()]
                    fecha_str = fecha_dia.strftime('%Y-%m-%d')
                    disponibilidad = obtener_disponibilidad_real(fecha_str)
                    horarios_disponibles = [h for h, o in disponibilidad.items() if o < 2]
                    
                    prefijo = "🔵" if i == 0 else "✅"  # Marcar hoy con diferente emoji
                    if horarios_disponibles:
                        respuesta += f"{prefijo} **{dia_nombre} {fecha_dia.strftime('%d/%m')}**: {len(horarios_disponibles)} horarios disponibles\n"
                    else:
                        respuesta += f"❌ **{dia_nombre} {fecha_dia.strftime('%d/%m')}**: Sin disponibilidad\n"
            
            respuesta += "\n¿Para qué día prefieres agendar?"
            return respuesta
        
        # Detectar si pregunta por "próxima semana"
        elif any(frase in mensaje_lower for frase in ['proxima semana', 'próxima semana', 'siguiente semana', 'semana que viene']):
            # Mostrar disponibilidad de varios días de la próxima semana
            hoy = datetime.now()
            dias_hasta_lunes = (7 - hoy.weekday()) % 7
            if dias_hasta_lunes == 0:
                dias_hasta_lunes = 7
            
            lunes_proxima = hoy + timedelta(days=dias_hasta_lunes)
            respuesta = "📅 **Disponibilidad para la próxima semana:**\n\n"
            
            # Mostrar lunes a viernes
            dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
            for i, dia_nombre in enumerate(dias_nombres):
                fecha_dia = lunes_proxima + timedelta(days=i)
                fecha_str = fecha_dia.strftime('%Y-%m-%d')
                disponibilidad = obtener_disponibilidad_real(fecha_str)
                
                horarios_disponibles = [h for h, o in disponibilidad.items() if o < 2]
                
                if horarios_disponibles:
                    respuesta += f"✅ **{dia_nombre} {fecha_dia.strftime('%d/%m')}**: {len(horarios_disponibles)} horarios disponibles\n"
                else:
                    respuesta += f"❌ **{dia_nombre} {fecha_dia.strftime('%d/%m')}**: Sin disponibilidad\n"
            
            respuesta += "\n¿Para qué día prefieres agendar?"
            return respuesta
        
        # Determinar qué fecha consultar
        if not contexto.fecha:
            # Si es después de las 17:00, recomendar mañana
            ahora = datetime.now()
            if ahora.hour >= 17:
                fecha_obj = ahora + timedelta(days=1)
            else:
                fecha_obj = ahora
            
            # Saltar fin de semana (sábado=5, domingo=6)
            while fecha_obj.weekday() >= 5:
                fecha_obj += timedelta(days=1)
            
            fecha = fecha_obj.strftime('%Y-%m-%d')
        else:
            fecha = contexto.fecha
        
        # Validar que no sea fin de semana
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        if fecha_obj.weekday() >= 5:  # Sábado o domingo
            return "😔 Lo siento, no atendemos los fines de semana. Nuestro horario es de lunes a viernes, 07:00 a 17:00. ¿Prefieres agendar para el lunes?"
        
        # Obtener disponibilidad real de la BD
        disponibilidad = obtener_disponibilidad_real(fecha)
        
        # Contar horarios disponibles (menos de 5 turnos = disponible)
        horarios_disponibles = []
        horarios_ocupados = []
        
        for hora, ocupacion in disponibilidad.items():
            if ocupacion < 2:  # Disponible (2 turnos por horario)
                horarios_disponibles.append((hora, ocupacion))
            else:  # Ocupado
                horarios_ocupados.append((hora, ocupacion))
        
        # Generar respuesta inteligente
        if not horarios_disponibles:
            return f"😔 Lo siento, para el {fecha} ya no hay horarios disponibles. ¿Te gustaría revisar otro día?"
        
        # Si el motor difuso está disponible, usar análisis avanzado
        if MOTOR_DIFUSO_OK:
            try:
                # Convertir string fecha a datetime.date (datetime ya importado arriba)
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                analisis = analizar_disponibilidad_dia(fecha_obj)
                
                # Obtener mejor hora de las franjas
                mejor_franja = max(analisis.items(), key=lambda x: x[1]['recomendacion'])
                mejor_hora = mejor_franja[1]['horarios_sugeridos'][0] if mejor_franja[1]['horarios_sugeridos'] else horarios_disponibles[0][0]
                contexto.hora_recomendada = mejor_hora  # Guardar para usar después
                
                # Construir respuesta con recomendación
                if len(horarios_disponibles) >= 8:
                    nivel = "✅ Muy buena disponibilidad"
                elif len(horarios_disponibles) >= 5:
                    nivel = "� Buena disponibilidad"
                else:
                    nivel = "⚠️ Disponibilidad limitada"
                
                respuesta = f"{nivel} para el {fecha}.\n\n"
                respuesta += f"🌟 Te recomiendo las {mejor_hora} (menor tiempo de espera).\n\n"
                respuesta += f"Otros horarios disponibles: {', '.join([h for h, _ in horarios_disponibles[:5]])}\n\n"
                respuesta += "¿A qué hora prefieres?"
                
                return respuesta
            except Exception as e:
                logger.warning(f"⚠️ Error en motor difuso: {e}")
        
        # Fallback: respuesta simple sin motor difuso
        if len(horarios_disponibles) > 6:
            return f"✅ Para el {fecha} hay muy buena disponibilidad. Horarios: {', '.join([h for h, _ in horarios_disponibles[:6]])}. ¿A qué hora prefieres?"
        elif len(horarios_disponibles) > 3:
            return f"👍 Para el {fecha} hay disponibilidad en: {', '.join([h for h, _ in horarios_disponibles])}. ¿Cuál te conviene?"
        else:
            return f"⚠️ Para el {fecha} quedan pocos horarios: {', '.join([h for h, _ in horarios_disponibles])}. ¿Te sirve alguno?"
    
    # Intent: FRASE AMBIGUA (temprano, lo antes posible, etc.)
    elif intent == 'frase_ambigua':
        # Verificar que tengamos nombre y cédula
        if not contexto.nombre:
            return "Primero necesito que me digas tu nombre completo para agendar el turno."
        if not contexto.cedula:
            return f"Gracias {contexto.nombre}. ¿Cuál es tu número de cédula?"
        
        # Si no tenemos fecha, usar el siguiente día hábil
        if not contexto.fecha:
            ahora = datetime.now()
            if ahora.hour >= 17:
                fecha_obj = ahora + timedelta(days=1)
            else:
                fecha_obj = ahora
            
            # Saltar fin de semana
            while fecha_obj.weekday() >= 5:
                fecha_obj += timedelta(days=1)
            
            contexto.fecha = fecha_obj.strftime('%Y-%m-%d')
        
        # Obtener disponibilidad y auto-asignar mejor hora
        disponibilidad = obtener_disponibilidad_real(contexto.fecha)
        
        if MOTOR_DIFUSO_OK:
            try:
                # Buscar el horario más temprano disponible
                horarios_disponibles = []
                for hora, ocupacion in disponibilidad.items():
                    if ocupacion < 2:  # Disponible (2 turnos por horario)
                        horarios_disponibles.append(hora)
                
                if horarios_disponibles:
                    mejor_hora = min(horarios_disponibles)  # El más temprano
                    contexto.hora = mejor_hora
                    
                    # Generar resumen
                    resumen = f"✅ Perfecto, te asigno el horario más próximo:\n\n"
                    resumen += f"📋 Resumen de tu turno:\n"
                    resumen += f"Nombre: {contexto.nombre}\n"
                    
                    if contexto.cedula and contexto.cedula != "SIN_CEDULA":
                        resumen += f"Cédula: {contexto.cedula}\n"
                    else:
                        resumen += f"Cédula: Sin cédula (trámite nuevo)\n"
                    
                    resumen += f"Fecha: {contexto.fecha}\n"
                    resumen += f"Hora: {mejor_hora}\n\n"
                    resumen += f"¿Confirmas estos datos? (Responde 'sí' para confirmar)"
                    
                    return resumen
            except:
                pass
        
        # Fallback: 08:00
        contexto.hora = "08:00"
        return "Te asigno el horario de las 08:00. ¿Te parece bien?"
    
    # Intent: TIEMPO DE ESPERA
    elif intent == 'consulta_tiempo_espera':
        respuesta_base = ""
        
        if MOTOR_DIFUSO_OK:
            try:
                # Obtener datos reales de ocupación
                disponibilidad = obtener_disponibilidad_real()
                hora_actual = datetime.now().hour
                ocupacion = disponibilidad.get(f"{hora_actual:02d}:00", 3) * 20  # Estimar %
                
                tiempo = calcular_espera(ocupacion, urgencia=5)
                respuesta_base = f"⏱️ El tiempo de espera estimado ahora es de aproximadamente {int(tiempo)} minutos.\n\n"
            except:
                respuesta_base = "⏱️ El tiempo de espera promedio es de 15-30 minutos, dependiendo de la hora.\n\n"
        else:
            respuesta_base = "⏱️ El tiempo de espera promedio es de 15-30 minutos, dependiendo de la hora.\n\n"
        
        # VERIFICAR SI ESTAMOS EN MEDIO DE UN FORMULARIO
        if not contexto.nombre:
            return respuesta_base + "Ahora, ¿cuál es tu nombre completo para continuar con tu turno?"
        elif not contexto.cedula:
            return respuesta_base + f"Perfecto {contexto.nombre}. ¿Cuál es tu número de cédula para continuar?"
        elif not contexto.fecha:
            return respuesta_base + "¿Para qué día necesitas el turno?"
        elif not contexto.hora:
            return respuesta_base + "¿A qué hora prefieres tu turno?"
        else:
            return respuesta_base.strip()
    
    # Intent: INFORMAR DATOS
    elif intent in ['informar_nombre', 'informar_cedula', 'informar_fecha', 'informar_email', 'elegir_horario']:
        # Ya se actualizó el contexto, preguntar siguiente dato
        if not contexto.nombre:
            return "¿Cuál es tu nombre completo?"
        elif not contexto.cedula:
            return f"Gracias {contexto.nombre}. ¿Cuál es tu número de cédula?"
        elif not contexto.fecha:
            return "¿Para qué día necesitas el turno?"
        elif not contexto.hora:
            # Si acabamos de recibir una fecha, mostrar disponibilidad
            if intent == 'informar_fecha' and contexto.fecha:
                # Reutilizar lógica de consultar_disponibilidad
                fecha = contexto.fecha
                
                # Validar que no sea fin de semana
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
                if fecha_obj.weekday() >= 5:  # Sábado o domingo
                    return "😔 Lo siento, no atendemos los fines de semana. Nuestro horario es de lunes a viernes, 07:00 a 15:00. ¿Prefieres agendar para el lunes?"
                
                # Obtener disponibilidad
                disponibilidad = obtener_disponibilidad_real(fecha)
                horarios_disponibles = [(h, o) for h, o in disponibilidad.items() if o < 2]
                
                if not horarios_disponibles:
                    return f"😔 Lo siento, para el {fecha} ya no hay horarios disponibles. ¿Te gustaría revisar otro día?"
                
                # Analizar con motor difuso
                if MOTOR_DIFUSO_OK:
                    try:
                        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
                        analisis = analizar_disponibilidad_dia(fecha_obj)
                        mejor_franja = max(analisis.items(), key=lambda x: x[1]['recomendacion'])
                        mejor_hora = mejor_franja[1]['horarios_sugeridos'][0] if mejor_franja[1]['horarios_sugeridos'] else horarios_disponibles[0][0]
                        contexto.hora_recomendada = mejor_hora
                        
                        return f"✅ Para el {fecha}:\n\n🌟 Te recomiendo las {mejor_hora} (menor tiempo de espera).\n\nOtros horarios: {', '.join([h for h, _ in horarios_disponibles[:5]])}\n\n¿A qué hora prefieres?"
                    except:
                        pass
                
                # Fallback sin motor difuso
                return f"✅ Para el {fecha} hay disponibilidad en: {', '.join([h for h, _ in horarios_disponibles[:6]])}. ¿Cuál te conviene?"
            else:
                return "¿A qué hora prefieres?"
        elif not contexto.email:
            # Pedir email
            return "Perfecto! Para enviarte la confirmación y el código QR, ¿cuál es tu email?"
        else:
            # Todos los datos completos - mostrar resumen
            resumen = f"📋 Perfecto! Resumen de tu turno:\n"
            resumen += f"Nombre: {contexto.nombre}\n"
            
            if contexto.cedula and contexto.cedula != "SIN_CEDULA":
                resumen += f"Cédula: {contexto.cedula}\n"
            else:
                resumen += f"Cédula: Sin cédula (trámite nuevo)\n"
            
            resumen += f"Fecha: {contexto.fecha}\n"
            resumen += f"Hora: {contexto.hora}\n"
            resumen += f"Email: {contexto.email}\n\n"
            resumen += f"¿Confirmas estos datos? (Responde 'sí' para confirmar)"
            
            return resumen
    
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
        # Si el usuario está corrigiendo ("ya te dije..."), continuar con el flujo
        # Verificar qué dato falta y continuar
        if not contexto.nombre:
            return "¿Cuál es tu nombre completo?"
        elif not contexto.cedula:
            return f"Perfecto {contexto.nombre}. ¿Cuál es tu número de cédula?"
        elif not contexto.fecha:
            return "¿Para qué día necesitas el turno?"
        elif not contexto.hora:
            return "¿A qué hora prefieres?"
        elif not contexto.email:
            return "Para enviarte la confirmación, ¿cuál es tu email?"
        
        # Si tiene todos los datos, confirmar
        if contexto.tiene_datos_completos():
            try:
                # Generar link de Google Calendar
                from urllib.parse import quote
                fecha_hora_str = f"{contexto.fecha} {contexto.hora}:00"
                fecha_hora_obj = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M:%S')
                fecha_hora_utc = fecha_hora_obj.strftime('%Y%m%dT%H%M%S')
                fecha_fin_utc = (fecha_hora_obj + timedelta(minutes=20)).strftime('%Y%m%dT%H%M%S')
                
                titulo = quote(f"Turno - Oficina de Identificaciones")
                descripcion = quote(f"Nombre: {contexto.nombre}\\nCédula: {contexto.cedula}\\nRecuerda llegar 10 minutos antes")
                ubicacion = quote("Av. San Blas, Ciudad del Este, Alto Paraná, Paraguay")
                
                google_calendar_link = (
                    f"https://calendar.google.com/calendar/render?action=TEMPLATE"
                    f"&text={titulo}"
                    f"&dates={fecha_hora_utc}/{fecha_fin_utc}"
                    f"&details={descripcion}"
                    f"&location={ubicacion}"
                    f"&ctz=America/Asuncion"
                )
                
                # URL de encuesta de satisfacción
                encuesta_url = "https://docs.google.com/forms/d/e/1FAIpQLSfNorudi36-q0VjKTWk2GwM277wCiypOTU_qMoPhHD0aWkG8A/viewform"
                
                # ==========================================
                # GENERAR CÓDIGO ÚNICO DE TURNO
                # ==========================================
                codigo_turno = generar_codigo_turno()
                
                # ==========================================
                # GUARDAR EN BASE DE DATOS
                # ==========================================
                try:
                    conn = psycopg2.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    
                    # Verificar si la cédula es "SIN_CEDULA" o un número real
                    cedula_valor = None if contexto.cedula == "SIN_CEDULA" else contexto.cedula
                    
                    # Combinar fecha y hora en un timestamp
                    fecha_hora_completa = f"{contexto.fecha} {contexto.hora}:00"
                    
                    # Insertar turno en la base de datos CON código único
                    # Nota: La tabla usa 'fecha_hora' (timestamp), 'codigo', 'created_at'
                    cursor.execute("""
                        INSERT INTO turnos (nombre, cedula, fecha_hora, email, codigo, estado)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        contexto.nombre,
                        cedula_valor,
                        fecha_hora_completa,
                        contexto.email,
                        codigo_turno,
                        'activo'
                    ))
                    
                    turno_id = cursor.fetchone()[0]
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    logger.info(f"✅ Turno guardado en BD con ID: {turno_id}, Código: {codigo_turno}")
                    
                    # ==========================================
                    # GENERAR CÓDIGO QR (opcional - requiere setup)
                    # ==========================================
                    try:
                        import sys
                        # os ya está importado al inicio del archivo
                        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'notificaciones'))
                        from qr_generator import QRConfirmationGenerator
                        
                        # Obtener URL base desde variable de entorno (para Cloudflare/ngrok/producción)
                        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
                        qr_gen = QRConfirmationGenerator(base_url=base_url)
                        logger.info(f"📍 Usando BASE_URL para QR: {base_url}")
                        turno_data_qr = {
                            'nombre': contexto.nombre,
                            'cedula': contexto.cedula,
                            'fecha': contexto.fecha,
                            'hora': contexto.hora,
                            'numero_turno': str(turno_id),
                            'codigo_turno': codigo_turno
                        }
                        qr_data = qr_gen.generate_qr_confirmation(turno_data_qr)
                        logger.info(f"✅ QR generado para turno {turno_id} con código {codigo_turno}")
                        
                        # ==========================================
                        # ENVIAR EMAIL CON QR
                        # ==========================================
                        smtp_email = os.getenv('SMTP_EMAIL')
                        smtp_password = os.getenv('SMTP_PASSWORD')
                        
                        if smtp_email and smtp_password:
                            try:
                                from email_sender import EmailNotificationSender
                                
                                email_sender = EmailNotificationSender(
                                    smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                                    smtp_port=int(os.getenv('SMTP_PORT', 587)),
                                    email=smtp_email,
                                    password=smtp_password
                                )
                                
                                email_sender.send_confirmation_email(contexto.email, turno_data_qr, qr_data)
                                logger.info(f"✅ Email enviado a {contexto.email}")
                                
                            except Exception as e_email:
                                logger.error(f"❌ Error al enviar email: {e_email}")
                        else:
                            logger.warning("⚠️ Credenciales de email no configuradas. Email no enviado.")
                        
                    except Exception as e_qr:
                        logger.warning(f"⚠️ No se pudo generar QR: {e_qr}")
                    
                except Exception as e_db:
                    logger.error(f"❌ Error al guardar en BD: {e_db}")
                    # Continuar con la respuesta aunque falle el guardado
                
                # ==========================================
                # RESPUESTA AL USUARIO
                # ==========================================
                respuesta = f"✅ ¡Turno confirmado exitosamente!\n\n"
                respuesta += f"🎫 **CÓDIGO DE TURNO: {codigo_turno}**\n"
                respuesta += f"   � Presenta este código al llegar a la oficina\n\n"
                respuesta += f"�📋 Resumen:\n"
                respuesta += f"• Nombre: {contexto.nombre}\n"
                respuesta += f"• Cédula: {contexto.cedula}\n"
                respuesta += f"• Fecha: {contexto.fecha}\n"
                respuesta += f"• Hora: {contexto.hora}\n"
                respuesta += f"• Email: {contexto.email}\n\n"
                respuesta += f"📧 Te enviaremos un email de confirmación con el código QR y tu código de turno a: {contexto.email}\n"
                respuesta += f"   (Si no recibes el email, revisa tu carpeta de spam)\n\n"
                respuesta += f"📅 Agrega el turno a tu Google Calendar:\n{google_calendar_link}\n\n"
                respuesta += f"⏰ Recuerda llegar 10 minutos antes de tu hora asignada.\n\n"
                respuesta += f"📋 Ayúdanos a mejorar completando esta breve encuesta:\n{encuesta_url}\n\n"
                respuesta += f"¡Hasta pronto! 👋"
                
                return respuesta
            except Exception as e:
                logger.error(f"Error al confirmar turno: {e}")
                # Generar código de emergencia aunque falle la BD
                codigo_emergencia = generar_codigo_turno()
                return (
                    f"✅ ¡Turno confirmado!\n"
                    f"🎫 Tu código de turno: {codigo_emergencia}\n"
                    f"Te llegará un email con más detalles a: {contexto.email}\n"
                    f"Recuerda llegar 10 minutos antes. ¡Hasta pronto!"
                )
        return "Perfecto, continuemos. ¿Qué necesitas?"
    
    # Intent: NEGAR
    elif intent == 'deny':
        return "Entendido. ¿Hay algo más en lo que pueda ayudarte?"
    
    # Intent: AGRADECIMIENTO
    elif intent == 'agradecimiento':
        return "¡De nada! Estoy aquí para ayudarte. 😊"
    
    # Intent: MODO DESARROLLADOR (Dashboard)
    elif intent == 'modo_desarrollador':
        dashboard_url = os.getenv('DASHBOARD_URL', '/dashboard')
        return {
            'text': "🔧 **Modo Desarrollador Activado**\n\nAccede al panel de administración para ver estadísticas y gestionar turnos.",
            'show_dashboard_button': True,
            'dashboard_url': dashboard_url
        }
    
    # Intent: CONSULTAR REQUISITOS
    elif intent == 'consultar_requisitos':
        mensaje_lower = mensaje.lower()
        
        # Construir la respuesta base según el tipo de consulta
        respuesta_base = ""
        
        # Detectar tipo de consulta
        if any(word in mensaje_lower for word in ['menor', 'niño', 'niña', 'hijo', 'hija']):
            respuesta_base = (
                "📋 **Requisitos para MENORES de edad:**\n\n"
                "1. Partida de nacimiento original\n"
                "2. Documento de identidad del padre/madre/tutor\n"
                "3. Presencia del menor (si es mayor de 12 años)\n"
                "4. Certificado de estudios (si es mayor de 12 años)\n\n"
                "💰 Costo: Gratuito para la primera cédula\n"
                "🕒 Tiempo estimado: 15-30 minutos\n\n"
            )
        elif any(word in mensaje_lower for word in ['primera', 'primera vez', '1ra vez', 'nuevo']):
            respuesta_base = (
                "📋 **Requisitos para PRIMERA CÉDULA:**\n\n"
                "1. Partida de nacimiento original\n"
                "2. Certificado de estudios (si es mayor de 18 años)\n"
                "3. Presencia personal obligatoria\n\n"
                "💰 Costo: Gratuito\n"
                "🕒 Tiempo estimado: 20-40 minutos\n\n"
            )
        elif any(word in mensaje_lower for word in ['renovar', 'renovacion', 'renovación', 'vencida', 'vencimiento']):
            respuesta_base = (
                "📋 **Requisitos para RENOVACIÓN:**\n\n"
                "1. Cédula anterior (original)\n"
                "2. Partida de nacimiento actualizada (si cambió estado civil)\n"
                "3. Presencia personal obligatoria\n\n"
                "💰 Costo: Gs. 25.000\n"
                "🕒 Tiempo estimado: 15-25 minutos\n\n"
            )
        elif any(word in mensaje_lower for word in ['extranjero', 'extranjera', 'no paraguayo', 'otro pais']):
            respuesta_base = (
                "📋 **Requisitos para EXTRANJEROS:**\n\n"
                "1. Pasaporte vigente\n"
                "2. Certificado de residencia (Migraciones)\n"
                "3. Partida de nacimiento apostillada\n"
                "4. Certificado de antecedentes penales del país de origen\n"
                "5. Presencia personal obligatoria\n\n"
                "💰 Costo: Gs. 100.000\n"
                "🕒 Tiempo estimado: 30-45 minutos\n\n"
            )
        elif any(word in mensaje_lower for word in ['perdida', 'perdió', 'perdio', 'robo', 'robada', 'extraviada']):
            respuesta_base = (
                "📋 **Requisitos por PÉRDIDA/ROBO:**\n\n"
                "1. Denuncia policial (original y copia)\n"
                "2. Partida de nacimiento actualizada\n"
                "3. Presencia personal obligatoria\n\n"
                "💰 Costo: Gs. 50.000\n"
                "🕒 Tiempo estimado: 20-30 minutos\n\n"
            )
        else:
            # Requisitos generales
            respuesta_base = (
                "📋 **Requisitos para CÉDULA DE IDENTIDAD:**\n\n"
                "**Primera vez:**\n"
                "• Partida de nacimiento original\n"
                "• Presencia personal\n\n"
                "**Renovación:**\n"
                "• Cédula anterior\n"
                "• Partida de nacimiento actualizada\n\n"
                "**Menores:**\n"
                "• Partida de nacimiento\n"
                "• Documento del tutor\n\n"
                "**Pérdida/Robo:**\n"
                "• Denuncia policial\n"
                "• Partida actualizada\n\n"
                "💡 Para más detalles, especifica tu caso: 'requisitos para menores', 'requisitos primera vez', etc.\n\n"
            )
        
        # VERIFICAR SI ESTAMOS EN MEDIO DE UN FORMULARIO
        # Si falta nombre, volver a pedirlo después de responder
        if not contexto.nombre:
            return respuesta_base + "Ahora, ¿cuál es tu nombre completo para continuar con tu turno?"
        # Si falta cédula, volver a pedirla
        elif not contexto.cedula:
            return respuesta_base + f"Perfecto {contexto.nombre}. ¿Cuál es tu número de cédula para continuar?"
        # Si falta fecha, volver a pedirla
        elif not contexto.fecha:
            return respuesta_base + "¿Para qué día necesitas el turno?"
        # Si falta hora, volver a pedirla
        elif not contexto.hora:
            return respuesta_base + "¿A qué hora prefieres tu turno?"
        # Si no estamos en formulario, preguntar si quiere agendar
        else:
            return respuesta_base + "¿Necesitas agendar un turno?"
    
    # Intent: CONSULTAR UBICACIÓN
    elif intent == 'consultar_ubicacion':
        mensaje_lower = mensaje.lower()
        
        # Detectar si pregunta ESPECÍFICAMENTE por teléfono/contacto
        pregunta_telefono = any(palabra in mensaje_lower for palabra in [
            'telefono', 'teléfono', 'tlf', 'número', 'numero', 'contacto', 
            'llamar', 'celular', 'whatsapp', 'hablar con alguien', 
            'hablar con una persona', 'contacto humano', 'hablar con un operador'
        ])
        
        # Si pregunta por teléfono, solo dar números
        if pregunta_telefono:
            respuesta_base = (
                "📞 **Números de contacto para llamadas:**\n\n"
                "• +595 976 200472\n"
                "• +595 976 200641\n\n"
                "🕒 **Horario de atención:**\n"
                "Lunes a Viernes: 07:00 a 17:00\n\n"
            )
        else:
            # Si pregunta por ubicación/dirección, dar info completa
            respuesta_base = (
                "📍 **Ubicación:**\n"
                "Av. San Blas, Ciudad del Este\n"
                "Alto Paraná, Paraguay\n\n"
            "� **Contactos:**\n"
            "+595 976 200472\n"
            "+595 976 200641\n\n"
            "🗺️ **Google Maps:**\n"
            "https://maps.app.goo.gl/zvqVjGtTVtguQ9UR9\n\n"
            "�🕒 **Horario de atención:**\n"
            "Lunes a Viernes: 07:00 a 17:00\n\n"
            "🚗 Estacionamiento disponible\n"
            "🚌 Líneas de bus: 12, 15, 30\n\n"
        )
        
        # VERIFICAR SI ESTAMOS EN MEDIO DE UN FORMULARIO
        if not contexto.nombre:
            return respuesta_base + "Ahora, ¿cuál es tu nombre completo para continuar con tu turno?"
        elif not contexto.cedula:
            return respuesta_base + f"Perfecto {contexto.nombre}. ¿Cuál es tu número de cédula para continuar?"
        elif not contexto.fecha:
            return respuesta_base + "¿Para qué día necesitas el turno?"
        elif not contexto.hora:
            return respuesta_base + "¿A qué hora prefieres tu turno?"
        else:
            return respuesta_base + "¿Necesitas agendar un turno?"
    
    # Intent: CONSULTAR COSTO
    elif intent == 'consultar_costo':
        respuesta_base = (
            "💰 **Costos del trámite:**\n\n"
            "• Primera cédula: **GRATUITO** ✅\n"
            "• Renovación: Gs. 25.000\n"
            "• Pérdida/Robo: Gs. 50.000\n"
            "• Extranjeros: Gs. 100.000\n"
            "• Menores (primera): **GRATUITO** ✅\n\n"
            "💳 Formas de pago:\n"
            "• Efectivo\n"
            "• Tarjeta de débito/crédito\n"
            "• Transferencia bancaria\n\n"
        )
        
        # VERIFICAR SI ESTAMOS EN MEDIO DE UN FORMULARIO
        if not contexto.nombre:
            return respuesta_base + "Ahora, ¿cuál es tu nombre completo para continuar con tu turno?"
        elif not contexto.cedula:
            return respuesta_base + f"Perfecto {contexto.nombre}. ¿Cuál es tu número de cédula para continuar?"
        elif not contexto.fecha:
            return respuesta_base + "¿Para qué día necesitas el turno?"
        elif not contexto.hora:
            return respuesta_base + "¿A qué hora prefieres tu turno?"
        else:
            return respuesta_base + "¿Necesitas agendar un turno?"
    
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
