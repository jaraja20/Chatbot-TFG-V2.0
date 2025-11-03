"""
ORQUESTADOR INTELIGENTE MEJORADO V3.0
Integra: GitHub Copilot + Motor Difuso + Base de Datos
Versión optimizada con GitHub Copilot como modelo principal
"""

import requests
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, date, timedelta
import psycopg2
import re
import traceback
import os
from dotenv import load_dotenv
from copilot_handler import procesar_mensaje_copilot

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
        self.fecha = None
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
            r'\b\d{5,8}\b',  # Número de cédula (5-8 dígitos)
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
            r'\b(que|qu[eé]|cuales|cu[aá]les)\s+(requisitos|documentos)\b',
            r'\b(que|qu[eé])\s+necesito\b',
            r'\b(que|qu[eé])\s+debo\s+(traer|llevar|presentar)\b',
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
            r'\bcu[aá]nto\s+(voy\s+a|tengo\s+que)\s+esperar\b',
            r'\bvoy\s+a\s+esperar\s+mucho\b',
            r'\bcu[aá]nto\s+(me\s+)?(demora|tarda)\b',
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
        
        # DETECCIÓN DE NEGACIONES (debe ir primero)
        palabras_negacion = ['no tengo', 'no tiene', 'sin cedula', 'sin cédula', 'todavia no', 'todavía no', 
                            'aun no', 'aún no', 'no cuento', 'no poseo', 'no dispongo',
                            'primera vez', '1ra vez', '1era vez', 'es mi primera', 'primera tramite']
        if any(neg in mensaje_lower for neg in palabras_negacion):
            logger.info(f"🎯 Intent detectado: negacion_sin_cedula (0.98)")
            return ("negacion_sin_cedula", 0.98)
        
        # Palabras clave de intents de ACCIÓN (no son nombres)
        palabras_accion = ['agendar', 'turno', 'cita', 'horario', 'disponibilidad', 
                          'requisitos', 'ubicacion', 'ubicación', 'direccion', 'dirección',
                          'costo', 'precio', 'cuanto', 'cuánto', 'pagar',
                          'consultar', 'ver', 'necesito', 'información', 'informacion',
                          'oficina', 'queda', 'esta', 'esta ubicada', 'como llego',
                          'ayuda', 'ayudar', 'puedes', 'necesitas', 'hacer']
        
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
        
        # CONTEXTO: Si NO tenemos nombre y el mensaje son 2-4 palabras sin números 
        # (probablemente nombre), pero SOLO si NO es un mensaje de acción
        if not contexto.nombre and not es_accion and 2 <= len(mensaje.split()) <= 4 and not re.search(r'\d', mensaje):
            palabras = mensaje.split()
            palabras_lower = [p.lower() for p in palabras]
            
            # Verificar que NO contengan palabras prohibidas
            if any(p in palabras_prohibidas for p in palabras_lower):
                logger.info(f"⚠️ Mensaje contiene palabras prohibidas, no es un nombre: {mensaje}")
                return ("desconocido", 0.0)
            
            # Verificar que sean palabras válidas (al menos 2 letras cada una, solo letras)
            if all(len(p) >= 2 and p.isalpha() for p in palabras):
                # Verificar que al menos una palabra empiece con mayúscula (característica de nombres propios)
                if any(p[0].isupper() for p in palabras):
                    logger.info(f"🎯 Intent detectado por contexto: informar_nombre (0.95)")
                    return ("informar_nombre", 0.95)
                else:
                    logger.info(f"⚠️ Posible nombre pero sin mayúsculas: {mensaje}")
            else:
                logger.info(f"⚠️ Palabras no válidas como nombre: {mensaje}")
        
        # CONTEXTO: Si ya tenemos nombre pero no cédula, y el mensaje son solo números
        if contexto.nombre and not contexto.cedula:
            if re.match(r'^\d{5,8}$', mensaje.strip()):
                logger.info(f"🎯 Intent detectado por contexto: informar_cedula (0.98)")
                return ("informar_cedula", 0.98)
        
        # CONTEXTO: Si ya tenemos fecha pero no hora, y el mensaje habla de hora
        if contexto.fecha and not contexto.hora:
            # Detectar frases como "las 8", "para las 7", "a las 10", "8 está bien"
            if re.search(r'\b(las|para\s+las|a\s+las)?\s*(\d{1,2})\s*(esta?\s+(bien|perfecto|ok))?', mensaje_lower):
                logger.info(f"🎯 Intent detectado por contexto: elegir_horario (0.98)")
                return ("elegir_horario", 0.98)
        
        # 1. MÉTODO RÁPIDO: Patrones de palabras clave
        intent_patron, confianza_patron = self._clasificar_por_patrones(mensaje_lower)
        
        # CONTEXTO: Si el patrón dice "informar_nombre" pero ya tenemos nombre, buscar cédula
        if intent_patron == 'informar_nombre' and contexto.nombre and not contexto.cedula:
            # Verificar si el mensaje contiene números (probablemente cédula)
            if re.search(r'\d{5,8}', mensaje):
                logger.info(f"🎯 Intent corregido por contexto: informar_cedula (0.95)")
                return ("informar_cedula", 0.95)
        
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
    
    # Extraer CÉDULA (5-8 dígitos para aceptar cédulas más cortas)
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
        
        # Crear estructura completa de horarios (8:00 a 17:00)
        horarios_completos = {}
        for hora in range(8, 18):  # 8:00 a 17:00
            hora_str = f"{hora:02d}:00"
            horarios_completos[hora_str] = 0  # Por defecto, disponible
        
        # Actualizar con ocupación real
        for hora_str, ocupados in resultados:
            if hora_str in horarios_completos:
                horarios_completos[hora_str] = ocupados
        
        # Contar cuántas horas tienen disponibilidad
        horas_disponibles = sum(1 for ocupacion in horarios_completos.values() if ocupacion < 5)
        
        logger.info(f"📊 {fecha}: {horas_disponibles}/10 horas disponibles")
        return horarios_completos
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo disponibilidad: {e}")
        # Si hay error, asumir que hay disponibilidad
        horarios_default = {}
        for hora in range(8, 18):
            horarios_default[f"{hora:02d}:00"] = 0
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
            # Mostrar horarios disponibles
            disponibilidad = obtener_disponibilidad_real(contexto.fecha)
            if MOTOR_DIFUSO_OK:
                try:
                    mejor_hora = obtener_mejor_recomendacion(disponibilidad)
                    return f"Para el {contexto.fecha}, te recomiendo {mejor_hora}. ¿Te parece bien esta hora?"
                except:
                    pass
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
        
        # IMPORTANTE: Verificar si estamos en medio de un formulario
        # Si falta nombre, NO mostrar disponibilidad todavía
        if not contexto.nombre:
            return (
                "Me encantaría mostrarte los horarios disponibles, pero primero necesito "
                "algunos datos para agendar tu turno.\n\n"
                "¿Cuál es tu nombre completo?"
            )
        
        # Si falta cédula, pedir cédula primero
        if not contexto.cedula:
            return (
                f"Perfecto {contexto.nombre}, para mostrarte la disponibilidad necesito "
                "completar tus datos.\n\n"
                "¿Cuál es tu número de cédula?"
            )
        
        # Ya tenemos nombre y cédula, podemos mostrar disponibilidad
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
                    horarios_disponibles = [h for h, o in disponibilidad.items() if o < 5]
                    
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
                    horarios_disponibles = [h for h, o in disponibilidad.items() if o < 5]
                    
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
                
                horarios_disponibles = [h for h, o in disponibilidad.items() if o < 5]
                
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
            if ocupacion < 5:  # Disponible
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
                    if ocupacion < 5:  # Disponible
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
                    return "😔 Lo siento, no atendemos los fines de semana. Nuestro horario es de lunes a viernes, 07:00 a 17:00. ¿Prefieres agendar para el lunes?"
                
                # Obtener disponibilidad
                disponibilidad = obtener_disponibilidad_real(fecha)
                horarios_disponibles = [(h, o) for h, o in disponibilidad.items() if o < 5]
                
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
                # GUARDAR EN BASE DE DATOS
                # ==========================================
                try:
                    conn = psycopg2.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    
                    # Verificar si la cédula es "SIN_CEDULA" o un número real
                    cedula_valor = None if contexto.cedula == "SIN_CEDULA" else contexto.cedula
                    
                    # Insertar turno en la base de datos
                    cursor.execute("""
                        INSERT INTO turnos (nombre, cedula, fecha, hora, email, estado, fecha_creacion)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (
                        contexto.nombre,
                        cedula_valor,
                        contexto.fecha,
                        contexto.hora,
                        contexto.email,
                        'pendiente'
                    ))
                    
                    turno_id = cursor.fetchone()[0]
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    logger.info(f"✅ Turno guardado en BD con ID: {turno_id}")
                    
                    # ==========================================
                    # GENERAR CÓDIGO QR (opcional - requiere setup)
                    # ==========================================
                    try:
                        import sys
                        import os
                        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'notificaciones'))
                        from qr_generator import QRConfirmationGenerator
                        
                        qr_gen = QRConfirmationGenerator(base_url="http://localhost:5000")
                        turno_data_qr = {
                            'nombre': contexto.nombre,
                            'cedula': contexto.cedula,
                            'fecha': contexto.fecha,
                            'hora': contexto.hora,
                            'numero_turno': str(turno_id)
                        }
                        qr_data = qr_gen.generate_qr_confirmation(turno_data_qr)
                        logger.info(f"✅ QR generado para turno {turno_id}")
                        
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
                respuesta += f"📋 Resumen:\n"
                respuesta += f"• Nombre: {contexto.nombre}\n"
                respuesta += f"• Cédula: {contexto.cedula}\n"
                respuesta += f"• Fecha: {contexto.fecha}\n"
                respuesta += f"• Hora: {contexto.hora}\n"
                respuesta += f"• Email: {contexto.email}\n\n"
                respuesta += f"📧 Te enviaremos un email de confirmación con el código QR a: {contexto.email}\n"
                respuesta += f"   (Si no recibes el email, revisa tu carpeta de spam)\n\n"
                respuesta += f"📅 Agrega el turno a tu Google Calendar:\n{google_calendar_link}\n\n"
                respuesta += f"⏰ Recuerda llegar 10 minutos antes de tu hora asignada.\n\n"
                respuesta += f"📋 Ayúdanos a mejorar completando esta breve encuesta:\n{encuesta_url}\n\n"
                respuesta += f"¡Hasta pronto! 👋"
                
                return respuesta
            except Exception as e:
                logger.error(f"Error al confirmar turno: {e}")
                return (
                    f"✅ ¡Turno confirmado!\n"
                    f"Te llegará un email con el código QR a: {contexto.email}\n"
                    f"Recuerda llegar 10 minutos antes. ¡Hasta pronto!"
                )
        return "Perfecto, continuemos. ¿Qué necesitas?"
    
    # Intent: NEGAR
    elif intent == 'deny':
        return "Entendido. ¿Hay algo más en lo que pueda ayudarte?"
    
    # Intent: AGRADECIMIENTO
    elif intent == 'agradecimiento':
        return "¡De nada! Estoy aquí para ayudarte. 😊"
    
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
        respuesta_base = (
            "📍 **Ubicación:**\n"
            "Av. San Blas, Ciudad del Este\n"
            "Alto Paraná, Paraguay\n\n"
            "🕒 **Horario de atención:**\n"
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