from typing import Any, Text, Dict, List, Optional, Tuple
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, SessionStarted, EventType, FollowupAction, ActionExecuted
from rasa_sdk.forms import FormValidationAction
from calendar_utils import crear_evento_turno, consultar_disponibilidad
from sqlalchemy import create_engine, Column, String, Integer, DateTime, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import cast, Date
from sqlalchemy.exc import SQLAlchemyError
import datetime
import random
import string
import dateparser
import re
import logging
import time
from contextlib import contextmanager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# FORMATO DE FECHAS EN ESPAÑOL
# =====================================================
_DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

PALABRAS_PROHIBIDAS_NOMBRE = [
    "amor", "corazon", "test", "prueba", "xxx", "asdf", "qwerty",
    "hola", "chau", "bot", "chatbot", "admin", "root", "user"
]

def validar_nombre_real(nombre: str) -> Tuple[bool, str]:
    """
    Valida que el nombre sea realista
    
    Returns:
        (es_valido, mensaje_error)
    """
    if not nombre or len(nombre.strip()) < 3:
        return False, "El nombre es demasiado corto"
    
    nombre_limpio = nombre.strip().lower()
    partes = nombre_limpio.split()
    
    # Debe tener al menos 2 palabras (nombre y apellido)
    if len(partes) < 2:
        return False, "Necesito tu nombre completo (nombre y apellido)"
    
    # Cada parte debe tener al menos 2 letras
    for parte in partes:
        if len(parte) < 2:
            return False, "Cada parte del nombre debe tener al menos 2 letras"
        
        # Solo letras (permitir tildes y ñ)
        if not re.match(r'^[a-záéíóúñü]+$', parte, re.IGNORECASE):
            return False, f"El nombre solo puede contener letras (sin números ni símbolos)"
    
    # Verificar palabras prohibidas
    for palabra in PALABRAS_PROHIBIDAS_NOMBRE:
        if palabra in nombre_limpio:
            return False, "Por favor, ingresá tu nombre real completo"
    
    # Verificar que no sea una frase o expresión
    if len(partes) > 4:
        return False, "Por favor, solo nombre y apellido(s)"
    
    return True, ""



def format_fecha_es(fecha: datetime.date, con_anio: bool = False) -> str:
    """Devuelve una fecha en formato español, manejando errores y capitalización."""
    try:
        dia_nombre = _DIAS_ES[fecha.weekday()]
        mes_nombre = _MESES_ES[fecha.month - 1]
        if con_anio:
            texto = f"{dia_nombre} {fecha.day} de {mes_nombre} de {fecha.year}"
        else:
            texto = f"{dia_nombre} {fecha.day} de {mes_nombre}"
        return texto.capitalize()
    except Exception as e:
        logger.error(f"Error formateando fecha {fecha}: {e}")
        return fecha.strftime("%d/%m/%Y")



# Motor difuso
try:
    from motor_difuso import calcular_espera
    FUZZY_AVAILABLE = True
    logger.info("Motor difuso cargado exitosamente")
except ImportError:
    logger.warning("Motor difuso no disponible, usando simulación básica")
    FUZZY_AVAILABLE = False
    def calcular_espera(ocupacion, urgencia):
        base = ocupacion * 0.4 + urgencia * 5
        return min(60, max(5, base))

# =====================================================
# ✅ SISTEMA DE LOGGING MEJORADO (conversation_logger.py)
# =====================================================
try:
    from conversation_logger import (
        setup_improved_logging_system, 
        log_rasa_interaction_improved,
        get_improved_conversation_logger,
        set_improved_conversation_logger
    )
    IMPROVED_LOGGING_AVAILABLE = True
    logger.info("✅ Sistema de logging mejorado cargado exitosamente")
except ImportError as e:
    IMPROVED_LOGGING_AVAILABLE = False
    logger.error(f"❌ Sistema de logging mejorado no disponible: {e}")
    
    # Crear funciones dummy para evitar errores
    def setup_improved_logging_system(*args, **kwargs):
        return None
    def log_rasa_interaction_improved(*args, **kwargs):
        pass
    def get_improved_conversation_logger():
        return None
    def set_improved_conversation_logger(*args, **kwargs):
        pass

# =====================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =====================================================
DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    Session = sessionmaker(bind=engine)
    Base = declarative_base()
    logger.info("Conexión a base de datos establecida")
except Exception as e:
    logger.error(f"Error conectando a la base de datos: {e}")
    raise

# Configurar sistema de aprendizaje
improved_logger = None
if IMPROVED_LOGGING_AVAILABLE:
    try:
        improved_logger = setup_improved_logging_system(DATABASE_URL)
        set_improved_conversation_logger(improved_logger)
        logger.info("✅ Sistema de logging mejorado inicializado correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema mejorado: {e}")
        improved_logger = None

# Ya no necesitamos fallback - solo usamos improved_logger

# =====================================================
# MODELOS DE BASE DE DATOS
# =====================================================
class Turno(Base):
    __tablename__ = 'turnos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    cedula = Column(String(20))
    fecha_hora = Column(DateTime, nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    estado = Column(String(20), default='activo')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    event_id = Column(String(255), nullable=True)
    email = Column(String(120), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('fecha_hora', 'cedula', name='unique_turno_persona_fecha'),
    )

# Crear tablas
try:
    Base.metadata.create_all(engine)
    logger.info("Tablas creadas/verificadas exitosamente")
except Exception as e:
    logger.error(f"Error creando tablas: {e}")

# =====================================================
# UTILIDADES
# =====================================================
@contextmanager
def get_db_session():
    """Context manager robusto con autorecuperación de sesiones fallidas"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"⚠️ Error en sesión de BD: {e}")
        try:
            session.rollback()
        except Exception:
            logger.warning("No se pudo hacer rollback; reiniciando sesión.")
        finally:
            try:
                session.close()
            except Exception:
                pass
        # 🔁 recrear conexión limpia
        session = Session()
        raise
    finally:
        try:
            session.close()
        except Exception:
            pass

def extraer_email_del_texto(texto: str) -> Optional[str]:
    """Extrae email de un texto si existe"""
    patron_email = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(patron_email, texto)
    return match.group(0) if match else None

def generar_codigo_unico(longitud=6):
    """Genera un código único alfanumérico"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=longitud))

def normalizar_fecha(texto: str) -> Optional[datetime.date]:
    """Convierte texto natural a fecha robusta en español (maneja expresiones ambiguas)."""
    if not texto:
        return None
    
    texto = texto.lower().strip()
    hoy = datetime.date.today()

    # Casos simples sin usar parser
    if texto in ["hoy", "el día de hoy"]:
        return hoy
    if "mañana" in texto:
        return hoy + datetime.timedelta(days=1)
    if "pasado mañana" in texto:
        return hoy + datetime.timedelta(days=2)
    
    settings = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': datetime.datetime.now(),
        'DATE_ORDER': 'DMY',
        'TIMEZONE': 'America/Asuncion'
    }
    
    try:
        fecha_parseada = dateparser.parse(texto, languages=['es'], settings=settings)
        if fecha_parseada:
            return fecha_parseada.date()
    except Exception as e:
        logger.error(f"Error parseando fecha '{texto}': {e}")
    
    return None

def normalizar_hora(texto: str) -> Optional[datetime.time]:
    """Convierte texto natural a hora"""
    if not texto:
        return None
    
    patrones = [
        r'(\d{1,2}):(\d{2})',
        r'(\d{1,2})\s*(am|pm)',
        r'(\d{1,2})\s*de\s*la\s*(mañana|tarde|noche)',
    ]
    
    texto_limpio = texto.lower().strip()
    
    for patron in patrones:
        match = re.search(patron, texto_limpio)
        if match:
            try:
                hora = int(match.group(1))
                
                if len(match.groups()) > 1:
                    periodo = match.group(2) if ':' not in match.group(0) else None
                    if periodo == 'pm' and hora < 12:
                        hora += 12
                    elif periodo == 'am' and hora == 12:
                        hora = 0
                
                if 'tarde' in texto_limpio and hora < 12:
                    hora += 12
                elif 'noche' in texto_limpio and hora < 18:
                    hora += 12
                
                minutos = int(match.group(2)) if ':' in match.group(0) else 0
                return datetime.time(hora, minutos)
            except (ValueError, IndexError):
                continue
    
    try:
        fecha_parseada = dateparser.parse(texto, languages=['es'])
        if fecha_parseada:
            return fecha_parseada.time()
    except:
        pass
    
    return None

def validar_horario_laboral(hora: datetime.time) -> bool:
    """Valida que la hora esté en horario laboral (7:00-15:00, excepto 11:00)"""
    if not hora:
        return False
    # Bloquear hora de almuerzo
    if hora.hour == 11:
        return False
    # Horario de atención: 7:00 - 15:00
    return datetime.time(7, 0) <= hora <= datetime.time(15, 0)

# ✅ FUNCIÓN CORREGIDA: Consulta BD real con debug detallado
def consultar_ocupacion_real_bd(fecha: datetime.date, hora_inicio: int, hora_fin: int, session) -> float:
    """
    Consulta la ocupación REAL de la base de datos para un rango de horas
    Retorna el porcentaje de ocupación (0-100) con debug detallado
    """
    try:
        inicio = datetime.datetime.combine(fecha, datetime.time(hora_inicio, 0))
        fin = datetime.datetime.combine(fecha, datetime.time(hora_fin, 0))
        
        # DEBUG: Log de consulta
        logger.info(f"🔍 DEBUG BD: Consultando ocupación desde {inicio} hasta {fin}")
        
        # Contar turnos ocupados en la BD
        turnos_ocupados = session.query(Turno).filter(
            Turno.fecha_hora >= inicio,
            Turno.fecha_hora < fin,
            Turno.estado == 'activo'
        ).count()
        
        # DEBUG: Mostrar turnos encontrados
        turnos_detalle = session.query(Turno).filter(
            Turno.fecha_hora >= inicio,
            Turno.fecha_hora < fin,
            Turno.estado == 'activo'
        ).all()
        
        logger.info(f"🔍 DEBUG BD: Turnos encontrados: {turnos_ocupados}")
        for turno in turnos_detalle:
            logger.info(f"  - {turno.nombre} el {turno.fecha_hora} (código: {turno.codigo})")
        
        # Calcular slots totales considerando 3 mesas simultáneas
        horas_en_rango = hora_fin - hora_inicio
        slots_por_hora = 4  # Cada 15 minutos: :00, :15, :30, :45
        mesas_simultaneas = 3  # 3 personas atendidas al mismo tiempo
        slots_totales = horas_en_rango * slots_por_hora * mesas_simultaneas
        
        logger.info(f"🔍 DEBUG BD: Slots totales calculados: {slots_totales} (horas: {horas_en_rango}, slots/hora: {slots_por_hora}, mesas: {mesas_simultaneas})")
        
        if slots_totales == 0:
            logger.warning("🔍 DEBUG BD: Slots totales = 0, retornando 0% ocupación")
            return 0.0
        
        porcentaje_ocupacion = (turnos_ocupados / slots_totales) * 100
        logger.info(f"🔍 DEBUG BD: Ocupación calculada: {porcentaje_ocupacion:.1f}% ({turnos_ocupados}/{slots_totales})")
        
        return round(porcentaje_ocupacion, 1)
        
    except Exception as e:
        logger.error(f"❌ ERROR consultar_ocupacion_real_bd: {e}")
        return 0.0  # En caso de error, asumir 0% ocupación

# ✅ FUNCIÓN CORREGIDA: Obtener horarios disponibles reales
def obtener_horarios_disponibles_reales(fecha: datetime.date, session, limite: int = 20) -> List[str]:
    """
    Obtiene horarios REALMENTE disponibles de la BD con debug detallado
    Retorna lista de horarios en formato HH:MM
    """
    try:
        logger.info(f"🔍 DEBUG: Buscando horarios disponibles para {fecha}")
        horarios_disponibles = []
        
        # Total de turnos para esta fecha (para debug)
        total_turnos_fecha = session.query(Turno).filter(
            cast(Turno.fecha_hora, Date) == fecha,
            Turno.estado == 'activo'
        ).count()
        logger.info(f"🔍 DEBUG: Total turnos ya agendados para {fecha}: {total_turnos_fecha}")
        
        # Generar todos los horarios posibles (7:00-15:00, cada 15 min, excepto 11:00-11:59)
        for hora in range(7, 15):
            if hora == 11:  # Saltar hora de almuerzo
                logger.info(f"🔍 DEBUG: Saltando hora {hora}:XX (almuerzo)")
                continue
            
            for minuto in [0, 15, 30, 45]:
                hora_dt = datetime.time(hora, minuto)
                fecha_hora = datetime.datetime.combine(fecha, hora_dt)
                
                # Contar turnos en este horario exacto (máximo 3 simultáneos)
                turnos_en_horario = session.query(Turno).filter(
                    Turno.fecha_hora == fecha_hora,
                    Turno.estado == 'activo'
                ).count()
                
                # Si hay menos de 3 turnos, hay disponibilidad
                if turnos_en_horario < 3:
                    horario_str = f"{hora:02d}:{minuto:02d}"
                    horarios_disponibles.append(horario_str)
                    logger.info(f"🔍 DEBUG: {horario_str} disponible ({turnos_en_horario}/3 ocupado)")
                else:
                    logger.info(f"🔍 DEBUG: {hora:02d}:{minuto:02d} ocupado ({turnos_en_horario}/3)")
                
                if len(horarios_disponibles) >= limite:
                    logger.info(f"🔍 DEBUG: Límite alcanzado ({limite}), retornando horarios")
                    return horarios_disponibles
        
        logger.info(f"🔍 DEBUG: Total horarios disponibles encontrados: {len(horarios_disponibles)}")
        return horarios_disponibles
        
    except Exception as e:
        logger.error(f"❌ ERROR obtener_horarios_disponibles_reales: {e}")
        return []


# ✅ FUNCIÓN CORREGIDA: Consultar disponibilidad con debug
def consultar_disponibilidad_real(fecha: datetime.date, session) -> Dict[str, int]:
    """Consulta disponibilidad real desde BD por franjas horarias con debug"""
    try:
        logger.info(f"🔍 DEBUG: Consultando disponibilidad real para {fecha}")
        ocupacion_franjas = {}
        
        franjas_config = {
            'temprano': (7, 9),    # 7:00-9:00
            'manana': (9, 11),     # 9:00-11:00 (antes de almuerzo)
            'tarde': (12, 15)      # 12:00-15:00 (después de almuerzo)
        }
        
        for franja, (hora_inicio, hora_fin) in franjas_config.items():
            ocupacion = consultar_ocupacion_real_bd(fecha, hora_inicio, hora_fin, session)
            ocupacion_franjas[franja] = int(ocupacion)
            logger.info(f"🔍 DEBUG: Franja {franja} ({hora_inicio}-{hora_fin}): {ocupacion}% ocupado")
        
        return ocupacion_franjas
        
    except Exception as e:
        logger.error(f"❌ ERROR consultar_disponibilidad_real: {e}")
        return {'temprano': 0, 'manana': 0, 'tarde': 0}

# ✅ CORREGIDO: Detectar frases ambiguas ANTES de procesarlas
def es_frase_ambigua(texto: str) -> bool:
    """Detecta si el texto contiene frases ambiguas que requieren lógica difusa (sin días explícitos)."""
    if not texto:
        return False

    texto_lower = texto.lower().strip()

    frases_genericas = [
        "lo antes posible", "lo más rápido", "cuando antes", "cuanto antes", "urgente",
        "primer turno", "primera fecha", "el primer horario que tengas",
        "cuando tengas", "cuando haya", "lo que tengas",
        "qué día", "que dia", "qué fecha", "que fecha",
        "día disponible", "dia disponible", "fecha disponible",
        "cuando haya menos gente", "cuando esté tranquilo",
        "el mejor horario", "recomendame", "recomiendame", "sugerime",
        "que horario", "horario libre", "cuando convenga",
        "lo mas temprano", "lo más temprano", "lo mas tarde", "lo más tarde",
        "a la mañana", "a la tarde", "temprano", "cualquier horario",
        "que horarios hay", "que horarios", "horarios disponibles",
        "está disponible", "esta disponible", "qué hora hay", "que hora hay",
        "qué hora está disponible", "que hora esta disponible",
        "qué horario está disponible", "que horario esta disponible"
    ]

    # ⚠️ Importante: NO considerar "lunes", "martes", "jueves", etc. como ambiguo
    return any(frase in texto_lower for frase in frases_genericas)


# ✅ NUEVO: Detección de frases de corrección de datos
def detectar_correccion(texto: str) -> Optional[str]:
    """Detecta si el usuario quiere cambiar o corregir un dato y cuál."""
    texto = texto.lower().strip()
    if any(p in texto for p in ["cambiar nombre", "corregir nombre", "me equivoqué en mi nombre"]):
        return "nombre"
    if any(p in texto for p in ["cambiar cedula", "corregir cedula", "me equivoqué en mi cédula", "editar cedula", "editar cédula"]):
        return "cedula"
    if any(p in texto for p in ["cambiar fecha", "otra fecha", "modificar fecha", "reagendar", "reprogramar", "nueva fecha"]):
        return "fecha"
    if any(p in texto for p in ["cambiar hora", "otra hora", "modificar hora", "más temprano", "más tarde", "hora diferente"]):
        return "hora"
    return None

# ✅ NUEVO: Función auxiliar para logging con sistema mejorado
def log_interaction_improved(tracker, bot_response, additional_data=None):
    """
    Función auxiliar para registrar interacciones usando el sistema mejorado
    """
    try:
        improved_logger = get_improved_conversation_logger()
        if improved_logger:
            # Preparar datos LLM si están disponibles
            llm_classification = additional_data if additional_data else {}
            log_rasa_interaction_improved(improved_logger, tracker, bot_response, llm_classification)
    except Exception as e:
        logger.error(f"❌ Error en logging mejorado: {e}")

# =====================================================
# VALIDACIÓN DE FORMULARIO
# =====================================================
class ValidateFormularioTurno(FormValidationAction):
    def name(self) -> Text:
        return "validate_turno_form"

    def validate_nombre(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        texto_usuario = str(slot_value).strip().lower()
        
        # Detectar corrección
        correccion = detectar_correccion(texto_usuario)
        if correccion:
            bot_response = f"Perfecto, corregiremos tu {correccion}."
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response)
            return {correccion: None}
        
        # Validar que sea un nombre real
        es_valido, mensaje_error = validar_nombre_real(slot_value)
        
        if not es_valido:
            bot_response = f"⚠️ {mensaje_error}\n\nEjemplo: 'Juan Carlos Pérez' o 'María González'"
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response, {"feedback_type": "validation_error", "field": "nombre"})
            return {"nombre": None}
        
        # Capitalizar correctamente
        nombre_formateado = slot_value.strip().title()
        
        bot_response = f"Perfecto, {nombre_formateado.split()[0]} 👍"
        dispatcher.utter_message(text=bot_response)
        log_interaction_improved(tracker, bot_response, {"validation_success": True, "field": "nombre"})
        return {"nombre": nombre_formateado}


    def validate_cedula(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        texto_usuario = str(slot_value).strip().lower()
        correccion = detectar_correccion(texto_usuario)
        if correccion:
            bot_response = f"Perfecto, corregiremos tu {correccion}."
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response)
            return {correccion: None}
        
        if not slot_value:
            return {"cedula": None}
        
        frases_primera_vez = ["primera vez", "no tengo", "nunca tuve", "primera", "no tengo cedula"]
        if any(frase in texto_usuario for frase in frases_primera_vez):
            bot_response = "Entendido, es tu primera cédula. Recordá que necesitarás partida de nacimiento original."
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response, {"cedula_type": "primera_vez"})
            return {"cedula": "PRIMERA_VEZ"}
        
        cedula_limpia = re.sub(r'[^\d]', '', texto_usuario)
        if cedula_limpia and 1 <= len(cedula_limpia) <= 8:
            log_interaction_improved(tracker, f"Cédula {cedula_limpia} registrada", {"validation_success": True, "field": "cedula"})
            return {"cedula": cedula_limpia}
        
        bot_response = "La cédula debe tener entre 1 y 8 dígitos, o decime si es tu primera vez."
        dispatcher.utter_message(text=bot_response)
        log_interaction_improved(tracker, bot_response, {"feedback_type": "validation_error", "field": "cedula"})
        return {"cedula": None}


    # ✅ CORREGIDO: validate_fecha ahora detecta frases ambiguas
    def validate_fecha(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        
        texto_usuario = str(slot_value).strip().lower()
        
        # ✅ NUEVA: Prevenir sobrescritura si ya hay fecha confirmada
        fecha_existente = tracker.get_slot("fecha")
        requested_slot = tracker.get_slot("requested_slot")
        
        # Si ya hay fecha Y NO estamos en el slot de fecha, NO sobrescribir
        if fecha_existente and requested_slot != "fecha":
            logger.info(f"🔒 Fecha ya existe ({fecha_existente}), ignorando '{texto_usuario}'")
            return {}  # No hacer nada
        
        # Detectar corrección
        correccion = detectar_correccion(texto_usuario)
        if correccion:
            bot_response = f"Perfecto, corregiremos tu {correccion}."
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response)
            return {correccion: None}
        
        if not slot_value:
            return {"fecha": None}
        
        # ✅ NUEVA: Detectar referencias al contexto previo
        referencias_contexto = [
            "ese martes", "ese dia", "ese día", "esa fecha", 
            "el martes", "ese mismo", "lo mismo", "esa misma"
        ]
        
        if any(ref in texto_usuario for ref in referencias_contexto):
            # Buscar última fecha mencionada en el historial
            eventos = tracker.events
            ultima_fecha_mencionada = None
            
            for evento in reversed(eventos):
                if evento.get("event") == "bot" and "texto" in evento:
                    texto_bot = evento["texto"].lower()
                    # Buscar fechas en formato "martes 4 de noviembre"
                    match = re.search(r'(\w+\s+\d{1,2}\s+de\s+\w+)', texto_bot)
                    if match:
                        try:
                            fecha_parseada = normalizar_fecha(match.group(1))
                            if fecha_parseada:
                                ultima_fecha_mencionada = fecha_parseada
                                break
                        except:
                            pass
            
            if ultima_fecha_mencionada:
                bot_response = f"Perfecto, confirmo la fecha: {format_fecha_es(ultima_fecha_mencionada, True)}"
                dispatcher.utter_message(text=bot_response)
                log_interaction_improved(tracker, bot_response, {"fecha_confirmada_contexto": True})
                return {"fecha": ultima_fecha_mencionada.isoformat()}
        
        # 🔍 Detección de frases ambiguas
        if es_frase_ambigua(texto_usuario):
            logger.info(f"Frase ambigua detectada en fecha: '{texto_usuario}'")
            
            dias_futuros = []
            for i in range(1, 31):
                fecha_futura = datetime.date.today() + datetime.timedelta(days=i)
                if fecha_futura.weekday() >= 5:
                    continue
                
                try:
                    with get_db_session() as session:
                        ocupacion_franjas = consultar_disponibilidad_real(fecha_futura, session)
                        ocupacion_promedio = sum(ocupacion_franjas.values()) / len(ocupacion_franjas)
                        dias_futuros.append({
                            'fecha': fecha_futura,
                            'ocupacion': ocupacion_promedio,
                            'dia_nombre': format_fecha_es(fecha_futura)
                        })
                except Exception as e:
                    logger.error(f"❌ Error consultando ocupación: {e}")
                    continue
            
            if dias_futuros:
                dias_ordenados = sorted(dias_futuros, key=lambda x: x['ocupacion'])
                mensaje = "📅 **Fechas recomendadas (menor ocupación):**\n\n"
                for i, dia in enumerate(dias_ordenados[:5], 1):
                    emoji = "🟢" if dia['ocupacion'] < 50 else "🟡" if dia['ocupacion'] < 80 else "🔴"
                    mensaje += f"{emoji} {dia['dia_nombre']}: {dia['ocupacion']:.0f}% ocupado\n"
                mensaje += f"\n💡 Te recomiendo: **{dias_ordenados[0]['dia_nombre']}**"
                mensaje += "\n\n✍️ Decime para qué fecha querés (ej: 'ese martes', 'viernes', '15 de octubre')"
                dispatcher.utter_message(text=mensaje)
                log_interaction_improved(tracker, mensaje, {"recomendacion_fecha": True, "tipo": "fuzzy_ambiguous"})
                return {"fecha": None}
        
        # 🔍 Intentar parsear fecha
        fecha_normalizada = normalizar_fecha(texto_usuario)
        hoy = datetime.date.today()
        
        if not fecha_normalizada:
            dispatcher.utter_message(
                text="No pude entender la fecha. Podés decir:\n"
                    "• 'mañana', 'lunes 25', '15 de octubre'\n"
                    "• 'ese martes' (si mencioné una fecha antes)"
            )
            return {"fecha": None}
        
        # ✅ Manejar fechas pasadas (tomar próximo mes/año)
        if fecha_normalizada < hoy:
            try:
                if fecha_normalizada.month < hoy.month:
                    # Próximo año
                    fecha_normalizada = fecha_normalizada.replace(year=hoy.year + 1)
                else:
                    # Próximo mes
                    nueva_fecha = fecha_normalizada.replace(month=hoy.month + 1)
                    if nueva_fecha > hoy:
                        fecha_normalizada = nueva_fecha
            except ValueError:
                dispatcher.utter_message(
                    text="La fecha debe ser de hoy en adelante. ¿Para qué fecha necesitás el turno?"
                )
                return {"fecha": None}
        
        # ⚠️ Limitar rango
        if (fecha_normalizada - hoy).days > 30:
            dispatcher.utter_message(
                text="Solo podemos agendar turnos hasta 30 días adelante. Elegí una fecha más cercana."
            )
            return {"fecha": None}
        
        # ⚠️ Solo días hábiles
        if fecha_normalizada.weekday() > 4:
            dispatcher.utter_message(
                text="Solo atendemos de lunes a viernes. Elegí un día hábil."
            )
            return {"fecha": None}
        
        # ✅ Verificar disponibilidad real
        with get_db_session() as session:
            horarios_libres = obtener_horarios_disponibles_reales(fecha_normalizada, session)
            if not horarios_libres:
                proxima_fecha = None
                for i in range(1, 15):
                    futura = fecha_normalizada + datetime.timedelta(days=i)
                    if futura.weekday() < 5:
                        libres_futura = obtener_horarios_disponibles_reales(futura, session)
                        if libres_futura:
                            proxima_fecha = futura
                            break
                if proxima_fecha:
                    dispatcher.utter_message(
                        text=f"⚠️ En {format_fecha_es(fecha_normalizada)} no hay horarios disponibles.\n"
                            f"💡 Te recomiendo **{format_fecha_es(proxima_fecha)}**\n\n"
                            f"¿Te sirve esa fecha? (decí 'ese día' o 'sí')"
                    )
                else:
                    dispatcher.utter_message(
                        text="⚠️ No hay horarios disponibles próximamente. Probá más adelante."
                    )
                return {"fecha": None}
        
        bot_response = f"Perfecto, registré la fecha para el **{format_fecha_es(fecha_normalizada, True)}** ✅"
        dispatcher.utter_message(text=bot_response)
        log_interaction_improved(tracker, bot_response, {"validation_success": True, "field": "fecha"})
        return {"fecha": fecha_normalizada.isoformat()}


    # ✅ CORREGIDO: validate_hora con mejor debug y lógica
    def validate_hora(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        
        if not slot_value:
            return {"hora": None}
        
        texto_usuario = str(slot_value).strip().lower()
        logger.info(f"🔍 DEBUG: Validando hora: '{texto_usuario}'")
        
        # Detectar corrección
        correccion = detectar_correccion(texto_usuario)
        if correccion:
            bot_response = f"Perfecto, corregiremos tu {correccion}."
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response)
            return {correccion: None}
        
        # ✅ NUEVA: Detección de expresiones naturales de hora temprana
        frases_temprano = [
            "primera hora", "a primera hora", "lo mas temprano", "lo más temprano",
            "mas temprano posible", "más temprano posible", "temprano", "bien temprano",
            "primera hora disponible", "lo antes posible", "cuando antes"
        ]
        
        if any(frase in texto_usuario for frase in frases_temprano):
            logger.info(f"🔍 DEBUG: Detectada frase temprana, asignando 07:00")
            bot_response = "Perfecto, te agendo a primera hora disponible (07:00) 🌅"
            dispatcher.utter_message(text=bot_response)
            log_interaction_improved(tracker, bot_response, {"hora_automatica": "07:00", "tipo": "temprano"})
            return {"hora": "07:00"}
        
        # ✅ NUEVA: Detección de solo números (ej: "8", "14")
        match_solo_numero = re.search(r'\b([7-9]|1[0-5])\b', texto_usuario)
        if match_solo_numero and len(texto_usuario) < 5:  # "8" o "14" solamente
            hora_detectada = int(match_solo_numero.group(1))
            if 7 <= hora_detectada <= 15 and hora_detectada != 11:
                hora_formateada = f"{hora_detectada:02d}:00"
                logger.info(f"🔍 DEBUG: Número detectado: {hora_detectada} → {hora_formateada}")
                return {"hora": hora_formateada}
        
        # ✅ DETECTAR FRASES AMBIGUAS (listar horarios)
        if es_frase_ambigua(texto_usuario):
            logger.info(f"🔍 DEBUG: Frase ambigua detectada: '{texto_usuario}'")
            
            try:
                fecha_slot = tracker.get_slot("fecha")
                if fecha_slot:
                    try:
                        fecha_base = datetime.datetime.fromisoformat(fecha_slot).date()
                    except:
                        fecha_base = datetime.date.today()
                else:
                    fecha_base = datetime.date.today()
                
                with get_db_session() as session:
                    horarios_libres = obtener_horarios_disponibles_reales(fecha_base, session, limite=40)
                    
                    if not horarios_libres:
                        dispatcher.utter_message(
                            text=f"⚠️ Para {format_fecha_es(fecha_base, True)} no hay horarios libres."
                        )
                        return {"hora": None}
                    
                    # Agrupar por franjas
                    tempr = [h for h in horarios_libres if 7 <= int(h.split(':')[0]) < 9]
                    mana  = [h for h in horarios_libres if 9 <= int(h.split(':')[0]) < 11]
                    tarde = [h for h in horarios_libres if 12 <= int(h.split(':')[0]) < 15]
                    
                    def preview(arr): 
                        return ", ".join(arr[:6]) + (f" (+{len(arr)-6} más)" if len(arr) > 6 else "")
                    
                    msg = f"📅 **Horarios disponibles para {format_fecha_es(fecha_base, True)}**\n\n"
                    if tempr: msg += f"🟢 Temprano (07:00-09:00): {preview(tempr)}\n"
                    if mana:  msg += f"🟡 Mañana (09:00-11:00): {preview(mana)}\n"
                    if tarde: msg += f"🟢 Tarde (12:00-15:00): {preview(tarde)}\n"
                    
                    msg += "\n💡 **Tip:** Si querés el más temprano, decí '07:00' o 'a primera hora'"
                    msg += "\n\n✍️ Escribí la hora exacta que preferís (ej: '07:15' o '2 de la tarde')."
                    
                    dispatcher.utter_message(text=msg)
                    log_interaction_improved(tracker, msg, {"horarios_disponibles_mostrados": True, "total_horarios": len(horarios_libres)})
                    return {"hora": None}
            
            except Exception as e:
                logger.error(f"❌ ERROR listando horarios: {e}")
                dispatcher.utter_message(
                    text="Indicá una hora concreta (p.ej., '08:00' o 'a primera hora')."
                )
                return {"hora": None}
        
        # ✅ Intentar parsear hora normal
        hora_normalizada = normalizar_hora(texto_usuario)
        if not hora_normalizada:
            dispatcher.utter_message(
                text="No pude entender la hora. Podés decir:\n"
                    "• '14:00', '2 de la tarde', '9am'\n"
                    "• 'a primera hora' (para 07:00)\n"
                    "• 'lo más temprano posible'"
            )
            return {"hora": None}
        
        # Validar horario laboral
        if not validar_horario_laboral(hora_normalizada):
            dispatcher.utter_message(
                text="Solo atendemos de 07:00 a 15:00 horas (cerrado 11:00 por almuerzo). "
                    "Elegí una hora dentro de este rango."
            )
            return {"hora": None}
        
        # ✅ Verificar disponibilidad
        with get_db_session() as session:
            fecha_slot = tracker.get_slot("fecha")
            if fecha_slot:
                try:
                    fecha = datetime.datetime.fromisoformat(fecha_slot).date()
                    fecha_hora = datetime.datetime.combine(fecha, hora_normalizada)
                    ocupados = session.query(Turno).filter(
                        Turno.fecha_hora == fecha_hora,
                        Turno.estado == 'activo'
                    ).count()
                    if ocupados >= 3:
                        dispatcher.utter_message(
                            text=f"⚠️ El horario {hora_normalizada.strftime('%H:%M')} ya está lleno. "
                                f"Probá otro horario disponible."
                        )
                        return {"hora": None}
                except Exception as e:
                    logger.error(f"Error validando ocupación: {e}")
        
        logger.info(f"🔍 DEBUG: Hora validada exitosamente: {hora_normalizada.strftime('%H:%M')}")
        log_interaction_improved(tracker, f"Hora validada: {hora_normalizada.strftime('%H:%M')}", {"validation_success": True, "field": "hora"})
        return {"hora": hora_normalizada.strftime("%H:%M")}


    def validate_email(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if not slot_value:
            return {"email": None}
        
        texto = slot_value.lower().strip()
        
        # Permitir saltar el email
        if texto in ['no', 'skip', 'omitir', 'no quiero', 'saltear', 'no gracias']:
            dispatcher.utter_message(
                text="Entendido, continuamos sin email."
            )
            return {"email": None}
        
        # Validar formato email básico
        patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(patron_email, slot_value):
            dispatcher.utter_message(
                text=f"Perfecto, te enviaremos la invitación a {slot_value}"
            )
            return {"email": slot_value}
        
        dispatcher.utter_message(
            text="El formato del email no es válido. Escribí un email válido o decí 'no' para continuar sin email."
        )
        return {"email": None}

# =====================================================
# ACCIONES PRINCIPALES CORREGIDAS
# =====================================================
# ✅ NUEVA ACCIÓN: Permite corregir solo un campo sin reiniciar todo
class ActionReiniciarCampo(Action):
    def name(self) -> Text:
        return "action_reiniciar_campo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        ultimo_mensaje = tracker.latest_message.get("text", "").lower()
        campo = detectar_correccion(ultimo_mensaje)
        
        if campo:
            mensaje = f"Entendido, vamos a corregir tu {campo}."
            dispatcher.utter_message(text=mensaje)
            log_interaction_improved(tracker, mensaje, {"accion": "reiniciar_campo", "campo": campo})
            return [SlotSet(campo, None), FollowupAction("turno_form")]
        else:
            mensaje = "Podés decir qué querés cambiar: nombre, cédula, fecha u hora."
            dispatcher.utter_message(text=mensaje)
            log_interaction_improved(tracker, mensaje, {"accion": "reiniciar_campo", "campo": "ninguno"})
            return []


class ActionConfirmarDatosTurno(Action):
    def name(self) -> Text:
        return "action_confirmar_datos_turno"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        nombre = tracker.get_slot("nombre")
        cedula = tracker.get_slot("cedula")
        fecha_slot = tracker.get_slot("fecha")
        hora_slot = tracker.get_slot("hora")
        email_slot = tracker.get_slot("email")
        
        # ✅ NUEVA: Detectar email en el mensaje actual
        ultimo_mensaje = tracker.latest_message.get("text", "")
        email_en_mensaje = extraer_email_del_texto(ultimo_mensaje)
        
        # Si hay email en el mensaje Y no hay email en slot, guardarlo
        if email_en_mensaje and not email_slot:
            logger.info(f"📧 Email detectado en mensaje: {email_en_mensaje}")
            return [
                SlotSet("email", email_en_mensaje),
                FollowupAction("action_guardar_turno")  # Guardar directamente
            ]
        
        if not all([nombre, fecha_slot, hora_slot]):
            dispatcher.utter_message(text="Faltan algunos datos. Vamos a completarlos.")
            return [FollowupAction("turno_form")]
        
        try:
            fecha = datetime.datetime.fromisoformat(fecha_slot).date()
            hora = datetime.datetime.strptime(hora_slot, "%H:%M").time()
            fecha_formateada = format_fecha_es(fecha, True)
            hora_formateada = hora.strftime("%H:%M")
        except:
            dispatcher.utter_message(text="Hubo un problema con la fecha u hora. Intentemos de nuevo.")
            return [FollowupAction("turno_form")]
        
        mensaje = "✅ **Resumen de tu turno:**\n\n"
        mensaje += f"👤 **Nombre:** {nombre}\n"
        
        if cedula == "PRIMERA_VEZ":
            mensaje += f"🆔 **Cédula:** Primera vez (recordá llevar partida de nacimiento)\n"
        else:
            mensaje += f"🆔 **Cédula:** {cedula}\n"
        
        mensaje += f"📅 **Fecha:** {fecha_formateada}\n"
        mensaje += f"🕐 **Hora:** {hora_formateada}\n\n"
        
        # ✅ NUEVA: Mensaje más claro sobre el email
        if email_slot:
            mensaje += f"📧 **Email:** {email_slot}\n\n"
            mensaje += "¿Está todo correcto? Decí **'confirmo'** para agendar."
        else:
            mensaje += "¿Está todo correcto? Podés:\n"
            mensaje += "• Decir **'confirmo'** para agendar sin email\n"
            mensaje += "• Escribir tu email para recibir invitación de Google Calendar"
        
        dispatcher.utter_message(text=mensaje)
        
        # Registrar interacción para aprendizaje con sistema mejorado
        log_interaction_improved(tracker, mensaje, {"accion": "confirmar_datos", "resultado": "datos_presentados", "tiene_email": bool(email_slot)})
        
        return []

class ActionGuardarTurno(Action):
    def name(self) -> Text:
        return "action_guardar_turno"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        start_time = time.time()
        nombre = tracker.get_slot("nombre")
        cedula = tracker.get_slot("cedula")
        fecha_slot = tracker.get_slot("fecha")
        hora_slot = tracker.get_slot("hora")
        email = tracker.get_slot("email")
        
        if not all([nombre, fecha_slot, hora_slot]):
            dispatcher.utter_message(text="Faltan datos para agendar el turno.")
            return []
        
        try:
            fecha = datetime.datetime.fromisoformat(fecha_slot).date()
            hora = datetime.datetime.strptime(hora_slot, "%H:%M").time()
            fecha_hora = datetime.datetime.combine(fecha, hora)
        except Exception as e:
            dispatcher.utter_message(text="Error procesando la fecha u hora.")
            logger.error(f"Error parseando fecha/hora: {e}")
            return []
        
        codigo = generar_codigo_unico()
        calendar_link = None
        
        try:
            with get_db_session() as session:
                # Verificar si ya existe un turno para esa fecha y cédula
                turno_existente = session.query(Turno).filter(
                    Turno.fecha_hora == fecha_hora,
                    Turno.cedula == cedula,
                    Turno.estado == 'activo'
                ).first()
                
                if turno_existente:
                    dispatcher.utter_message(
                        text="⚠️ Ya tenés un turno activo para esa fecha y hora. ¿Querés agendarlo en otro horario?"
                    )
                    return []
                
                turnos_mismo_horario = session.query(Turno).filter(
                    Turno.fecha_hora == fecha_hora,
                    Turno.estado == 'activo'
                ).count()
                
                if turnos_mismo_horario >= 3:
                    dispatcher.utter_message(
                        text="⚠️ Este horario ya tiene todos los cupos ocupados. Elegí otro horario disponible."
                    )
                    return []
                
                # Crear turno inicial sin event_id (todavía no se genera el evento)
                nuevo_turno = Turno(
                    nombre=nombre,
                    cedula=cedula if cedula != "PRIMERA_VEZ" else None,
                    fecha_hora=fecha_hora,
                    codigo=codigo,
                    email=email
                )
                
                session.add(nuevo_turno)
                session.flush()
                logger.info(f"✅ BD: Turno guardado - ID {nuevo_turno.id}, Código {codigo}")
                
                # Intentar crear evento en Google Calendar
                try:
                    logger.info(f"📅 CALENDAR: Creando evento (email: {email if email else 'sin email'})")
                    
                    exito_calendar, resultado = crear_evento_turno(
                        nombre=nombre,
                        cedula=cedula,
                        fecha_hora=fecha_hora,
                        codigo_turno=codigo,
                        email_usuario=email if email and email.lower() not in ['no', 'skip', 'omitir'] else None
                    )
                    
                    if exito_calendar:
                        calendar_link = resultado
                        nuevo_turno.event_id = resultado  # ✅ guardar ID del evento
                        session.commit()
                        logger.info(f"✅ CALENDAR: Evento creado - {calendar_link}")
                    else:
                        logger.warning(f"⚠️ CALENDAR: Fallo - {resultado}")
                
                except Exception as e:
                    logger.error(f"❌ CALENDAR: Error crítico - {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                # Mensaje final al usuario
                mensaje = f"✅ **¡Turno agendado exitosamente!**\n\n"
                mensaje += f"🎫 **Código de turno:** `{codigo}`\n"
                mensaje += f"👤 **Nombre:** {nombre}\n"
                
                if cedula == "PRIMERA_VEZ":
                    mensaje += f"🆔 **Tipo:** Primera cédula\n"
                else:
                    mensaje += f"🆔 **Cédula:** {cedula}\n"
                
                mensaje += f"📅 **Fecha:** {format_fecha_es(fecha, True)}\n"
                mensaje += f"🕐 **Hora:** {hora.strftime('%H:%M')}\n"
                mensaje += f"📍 **Lugar:** Av. Pioneros del Este, CDE\n"
                
                if calendar_link:
                    mensaje += f"\n📅 **Google Calendar:** {calendar_link}\n"
                    if email and email.lower() not in ['no', 'skip', 'omitir']:
                        mensaje += f"📧 **Invitación enviada a:** {email}\n"
                        mensaje += f"💡 **Tip:** Revisá tu correo y aceptá la invitación\n"
                else:
                    mensaje += f"\n💾 **Guardado en base de datos**\n"
                
                mensaje += f"\n⚠️ **Importante:** Llegá 15 min antes con tu código `{codigo}`"
                
                dispatcher.utter_message(text=mensaje)
                
                # Registrar interacción en el sistema de aprendizaje con datos enriquecidos
                response_time_ms = int((time.time() - start_time) * 1000)
                turno_data = {
                    "accion": "guardar_turno", 
                    "resultado": "exitoso",
                    "codigo_turno": codigo,
                    "tiene_email": bool(email),
                    "tiene_calendar": bool(calendar_link),
                    "response_time_ms": response_time_ms,
                    "cedula_tipo": "primera_vez" if cedula == "PRIMERA_VEZ" else "existente"
                }
                log_interaction_improved(tracker, mensaje, turno_data)
                
        except Exception as e:
            dispatcher.utter_message(text="❌ Error al guardar el turno. Por favor, intentá de nuevo.")
            logger.error(f"Error crítico: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        
        return [
            SlotSet("nombre", None),
            SlotSet("cedula", None),
            SlotSet("fecha", None),
            SlotSet("hora", None),
            SlotSet("email", None)
        ]


# ✅ ACTION CORREGIDO: Motor difuso mejorado con debug
class ActionRecomendarHorarioFuzzy(Action):
    def name(self) -> Text:
        return "action_recomendar_horario_fuzzy"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        start_time = time.time()
        logger.info("🔥 MOTOR DIFUSO: Iniciando análisis con BD REAL")
        
        fecha_slot = tracker.get_slot("fecha")
        if fecha_slot:
            try:
                fecha = datetime.datetime.fromisoformat(fecha_slot).date()
                logger.info(f"🔥 MOTOR DIFUSO: Fecha del slot: {fecha}")
            except:
                fecha = datetime.date.today() + datetime.timedelta(days=1)
                logger.info(f"🔥 MOTOR DIFUSO: Error parseando fecha, usando: {fecha}")
        else:
            fecha = datetime.date.today() + datetime.timedelta(days=1)
            logger.info(f"🔥 MOTOR DIFUSO: No hay fecha en slot, usando: {fecha}")
        
        try:
            with get_db_session() as session:
                logger.info(f"🔥 MOTOR DIFUSO: Conectado a BD, consultando disponibilidad")
                
                # CONSULTAR OCUPACIÓN REAL DE LA BD CON DEBUG
                ocupacion_franjas = consultar_disponibilidad_real(fecha, session)
                horarios_libres = obtener_horarios_disponibles_reales(fecha, session, 25)
                
                logger.info(f"🔥 MOTOR DIFUSO: Ocupación franjas: {ocupacion_franjas}")
                logger.info(f"🔥 MOTOR DIFUSO: Horarios libres: {len(horarios_libres)}")
                
                franjas_info = {
                    'temprano': ('07:00-09:00', (7, 9)),
                    'manana': ('09:00-11:00', (9, 11)),
                    'tarde': ('12:00-15:00', (12, 15))
                }
                
                # Calcular tiempo de espera con motor difuso
                recomendaciones_detalladas = {}
                for franja, porcentaje_ocupacion in ocupacion_franjas.items():
                    urgencia = 5  # Nivel medio
                    tiempo_espera = calcular_espera(porcentaje_ocupacion, urgencia)
                    
                    rango, horas = franjas_info[franja]
                    
                    # Obtener horarios disponibles de esta franja
                    horarios_franja = [h for h in horarios_libres if 
                                      horas[0] <= int(h.split(':')[0]) < horas[1]]
                    
                    recomendaciones_detalladas[franja] = {
                        'rango': rango,
                        'ocupacion': porcentaje_ocupacion,
                        'espera_estimada': tiempo_espera,
                        'horarios_disponibles': horarios_franja[:8]  # Más horarios
                    }
                    
                    logger.info(f"🔥 MOTOR DIFUSO: {franja} - {porcentaje_ocupacion}% ocupado, {tiempo_espera}min espera, {len(horarios_franja)} horarios")
                
                # Ordenar por mejor (menor ocupación y espera)
                franjas_ordenadas = sorted(
                    recomendaciones_detalladas.items(),
                    key=lambda x: (x[1]['ocupacion'], x[1]['espera_estimada'])
                )
                
                mensaje = f"🤖 **Motor Difuso - Análisis Inteligente para {format_fecha_es(fecha)}**\n\n"
                
                mejor_franja_nombre, mejor_franja_datos = franjas_ordenadas[0]
                mensaje += f"🏆 **Recomendación principal:** {mejor_franja_nombre.title()} ({mejor_franja_datos['rango']})\n"
                mensaje += f"📈 **Ocupación:** {mejor_franja_datos['ocupacion']:.0f}%\n"
                mensaje += f"⏱️ **Espera estimada:** {mejor_franja_datos['espera_estimada']:.0f} minutos\n"
                
                if mejor_franja_datos['horarios_disponibles']:
                    mensaje += f"🕐 **Horarios recomendados:** {', '.join(mejor_franja_datos['horarios_disponibles'])}\n\n"
                
                mensaje += "📊 **Análisis completo por franjas:**\n"
                for franja_nombre, datos in franjas_ordenadas:
                    emoji = "🟢" if datos['ocupacion'] < 50 else "🟡" if datos['ocupacion'] < 80 else "🔴"
                    mensaje += f"{emoji} **{franja_nombre.title()}** ({datos['rango']}): "
                    mensaje += f"{datos['ocupacion']:.0f}% ocupado, "
                    mensaje += f"espera {datos['espera_estimada']:.0f}min"
                    
                    if datos['horarios_disponibles']:
                        mensaje += f" | Disponibles: {', '.join(datos['horarios_disponibles'][:4])}"
                        if len(datos['horarios_disponibles']) > 4:
                            mensaje += f" (+{len(datos['horarios_disponibles'])-4} más)"
                    
                    mensaje += "\n"
                
                if not horarios_libres:
                    mensaje += "\n⚠️ **No hay horarios disponibles** para esta fecha. Probá con otra fecha."
                else:
                    mensaje += f"\n💡 **Total de horarios disponibles:** {len(horarios_libres)}"
                    mensaje += f"\n🎯 **Mi recomendación:** {mejor_franja_datos['horarios_disponibles'][0] if mejor_franja_datos['horarios_disponibles'] else 'Elegí otra fecha'}"
                
                mensaje += "\n\n¿Cuál horario preferís?"
                
                dispatcher.utter_message(text=mensaje)
                logger.info(f"🔥 MOTOR DIFUSO: Análisis completado y enviado al usuario")
                
                # Registrar interacción con datos enriquecidos
                response_time_ms = int((time.time() - start_time) * 1000)
                fuzzy_data = {
                    "accion": "motor_difuso",
                    "fecha_analizada": fecha.isoformat(),
                    "ocupacion_franjas": ocupacion_franjas,
                    "horarios_disponibles": len(horarios_libres),
                    "mejor_franja": mejor_franja_nombre,
                    "response_time_ms": response_time_ms
                }
                log_interaction_improved(tracker, mensaje, fuzzy_data)
                
                return []
                
        except Exception as e:
            logger.error(f"❌ ERROR CRÍTICO en motor difuso: {e}")
            import traceback
            logger.error(traceback.format_exc())
            dispatcher.utter_message(text="No pude consultar la disponibilidad inteligente en este momento. Intentá de nuevo o decime una hora específica.")
            return []

class ActionConsultarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_consultar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        logger.info("📊 DISPONIBILIDAD: Consultando próximos días")
        hoy = datetime.date.today()
        disponibilidad = []
        
        try:
            with get_db_session() as session:
                for i in range(1, 8):  # Próximos 7 días
                    fecha = hoy + datetime.timedelta(days=i)
                    if fecha.weekday() < 5:  # Solo días hábiles
                        ocupacion_franjas = consultar_disponibilidad_real(fecha, session)
                        ocupacion_promedio = sum(ocupacion_franjas.values()) / len(ocupacion_franjas)
                        
                        horarios_dia = obtener_horarios_disponibles_reales(fecha, session, 50)
                        
                        if ocupacion_promedio < 50:
                            estado, emoji = "Alta disponibilidad", "🟢"
                        elif ocupacion_promedio < 80:
                            estado, emoji = "Disponibilidad media", "🟡"
                        else:
                            estado, emoji = "Poca disponibilidad", "🔴"
                        
                        disponibilidad.append(
                            f"{emoji} { _DIAS_ES[fecha.weekday()] } {fecha.strftime('%d/%m')}: {estado} ({ocupacion_promedio:.0f}% ocupado) - {len(horarios_dia)} horarios libres"
                        )
                        
                        logger.info(f"📊 DISPONIBILIDAD: {fecha} - {ocupacion_promedio:.0f}% ocupado, {len(horarios_dia)} horarios")
                        
        except Exception as e:
            logger.error(f"❌ ERROR consultando disponibilidad: {e}")
            dispatcher.utter_message(text="No pude consultar la disponibilidad. Intentá de nuevo.")
            return []
        
        mensaje = "📊 **Disponibilidad próximos días (datos reales de BD):**\n\n"
        mensaje += "\n".join(disponibilidad)
        mensaje += "\n\n🕐 **Horario:** 7:00 - 15:00 (cada 15 min, máximo 3 personas por horario)\n🍽️ **Almuerzo:** 11:00 (cerrado)"
        mensaje += "\n\n¿Para qué fecha querés agendar? O decí 'recomendame' para análisis inteligente."
        
        dispatcher.utter_message(text=mensaje)
        
        # Registrar consulta para aprendizaje con sistema mejorado
        log_interaction_improved(tracker, mensaje, {"accion": "consultar_disponibilidad", "dias_consultados": len(disponibilidad)})
        
        return []

# ✅ RESTO DE LAS ACCIONES (sin cambios mayores)
class ActionTiempoEsperaActual(Action):
    def name(self) -> Text:
        return "action_tiempo_espera_actual"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ahora = datetime.datetime.now()
        hoy = ahora.date()
        hora_actual = ahora.hour
        
        try:
            with get_db_session() as session:
                # Consultar ocupación real de la hora actual
                ocupacion_actual = consultar_ocupacion_real_bd(hoy, hora_actual, hora_actual + 1, session)
                urgencia = 5
                tiempo_espera = calcular_espera(ocupacion_actual, urgencia)
                
                if ocupacion_actual < 40:
                    estado, emoji = "tranquila", "🟢"
                elif ocupacion_actual < 70:
                    estado, emoji = "moderada", "🟡"
                else:
                    estado, emoji = "ocupada", "🔴"
                
                mensaje = f"{emoji} **Estado actual de la oficina:** {estado}\n"
                mensaje += f"📊 **Nivel de ocupación REAL:** {ocupacion_actual:.0f}%\n"
                mensaje += f"⏱️ **Tiempo estimado de espera:** {tiempo_espera:.1f} minutos\n\n"
                
                if ocupacion_actual > 80:
                    mensaje += "💡 Te recomiendo agendar para otro horario si es posible."
                
                dispatcher.utter_message(text=mensaje)
                
                # Registrar consulta para aprendizaje con sistema mejorado
                log_interaction_improved(tracker, mensaje, {
                    "accion": "tiempo_espera_actual", 
                    "ocupacion": ocupacion_actual, 
                    "tiempo_espera_min": tiempo_espera
                })
        
        except Exception as e:
            logger.error(f"Error consultando estado actual: {e}")
            dispatcher.utter_message(text="No pude consultar el estado actual.")
        
        return []

class ActionCalcularSaturacion(Action):
    def name(self) -> Text:
        return "action_calcular_saturacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ahora = datetime.datetime.now()
        hoy = ahora.date()
        hora_actual = ahora.hour
        
        try:
            with get_db_session() as session:
                # Consultar ocupación real
                ocupacion_actual = consultar_ocupacion_real_bd(hoy, hora_actual, hora_actual + 1, session)
                
                if ocupacion_actual < 30:
                    estado, emoji, descripcion = "muy baja", "🟢", "La oficina está muy tranquila"
                elif ocupacion_actual < 50:
                    estado, emoji, descripcion = "baja", "🟢", "Poca gente esperando"
                elif ocupacion_actual < 70:
                    estado, emoji, descripcion = "media", "🟡", "Nivel normal de ocupación"
                elif ocupacion_actual < 85:
                    estado, emoji, descripcion = "alta", "🟠", "Bastante gente esperando"
                else:
                    estado, emoji, descripcion = "muy alta", "🔴", "La oficina está muy llena"
                
                mensaje = f"{emoji} **Saturación actual (BD real):** {estado}\n"
                mensaje += f"📊 **Porcentaje de ocupación:** {ocupacion_actual:.0f}%\n"
                mensaje += f"📝 **Estado:** {descripcion}"
                
                dispatcher.utter_message(text=mensaje)
                
                # Registrar consulta para aprendizaje con sistema mejorado
                log_interaction_improved(tracker, mensaje, {
                    "accion": "calcular_saturacion", 
                    "saturacion": estado, 
                    "ocupacion": ocupacion_actual
                })
        
        except Exception as e:
            logger.error(f"Error consultando saturación: {e}")
            dispatcher.utter_message(text="No pude consultar la saturación actual.")
        
        return []

class ActionConsultarTurnoExistente(Action):
    def name(self) -> Text:
        return "action_consultar_turno_existente"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        cedula = tracker.get_slot("cedula")
        
        if not cedula:
            dispatcher.utter_message(
                text="Para consultar tu turno, necesito tu número de cédula."
            )
            return []
        
        try:
            with get_db_session() as session:
                turno = session.query(Turno).filter(
                    Turno.cedula == cedula,
                    Turno.estado == 'activo',
                    Turno.fecha_hora >= datetime.datetime.now()
                ).order_by(Turno.fecha_hora).first()
                
                if turno:
                    mensaje = f"✅ **Tu turno activo:**\n\n"
                    mensaje += f"🎫 **Código:** `{turno.codigo}`\n"
                    mensaje += f"👤 **Nombre:** {turno.nombre}\n"
                    mensaje += f"📅 **Fecha:** {turno.fecha_hora.strftime('%d/%m/%Y')}\n"
                    mensaje += f"🕐 **Hora:** {turno.fecha_hora.strftime('%H:%M')}\n"
                    mensaje += f"📍 **Lugar:** Av. Pioneros del Este, CDE\n"
                    mensaje += f"\n⚠️ Recordá llegar 15 min antes con tu código `{turno.codigo}`"
                else:
                    mensaje = "No tenés ningún turno activo agendado. ¿Querés sacar uno?"
                
                dispatcher.utter_message(text=mensaje)
                
                # Registrar consulta para aprendizaje con sistema mejorado
                log_interaction_improved(tracker, mensaje, {
                    "accion": "consultar_turno_existente", 
                    "resultado": "encontrado" if turno else "no_encontrado"
                })
        
        except Exception as e:
            logger.error(f"Error consultando turno: {e}")
            dispatcher.utter_message(text="No pude consultar tu turno en este momento.")
        
        return []

class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:
        
        logger.info(f"🟢 Iniciando nueva sesión para: {tracker.sender_id}")
        
        # Registrar inicio de sesión para aprendizaje con sistema mejorado
        log_interaction_improved(tracker, "Nueva sesión iniciada", {"accion": "session_start"})
        
        return [
            SessionStarted(),
            # 🔹 Limpieza completa de slots
            SlotSet("nombre", None),
            SlotSet("cedula", None),
            SlotSet("fecha", None),
            SlotSet("hora", None),
            SlotSet("email", None),
            SlotSet("session_started_metadata", {
                "started_at": datetime.datetime.now().isoformat(),
                "sender_id": tracker.sender_id
            }),
            ActionExecuted("action_listen")
        ]
        
# ✅ NUEVA ACCIÓN: Fallback inteligente para confusiones o interrupciones
class ActionFallbackContexto(Action):
    def name(self) -> Text:
        return "action_fallback_contexto"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        ultimo = tracker.latest_message.get("text", "").lower()
        campo = detectar_correccion(ultimo)
        
        if campo:
            mensaje = f"Entendido, cambiamos tu {campo}."
            dispatcher.utter_message(text=mensaje)
            log_interaction_improved(tracker, mensaje, {"accion": "fallback_contexto", "campo": campo})
            return [SlotSet(campo, None), FollowupAction("turno_form")]
        
        mensaje = "Perdón, no entendí bien. Continuemos con tu turno."
        dispatcher.utter_message(text=mensaje)
        log_interaction_improved(tracker, mensaje, {"accion": "fallback_contexto", "campo": "ninguno"})
        return [FollowupAction("turno_form")]
    
class ActionGestionarCambioDatos(Action):
    def name(self) -> Text:
        return "action_gestionar_cambio_datos"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ultimo = tracker.latest_message.get("text", "").lower()
        campos_detectados = []

        # Detectar qué campos mencionó el usuario
        if "nombre" in ultimo:
            campos_detectados.append("nombre")
        if "cédula" in ultimo or "cedula" in ultimo:
            campos_detectados.append("cedula")
        if "fecha" in ultimo or "día" in ultimo or "dia" in ultimo:
            campos_detectados.append("fecha")
        if "hora" in ultimo:
            campos_detectados.append("hora")

        # Si no menciona campos, preguntar cuáles quiere cambiar
        if not campos_detectados:
            dispatcher.utter_message(
                text="Por supuesto 😊 ¿qué querés cambiar? Podés decir por ejemplo: 'fecha', 'hora', 'nombre' o 'cédula'."
            )
            return [SlotSet("paso_formulario", "confirmacion")]

        # Si menciona uno o varios campos
        dispatcher.utter_message(
            text=f"Entendido 👍 Vamos a corregir {', '.join(campos_detectados)}. Escribí los nuevos valores:"
        )

        # Limpiar solo los slots mencionados
        eventos = [SlotSet(c, None) for c in campos_detectados]
        eventos.append(FollowupAction("turno_form"))
        return eventos
    
def log_interaction_improved(tracker, bot_response, additional_data=None):
    """
    Función auxiliar MEJORADA para registrar interacciones con captura de contexto
    """
    try:
        improved_logger = get_improved_conversation_logger()
        if improved_logger:
            # Preparar datos LLM si están disponibles
            llm_classification = additional_data if additional_data else {}
            
            # Registrar mensaje normal
            message_id = log_rasa_interaction_improved(improved_logger, tracker, bot_response, llm_classification)
            
            # NUEVA: Detectar situaciones problemáticas y capturar contexto
            session_id = getattr(tracker, 'sender_id', 'unknown')
            last_user_message = ""
            intent_detected = ""
            confidence = 0.0
            
            # Extraer último mensaje del usuario
            events = getattr(tracker, 'events', [])
            for event in reversed(events):
                if hasattr(event, 'type') and event.type == 'user':
                    if hasattr(event, 'text') and event.text:
                        last_user_message = event.text
                    if hasattr(event, 'parse_data') and event.parse_data:
                        intent_data = event.parse_data.get('intent', {})
                        intent_detected = intent_data.get('name', '')
                        confidence = intent_data.get('confidence', 0.0)
                    break
            
            # Capturar contexto si es problemático
            should_capture = False
            feedback_type = None
            
            # Caso 1: Intent es fallback
            if intent_detected == 'nlu_fallback':
                should_capture = True
                feedback_type = 'fallback'
            
            # Caso 2: Confianza baja
            elif confidence < 0.7:
                should_capture = True
                feedback_type = 'low_confidence'
            
            # Caso 3: Respuesta contiene errores o no entendimientos
            if any(phrase in bot_response.lower() for phrase in [
                'no entendí', 'no pude entender', 'no comprendo', 
                'disculpa', 'error', 'intenta de nuevo', 'reformular'
            ]):
                should_capture = True
                if not feedback_type:
                    feedback_type = 'misunderstanding'
            
            if should_capture:
                context_id = improved_logger.capture_conversation_context(
                    session_id=session_id,
                    problematic_message=last_user_message,
                    bot_response=bot_response,
                    intent_detected=intent_detected,
                    confidence=confidence,
                    feedback_type=feedback_type
                )
                logger.info(f"🔍 Contexto problemático capturado: ID {context_id}")
            
            # Actualizar estadísticas de eficiencia
            improved_logger.update_model_efficiency_stats()
            
    except Exception as e:
        logger.error(f"❌ Error en logging mejorado: {e}")
    
class ActionCaptureFeedbackContext(Action):
    def name(self) -> Text:
        return "action_capture_feedback_context"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """Captura contexto cuando el usuario da feedback negativo"""
        
        try:
            improved_logger = get_improved_conversation_logger()
            if not improved_logger:
                return []
            
            session_id = tracker.sender_id
            
            # Extraer último intercambio
            events = tracker.events
            last_user_message = ""
            last_bot_response = ""
            intent_detected = ""
            confidence = 0.0
            
            # Buscar los últimos mensajes
            for event in reversed(events):
                if hasattr(event, 'type'):
                    if event.type == 'user' and hasattr(event, 'text'):
                        if not last_user_message:
                            last_user_message = event.text
                        if hasattr(event, 'parse_data') and event.parse_data:
                            intent_data = event.parse_data.get('intent', {})
                            intent_detected = intent_data.get('name', '')
                            confidence = intent_data.get('confidence', 0.0)
                    elif event.type == 'bot' and hasattr(event, 'text'):
                        if not last_bot_response:
                            last_bot_response = event.text
                
                if last_user_message and last_bot_response:
                    break
            
            # Capturar contexto para feedback negativo
            if last_user_message and last_bot_response:
                context_id = improved_logger.capture_conversation_context(
                    session_id=session_id,
                    problematic_message=last_user_message,
                    bot_response=last_bot_response,
                    intent_detected=intent_detected,
                    confidence=confidence,
                    feedback_type='thumbs_down'
                )
                
                logger.info(f"👎 Feedback negativo con contexto capturado: ID {context_id}")
                
                mensaje = "Gracias por tu feedback. Lo usaremos para mejorar mis respuestas."
                dispatcher.utter_message(text=mensaje)
                log_interaction_improved(tracker, mensaje, {"accion": "capture_feedback"})
            
        except Exception as e:
            logger.error(f"❌ Error capturando contexto de feedback: {e}")
        
        return []
    
# =====================================================
# NUEVA ACCIÓN: Confirmar primera vez y continuar el formulario
# =====================================================
class ActionConfirmarPrimeraVez(Action):
    def name(self) -> Text:
        return "action_confirmar_primera_vez"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        bot_response = (
            "Perfecto 👍 entonces es tu primera cédula. "
            "Recordá llevar tu partida de nacimiento original y comprobante de pago. "
            "Continuemos con el agendamiento."
        )
        dispatcher.utter_message(text=bot_response)
        log_interaction_improved(tracker, bot_response, {"accion": "confirmar_primera_vez"})
        return [SlotSet("cedula", "PRIMERA_VEZ"), FollowupAction("turno_form")]


class ActionGuardarCorreccion(Action):
    def name(self) -> Text:
        return "action_guardar_correccion"

    def run(self, dispatcher, tracker, domain):
        ultimo_mensaje = tracker.latest_message.get("text", "")
        if "deberías responderme" in ultimo_mensaje.lower():
            try:
                match = re.search(r"deberías responderme\s*(.*)", ultimo_mensaje, re.IGNORECASE)
                if match:
                    corrected_text = match.group(1).strip()
                    last_bot = None
                    for e in reversed(tracker.events):
                        if e.get("event") == "bot" and e.get("text"):
                            last_bot = e["text"]
                            break
                    if last_bot and corrected_text:
                        save_user_correction(tracker.sender_id, tracker.latest_message.get("text"), last_bot, corrected_text)
                        dispatcher.utter_message(text="Gracias, guardaré esta corrección para mejorar mis respuestas 🤖")
                        return []
            except Exception as e:
                logger.error(f"Error guardando corrección: {e}")
        dispatcher.utter_message(text="No entendí la corrección. Podés decir: 'deberías responderme ...'")
        return []
