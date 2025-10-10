from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, SessionStarted, EventType, FollowupAction, ActionExecuted
from rasa_sdk.forms import FormValidationAction
from calendar_utils import crear_evento_turno, consultar_disponibilidad
from sqlalchemy import create_engine, Column, String, Integer, DateTime, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, sessionmaker
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

# Sistema de aprendizaje
try:
    from conversation_logger import setup_learning_system, log_rasa_interaction
    LEARNING_AVAILABLE = True
    logger.info("✅ Sistema de aprendizaje cargado exitosamente")
except ImportError as e:
    logger.warning(f"❌ Sistema de aprendizaje no disponible: {e}")
    LEARNING_AVAILABLE = False
    def log_rasa_interaction(*args, **kwargs):
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
conversation_logger = None
if LEARNING_AVAILABLE:
    try:
        conversation_logger = setup_learning_system(DATABASE_URL)
        logger.info("✅ Sistema de aprendizaje inicializado correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema de aprendizaje: {e}")
        conversation_logger = None

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
    """Context manager para manejo seguro de sesiones de BD"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error en sesión de BD: {e}")
        raise
    finally:
        session.close()

def generar_codigo_unico(longitud=6):
    """Genera un código único alfanumérico"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=longitud))

def normalizar_fecha(texto: str) -> Optional[datetime.date]:
    """Convierte texto natural a fecha"""
    if not texto:
        return None
    
    settings = {
        'PREFER_DATES_FROM': 'future',
        'RELATIVE_BASE': datetime.datetime.now(),
        'DATE_ORDER': 'DMY',
        'TIMEZONE': 'America/Asuncion'
    }
    
    try:
        fecha_parseada = dateparser.parse(
            texto.lower(),
            languages=['es'],
            settings=settings
        )
        
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

def consultar_ocupacion_real_bd(fecha: datetime.date, hora_inicio: int, hora_fin: int, session) -> float:
    """
    Consulta la ocupación REAL de la base de datos para un rango de horas
    Retorna el porcentaje de ocupación (0-100)
    """
    inicio = datetime.datetime.combine(fecha, datetime.time(hora_inicio, 0))
    fin = datetime.datetime.combine(fecha, datetime.time(hora_fin, 0))
    
    # Contar turnos ocupados en la BD
    turnos_ocupados = session.query(Turno).filter(
        Turno.fecha_hora >= inicio,
        Turno.fecha_hora < fin,
        Turno.estado == 'activo'
    ).count()
    
    # Calcular slots totales considerando 3 mesas simultáneas
    horas_en_rango = hora_fin - hora_inicio
    slots_por_hora = 4  # Cada 15 minutos: :00, :15, :30, :45
    mesas_simultaneas = 3  # 3 personas atendidas al mismo tiempo
    slots_totales = horas_en_rango * slots_por_hora * mesas_simultaneas
    
    if slots_totales == 0:
        return 0.0
    
    porcentaje_ocupacion = (turnos_ocupados / slots_totales) * 100
    return round(porcentaje_ocupacion, 1)

def consultar_disponibilidad_real(fecha: datetime.date, session) -> Dict[str, int]:
    """Consulta disponibilidad real desde BD por franjas horarias"""
    ocupacion_franjas = {}
    
    franjas_config = {
        'temprano': (7, 9),    # 7:00-9:00
        'manana': (9, 11),     # 9:00-11:00 (antes de almuerzo)
        'tarde': (12, 15)      # 12:00-15:00 (después de almuerzo)
    }
    
    for franja, (hora_inicio, hora_fin) in franjas_config.items():
        ocupacion = consultar_ocupacion_real_bd(fecha, hora_inicio, hora_fin, session)
        ocupacion_franjas[franja] = int(ocupacion)
    
    return ocupacion_franjas

def obtener_horarios_disponibles_reales(fecha: datetime.date, session, limite: int = 10) -> List[str]:
    """
    Obtiene horarios REALMENTE disponibles de la BD
    Retorna lista de horarios en formato HH:MM
    """
    horarios_disponibles = []
    
    # Generar todos los horarios posibles (7:00-15:00, cada 15 min, excepto 11:00)
    for hora in range(7, 15):
        if hora == 11:  # Saltar hora de almuerzo
            continue
        
        for minuto in [0, 15, 30, 45]:
            hora_dt = datetime.time(hora, minuto)
            fecha_hora = datetime.datetime.combine(fecha, hora_dt)
            
            # Contar turnos en este horario (máximo 3 simultáneos)
            turnos_en_horario = session.query(Turno).filter(
                Turno.fecha_hora == fecha_hora,
                Turno.estado == 'activo'
            ).count()
            
            # Si hay menos de 3 turnos, hay disponibilidad
            if turnos_en_horario < 3:
                horarios_disponibles.append(f"{hora:02d}:{minuto:02d}")
                
                if len(horarios_disponibles) >= limite:
                    return horarios_disponibles
    
    return horarios_disponibles

# ✅ CORREGIDO: Detectar frases ambiguas ANTES de procesarlas
def es_frase_ambigua(texto: str) -> bool:
    """
    Detecta si el texto contiene frases ambiguas que requieren lógica difusa
    """
    if not texto:
        return False
    
    texto_lower = texto.lower().strip()
    
    # Frases para FECHA ambigua
    frases_fecha_ambigua = [
        "lo antes posible",
        "lo más rápido",
        "cuando antes",
        "cuanto antes",
        "urgente",
        "primer turno",
        "primera fecha",
        "el primer día",
        "cuando tengas",
        "cuando haya",
        "lo que tengas",
    ]
    
    # Frases para HORA ambigua
    frases_hora_ambigua = [
        "cuando haya menos gente",
        "cuando esté tranquilo",
        "el mejor horario",
        "recomendame",
        "recomiendame",
        "sugerime",
        "que horario",
        "horario libre",
        "cuando convenga",
        "lo mas temprano",
        "lo más temprano",
        "lo mas tarde",
        "lo más tarde",
        "a la mañana",
        "a la tarde",
        "temprano",
        "cualquier horario",
    ]
    
    todas_frases = frases_fecha_ambigua + frases_hora_ambigua
    
    return any(frase in texto_lower for frase in todas_frases)

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
        if not slot_value or len(slot_value.strip()) < 3:
            dispatcher.utter_message(text="Por favor, proporcioná tu nombre completo (mínimo 3 caracteres).")
            return {"nombre": None}
        
        partes = slot_value.strip().split()
        if len(partes) < 2:
            dispatcher.utter_message(text="Necesito tu nombre completo (nombre y apellido).")
            return {"nombre": None}
        
        return {"nombre": slot_value.strip().title()}

    def validate_cedula(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if not slot_value:
            return {"cedula": None}
        
        texto = slot_value.lower().strip()
        
        frases_primera_vez = ["primera vez", "no tengo", "nunca tuve", "primera", "no tengo cedula"]
        if any(frase in texto for frase in frases_primera_vez):
            dispatcher.utter_message(
                text="Entendido, es tu primera cédula. Recordá que necesitarás partida de nacimiento original."
            )
            return {"cedula": "PRIMERA_VEZ"}
        
        cedula_limpia = re.sub(r'[^\d]', '', texto)
        if cedula_limpia and 1 <= len(cedula_limpia) <= 8:
            return {"cedula": cedula_limpia}
        
        dispatcher.utter_message(
            text="La cédula debe tener entre 1 y 8 dígitos, o decime si es tu primera vez."
        )
        return {"cedula": None}

    # ✅ CORREGIDO: validate_fecha ahora detecta frases ambiguas
    def validate_fecha(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if not slot_value:
            return {"fecha": None}
        
        texto_usuario = str(slot_value).strip()
        
        # ✅ NUEVO: Detectar frases ambiguas para FECHA
        if es_frase_ambigua(texto_usuario):
            logger.info(f"Frase ambigua detectada en fecha: '{texto_usuario}'")
            
            try:
                with get_db_session() as session:
                    # Buscar primer día disponible
                    dias_futuros = []
                    for i in range(1, 8):  # Próximos 7 días
                        fecha_futura = datetime.date.today() + datetime.timedelta(days=i)
                        if fecha_futura.weekday() < 5:  # Solo días hábiles
                            ocupacion_franjas = consultar_disponibilidad_real(fecha_futura, session)
                            ocupacion_promedio = sum(ocupacion_franjas.values()) / len(ocupacion_franjas)
                            
                            dias_futuros.append({
                                'fecha': fecha_futura,
                                'ocupacion': ocupacion_promedio,
                                'dia_nombre': fecha_futura.strftime('%A %d/%m')
                            })
                    
                    # Ordenar por menor ocupación
                    dias_ordenados = sorted(dias_futuros, key=lambda x: x['ocupacion'])
                    
                    mensaje = "📅 **Fechas recomendadas (menor ocupación):**\n\n"
                    for i, dia in enumerate(dias_ordenados[:5], 1):
                        emoji = "🟢" if dia['ocupacion'] < 50 else "🟡" if dia['ocupacion'] < 80 else "🔴"
                        mensaje += f"{i}. {emoji} {dia['dia_nombre']}: {dia['ocupacion']:.0f}% ocupado\n"
                    
                    mensaje += "\n💡 Te recomiendo: " + dias_ordenados[0]['dia_nombre']
                    mensaje += "\n\nDecime para qué fecha querés (ej: 'mañana', 'viernes', '15 de octubre')"
                    
                    dispatcher.utter_message(text=mensaje)
                    return {"fecha": None}
                    
            except Exception as e:
                logger.error(f"Error consultando fechas disponibles: {e}")
                dispatcher.utter_message(
                    text="Podés agendar de lunes a viernes. ¿Para qué fecha necesitás el turno?"
                )
                return {"fecha": None}
        
        # ✅ Intentar parsear fecha normal
        fecha_normalizada = normalizar_fecha(texto_usuario)
        if not fecha_normalizada:
            dispatcher.utter_message(
                text="No pude entender la fecha. Podés decir 'mañana', 'lunes 25', '15 de octubre', etc."
            )
            return {"fecha": None}
        
        hoy = datetime.date.today()
        if fecha_normalizada < hoy:
            dispatcher.utter_message(
                text="La fecha debe ser de hoy en adelante. ¿Para qué fecha necesitás el turno?"
            )
            return {"fecha": None}
        
        if (fecha_normalizada - hoy).days > 30:
            dispatcher.utter_message(
                text="Solo podemos agendar turnos hasta 30 días adelante. Elegí una fecha más cercana."
            )
            return {"fecha": None}
        
        if fecha_normalizada.weekday() > 4:
            dispatcher.utter_message(
                text="Solo atendemos de lunes a viernes. Elegí un día hábil."
            )
            return {"fecha": None}
        
        dispatcher.utter_message(
            text=f"Perfecto, registré la fecha para el {fecha_normalizada.strftime('%A %d de %B de %Y')}."
        )
        return {"fecha": fecha_normalizada.isoformat()}

    # ✅ CORREGIDO: validate_hora mejorado
    def validate_hora(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if not slot_value:
            return {"hora": None}
        
        texto_usuario = str(slot_value).strip()
        
        # ✅ MEJOR DETECCIÓN: Usar función centralizada
        if es_frase_ambigua(texto_usuario):
            logger.info(f"Frase ambigua detectada en hora: '{texto_usuario}' - Consultando BD real")
            
            try:
                fecha_slot = tracker.get_slot("fecha")
                if fecha_slot:
                    try:
                        fecha = datetime.datetime.fromisoformat(fecha_slot).date()
                    except:
                        fecha = datetime.date.today() + datetime.timedelta(days=1)
                else:
                    fecha = datetime.date.today() + datetime.timedelta(days=1)
                
                # CONSULTAR BD REAL
                with get_db_session() as session:
                    ocupacion_franjas = consultar_disponibilidad_real(fecha, session)
                    horarios_libres = obtener_horarios_disponibles_reales(fecha, session, 15)
                    
                    franjas_info = {
                        'temprano': '07:00-09:00',
                        'manana': '09:00-11:00',
                        'tarde': '12:00-15:00'
                    }
                    
                    # ✅ CORREGIDO: Mensaje coherente sin contradicciones
                    mensaje = f"📊 **Disponibilidad para {fecha.strftime('%A %d de %B')}**\n\n"
                    
                    # Ordenar franjas por ocupación
                    franjas_ordenadas = sorted(ocupacion_franjas.items(), key=lambda x: x[1])
                    
                    for franja, porcentaje in franjas_ordenadas:
                        rango = franjas_info[franja]
                        emoji = "🟢" if porcentaje < 50 else "🟡" if porcentaje < 80 else "🔴"
                        
                        if porcentaje < 50:
                            estado = "Alta disponibilidad ✅"
                        elif porcentaje < 80:
                            estado = "Disponibilidad media"
                        else:
                            estado = "Poca disponibilidad"
                        
                        mensaje += f"{emoji} **{franja.title()}** ({rango}): {porcentaje}% ocupado - {estado}\n"
                    
                    mejor_franja, mejor_ocupacion = franjas_ordenadas[0]
                    mensaje += f"\n🏆 **Mejor opción:** {mejor_franja.title()} ({franjas_info[mejor_franja]})\n"
                    
                    # ✅ CORREGIDO: Solo mostrar horarios si HAY disponibilidad
                    if horarios_libres:
                        mensaje += f"\n🕐 **Horarios disponibles:** {', '.join(horarios_libres[:8])}\n"
                        mensaje += f"\n💡 Total de horarios libres: {len(horarios_libres)}"
                        mensaje += "\n\n¿Qué hora preferís? (ej: 08:00, 10:30, 14:00)"
                    else:
                        mensaje += "\n\n⚠️ **No hay horarios disponibles para esta fecha.**"
                        mensaje += "\nProbá con otra fecha o elegí otro día."
                    
                    dispatcher.utter_message(text=mensaje)
                    logger.info(f"Recomendación: {mejor_franja} con {mejor_ocupacion}% ocupación")
                    
                    return {"hora": None}
                    
            except Exception as e:
                logger.error(f"Error consultando BD: {e}")
                dispatcher.utter_message(
                    text="Atendemos de 07:00 a 15:00 (cerrado 11:00). ¿Qué hora preferís?"
                )
                return {"hora": None}
        
        # ✅ Intentar parsear hora normal
        hora_normalizada = normalizar_hora(texto_usuario)
        if not hora_normalizada:
            dispatcher.utter_message(
                text="No pude entender la hora. Podés decir '14:00', '2 de la tarde', '9am', etc.\n\n"
                     "💡 Si querés recomendaciones, decí 'recomendame un horario'."
            )
            return {"hora": None}
        
        if not validar_horario_laboral(hora_normalizada):
            dispatcher.utter_message(
                text="Solo atendemos de 07:00 a 15:00 horas (cerrado 11:00 por almuerzo). Elegí una hora dentro de este rango."
            )
            return {"hora": None}
        
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
# ACCIONES PRINCIPALES
# =====================================================
class ActionConfirmarDatosTurno(Action):
    def name(self) -> Text:
        return "action_confirmar_datos_turno"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        nombre = tracker.get_slot("nombre")
        cedula = tracker.get_slot("cedula")
        fecha_slot = tracker.get_slot("fecha")
        hora_slot = tracker.get_slot("hora")
        
        if not all([nombre, fecha_slot, hora_slot]):
            dispatcher.utter_message(text="Faltan algunos datos. Vamos a completarlos.")
            return [FollowupAction("turno_form")]
        
        try:
            fecha = datetime.datetime.fromisoformat(fecha_slot).date()
            hora = datetime.datetime.strptime(hora_slot, "%H:%M").time()
            fecha_formateada = fecha.strftime("%A %d de %B de %Y")
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
        mensaje += "¿Está todo correcto? Decí **'confirmo'** para agendar.\n\n"
        mensaje += "📧 **Opcional:** Si querés recibir invitación de Google Calendar, escribí tu email. Si no, simplemente decí 'confirmo'."
        
        dispatcher.utter_message(text=mensaje)
        
        if conversation_logger:
            log_rasa_interaction(
                conversation_logger,
                tracker,
                "Confirmación de datos de turno mostrada"
            )
        
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
                
                nuevo_turno = Turno(
                    nombre=nombre,
                    cedula=cedula if cedula != "PRIMERA_VEZ" else None,
                    fecha_hora=fecha_hora,
                    codigo=codigo
                )
                
                session.add(nuevo_turno)
                session.flush()
                
                logger.info(f"✅ BD: Turno guardado - ID {nuevo_turno.id}, Código {codigo}")
                
                # INTEGRAR GOOGLE CALENDAR
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
                        logger.info(f"✅ CALENDAR: Evento creado - {calendar_link}")
                    else:
                        logger.warning(f"⚠️ CALENDAR: Fallo - {resultado}")
                
                except Exception as e:
                    logger.error(f"❌ CALENDAR: Error crítico - {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                
                mensaje = f"✅ **¡Turno agendado exitosamente!**\n\n"
                mensaje += f"🎫 **Código de turno:** `{codigo}`\n"
                mensaje += f"👤 **Nombre:** {nombre}\n"
                
                if cedula == "PRIMERA_VEZ":
                    mensaje += f"🆔 **Tipo:** Primera cédula\n"
                else:
                    mensaje += f"🆔 **Cédula:** {cedula}\n"
                
                mensaje += f"📅 **Fecha:** {fecha.strftime('%d/%m/%Y')}\n"
                mensaje += f"🕐 **Hora:** {hora.strftime('%H:%M')}\n"
                mensaje += f"📍 **Lugar:** Av. Pioneros del Este, CDE\n"
                
                if calendar_link:
                    mensaje += f"\n📅 **Google Calendar:** {calendar_link}\n"
                    if email and email.lower() not in ['no', 'skip', 'omitir']:
                        mensaje += f"📧 **Invitación enviada a:** {email}\n"
                        mensaje += f"💡 **Tip:** Revisa tu correo y acepta la invitación\n"
                else:
                    mensaje += f"\n💾 **Guardado en base de datos**\n"
                
                mensaje += f"\n⚠️ **Importante:** Llegá 15 min antes con tu código `{codigo}`"
                
                dispatcher.utter_message(text=mensaje)
                
                if conversation_logger:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        f"Turno {codigo} guardado (email: {'sí' if email else 'no'})",
                        response_time_ms
                    )
                
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

class ActionRecomendarHorarioFuzzy(Action):
    def name(self) -> Text:
        return "action_recomendar_horario_fuzzy"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        start_time = time.time()
        logger.info("🔥 Motor difuso CON BD REAL ejecutándose")
        
        fecha_slot = tracker.get_slot("fecha")
        if fecha_slot:
            try:
                fecha = datetime.datetime.fromisoformat(fecha_slot).date()
            except:
                fecha = datetime.date.today() + datetime.timedelta(days=1)
        else:
            fecha = datetime.date.today() + datetime.timedelta(days=1)
        
        try:
            with get_db_session() as session:
                # CONSULTAR OCUPACIÓN REAL DE LA BD
                ocupacion_franjas = consultar_disponibilidad_real(fecha, session)
                horarios_libres = obtener_horarios_disponibles_reales(fecha, session, 20)
                
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
                        'horarios_disponibles': horarios_franja[:5]
                    }
                
                # Ordenar por mejor (menor ocupación y espera)
                franjas_ordenadas = sorted(
                    recomendaciones_detalladas.items(),
                    key=lambda x: (x[1]['ocupacion'], x[1]['espera_estimada'])
                )
                
                mensaje = f"📊 **Análisis de disponibilidad REAL para {fecha.strftime('%A %d de %B')}**\n\n"
                
                mejor_franja_nombre, mejor_franja_datos = franjas_ordenadas[0]
                mensaje += f"🏆 **Mejor opción:** {mejor_franja_nombre.title()} ({mejor_franja_datos['rango']})\n"
                mensaje += f"📈 **Ocupación:** {mejor_franja_datos['ocupacion']:.0f}%\n"
                mensaje += f"⏱️ **Espera estimada:** {mejor_franja_datos['espera_estimada']:.0f} minutos\n"
                
                if mejor_franja_datos['horarios_disponibles']:
                    mensaje += f"🕐 **Horarios libres:** {', '.join(mejor_franja_datos['horarios_disponibles'])}\n\n"
                
                mensaje += "📋 **Todas las opciones:**\n"
                for franja_nombre, datos in franjas_ordenadas:
                    emoji = "🟢" if datos['ocupacion'] < 50 else "🟡" if datos['ocupacion'] < 80 else "🔴"
                    mensaje += f"{emoji} **{franja_nombre.title()}** ({datos['rango']}): "
                    mensaje += f"{datos['ocupacion']:.0f}% ocupado, "
                    mensaje += f"espera {datos['espera_estimada']:.0f}min\n"
                
                if not horarios_libres:
                    mensaje += "\n⚠️ **No hay horarios disponibles** para esta fecha. Probá con otra fecha."
                else:
                    mensaje += f"\n💡 Total de horarios libres: {len(horarios_libres)}"
                
                mensaje += "\n\n¿Cuál horario preferís?"
                
                dispatcher.utter_message(text=mensaje)
                logger.info(f"✅ Recomendación basada en BD real completada")
                
                if conversation_logger:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        "Motor difuso con BD real - análisis completado",
                        response_time_ms
                    )
                
                return []
                
        except Exception as e:
            logger.error(f"❌ Error consultando BD en motor difuso: {e}")
            dispatcher.utter_message(text="No pude consultar la disponibilidad en este momento. Intentá de nuevo.")
            return []

class ActionConsultarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_consultar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        hoy = datetime.date.today()
        disponibilidad = []
        
        try:
            with get_db_session() as session:
                for i in range(1, 6):
                    fecha = hoy + datetime.timedelta(days=i)
                    if fecha.weekday() < 5:  # Solo días hábiles
                        ocupacion_franjas = consultar_disponibilidad_real(fecha, session)
                        ocupacion_promedio = sum(ocupacion_franjas.values()) / len(ocupacion_franjas)
                        
                        if ocupacion_promedio < 50:
                            estado, emoji = "Alta disponibilidad", "🟢"
                        elif ocupacion_promedio < 80:
                            estado, emoji = "Disponibilidad media", "🟡"
                        else:
                            estado, emoji = "Poca disponibilidad", "🔴"
                        
                        disponibilidad.append(
                            f"{emoji} {fecha.strftime('%A %d/%m')}: {estado} ({ocupacion_promedio:.0f}% ocupado)"
                        )
        except Exception as e:
            logger.error(f"Error consultando disponibilidad: {e}")
            dispatcher.utter_message(text="No pude consultar la disponibilidad.")
            return []
        
        mensaje = "📊 **Disponibilidad próximos días (basado en BD real):**\n\n"
        mensaje += "\n".join(disponibilidad)
        mensaje += "\n\n🕐 **Horario:** 7:00 - 15:00\n🍽️ **Almuerzo:** 11:00 (cerrado)"
        mensaje += "\n\n¿Para qué fecha querés agendar?"
        
        dispatcher.utter_message(text=mensaje)
        if conversation_logger:
            log_rasa_interaction(conversation_logger, tracker, "Consulta disponibilidad real")
        return []

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
                
                if conversation_logger:
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        f"Consulta tiempo espera real: {tiempo_espera:.1f}min, ocupación: {ocupacion_actual}%"
                    )
        
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
                
                if conversation_logger:
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        f"Consulta saturación real: {estado} ({ocupacion_actual}%)"
                    )
        
        except Exception as e:
            logger.error(f"Error consultando saturación: {e}")
            dispatcher.utter_message(text="No pude consultar la saturación actual.")
        
        return []

# ✅ NUEVO: Action para consultar turno existente
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
                
                if conversation_logger:
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        f"Consulta turno - {'encontrado' if turno else 'no encontrado'}"
                    )
        
        except Exception as e:
            logger.error(f"Error consultando turno: {e}")
            dispatcher.utter_message(text="No pude consultar tu turno en este momento.")
        
        return []

# ✅ CORREGIDO: ActionSessionStart mejorado
class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:
        
        logger.info(f"🟢 Iniciando nueva sesión para: {tracker.sender_id}")
        
        if conversation_logger:
            try:
                log_rasa_interaction(
                    conversation_logger,
                    tracker,
                    "Nueva sesión iniciada"
                )
            except Exception as e:
                logger.error(f"Error logging inicio de sesión: {e}")
        
        # ✅ CORREGIDO: Enviar mensaje de bienvenida ANTES de los eventos
        dispatcher.utter_message(
            text="¡Hola! Soy tu asistente virtual para gestión de cédulas en Ciudad del Este. ¿En qué puedo ayudarte hoy?"
        )
        
        # ✅ IMPORTANTE: Retornar eventos en el orden correcto
        return [
            SessionStarted(),
            SlotSet("session_started_metadata", {
                "started_at": datetime.datetime.now().isoformat(),
                "sender_id": tracker.sender_id
            }),
            ActionExecuted("action_listen")
        ]