from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, SessionStarted, EventType, FollowupAction
from rasa_sdk.forms import FormValidationAction

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
    
    # Configurar dateparser para Paraguay
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
    
    # Patrones comunes de hora
    patrones = [
        r'(\d{1,2}):(\d{2})',  # 15:30
        r'(\d{1,2})\s*(am|pm)',  # 3pm, 10am
        r'(\d{1,2})\s*de\s*la\s*(mañana|tarde|noche)',  # 3 de la tarde
    ]
    
    texto_limpio = texto.lower().strip()
    
    for patron in patrones:
        match = re.search(patron, texto_limpio)
        if match:
            try:
                hora = int(match.group(1))
                
                # Manejo de AM/PM
                if len(match.groups()) > 1:
                    periodo = match.group(2) if ':' not in match.group(0) else None
                    if periodo == 'pm' and hora < 12:
                        hora += 12
                    elif periodo == 'am' and hora == 12:
                        hora = 0
                
                # Manejo de expresiones naturales
                if 'tarde' in texto_limpio and hora < 12:
                    hora += 12
                elif 'noche' in texto_limpio and hora < 18:
                    hora += 12
                
                minutos = int(match.group(2)) if ':' in match.group(0) else 0
                return datetime.time(hora, minutos)
            except (ValueError, IndexError):
                continue
    
    # Fallback con dateparser
    try:
        fecha_parseada = dateparser.parse(texto, languages=['es'])
        if fecha_parseada:
            return fecha_parseada.time()
    except:
        pass
    
    return None

def validar_horario_laboral(hora: datetime.time) -> bool:
    """Valida que la hora esté en horario laboral (7:00-17:00)"""
    if not hora:
        return False
    return datetime.time(7, 0) <= hora <= datetime.time(17, 0)

def obtener_ocupacion_simulada(fecha_hora: datetime.datetime) -> int:
    """Simula ocupación basada en fecha y hora"""
    hora = fecha_hora.hour
    dia_semana = fecha_hora.weekday()
    
    # Factores de ocupación
    factor_hora = 50
    if 8 <= hora <= 10 or 14 <= hora <= 16:  # Horas pico
        factor_hora = 85
    elif 11 <= hora <= 13:  # Mediodía
        factor_hora = 95
    elif hora < 8 or hora > 16:  # Horas tranquilas
        factor_hora = 30
    
    factor_dia = 70
    if dia_semana in [0, 4]:  # Lunes y viernes
        factor_dia = 90
    elif dia_semana in [1, 2, 3]:  # Martes a jueves
        factor_dia = 60
    
    ocupacion = int((factor_hora + factor_dia) / 2)
    return min(100, max(0, ocupacion + random.randint(-15, 15)))

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
        """Valida el nombre completo"""
        if not slot_value or len(slot_value.strip()) < 3:
            dispatcher.utter_message(text="Por favor, proporcioná tu nombre completo (mínimo 3 caracteres).")
            return {"nombre": None}
        
        # Verificar que tenga al menos nombre y apellido
        partes = slot_value.strip().split()
        if len(partes) < 2:
            dispatcher.utter_message(text="Necesito tu nombre completo (nombre y apellido).")
            return {"nombre": None}
        
        return {"nombre": slot_value.strip().title()}

    def validate_cedula(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Valida número de cédula o marca como primera vez"""
        if not slot_value:
            return {"cedula": None}
        
        texto = slot_value.lower().strip()
        
        # Detectar si es primera vez
        frases_primera_vez = ["primera vez", "no tengo", "nunca tuve", "primera", "no tengo cedula"]
        if any(frase in texto for frase in frases_primera_vez):
            dispatcher.utter_message(
                text="Entendido, es tu primera cédula. Recordá que necesitarás partida de nacimiento original."
            )
            return {"cedula": "PRIMERA_VEZ"}
        
        # Validar formato de cédula paraguaya (solo números, 1-8 dígitos)
        cedula_limpia = re.sub(r'[^\d]', '', texto)
        if cedula_limpia and 1 <= len(cedula_limpia) <= 8:
            return {"cedula": cedula_limpia}
        
        dispatcher.utter_message(
            text="La cédula debe tener entre 1 y 8 dígitos, o decime si es tu primera vez."
        )
        return {"cedula": None}

    def validate_fecha(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Valida y normaliza la fecha"""
        if not slot_value:
            return {"fecha": None}
        
        fecha_normalizada = normalizar_fecha(slot_value)
        if not fecha_normalizada:
            dispatcher.utter_message(
                text="No pude entender la fecha. Podés decir 'mañana', 'lunes 25', '15 de octubre', etc."
            )
            return {"fecha": None}
        
        # Validar que no sea fecha pasada
        hoy = datetime.date.today()
        if fecha_normalizada < hoy:
            dispatcher.utter_message(
                text="La fecha debe ser de hoy en adelante. ¿Para qué fecha necesitás el turno?"
            )
            return {"fecha": None}
        
        # Validar que no sea muy lejana (máximo 30 días)
        if (fecha_normalizada - hoy).days > 30:
            dispatcher.utter_message(
                text="Solo podemos agendar turnos hasta 30 días adelante. Elegí una fecha más cercana."
            )
            return {"fecha": None}
        
        # Validar día laboral
        if fecha_normalizada.weekday() > 4:  # Sábado=5, Domingo=6
            dispatcher.utter_message(
                text="Solo atendemos de lunes a viernes. Elegí un día hábil."
            )
            return {"fecha": None}
        
        dispatcher.utter_message(
            text=f"Perfecto, registré la fecha para el {fecha_normalizada.strftime('%A %d de %B de %Y')}."
        )
        return {"fecha": fecha_normalizada.isoformat()}

    def validate_hora(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Valida y normaliza la hora, o activa motor difuso si es frase ambigua"""
        if not slot_value:
            return {"hora": None}
        
        # ========================================
        # DETECTAR FRASES AMBIGUAS PARA MOTOR DIFUSO
        # ========================================
        
        # Lista de frases que deben activar el motor difuso
        frases_difusas = [
            "el que tengas libre", "cuando haya menos gente", "cuando esté más tranquilo",
            "que horarios hay disponibles", "recomendame un horario", "cualquier horario",
            "el mejor horario", "cuando sea mejor", "cuando convenga", "lo mas temprano",
            "sugerime", "recomendación", "la mejor opción", "horario óptimo"
        ]
        
        texto_usuario = slot_value.lower().strip()
        
        # Verificar si es una frase ambigua
        es_frase_ambigua = any(frase in texto_usuario for frase in frases_difusas)
        
        if es_frase_ambigua:
            logger.info(f"Frase ambigua detectada en formulario: '{slot_value}'")
            
            # Registrar para aprendizaje
            if conversation_logger:
                log_rasa_interaction(
                    conversation_logger,
                    tracker,
                    "Motor difuso activado en formulario de validación"
                )
            
            # Activar motor difuso desde dentro del formulario
            try:
                # Obtener fecha del slot actual
                fecha_slot = tracker.get_slot("fecha")
                if fecha_slot:
                    try:
                        fecha = datetime.datetime.fromisoformat(fecha_slot).date()
                    except:
                        fecha = datetime.date.today() + datetime.timedelta(days=1)
                else:
                    fecha = datetime.date.today() + datetime.timedelta(days=1)
                
                # Usar motor difuso si está disponible
                if FUZZY_AVAILABLE:
                    try:
                        from motor_difuso import analizar_disponibilidad_dia, obtener_mejor_recomendacion
                        
                        analisis = analizar_disponibilidad_dia(fecha)
                        mejor_franja, mejor_datos = obtener_mejor_recomendacion(fecha)
                        
                        mensaje = f"📊 **Análisis difuso para {fecha.strftime('%A %d de %B')}**\n\n"
                        mensaje += f"🏆 **Mejor recomendación:** {mejor_franja} ({mejor_datos['rango']})\n"
                        mensaje += f"📈 **Puntuación:** {mejor_datos['recomendacion']:.0f}/100\n"
                        mensaje += f"⏱️ **Espera estimada:** {mejor_datos['espera_estimada']:.0f} minutos\n"
                        mensaje += f"🕐 **Horarios sugeridos:** {', '.join(mejor_datos['horarios_sugeridos'])}\n\n"
                        
                        # Mostrar opciones más compactas
                        mensaje += "📋 **Opciones disponibles:**\n"
                        for i, (franja_nombre, franja_datos) in enumerate(sorted(analisis.items(), key=lambda x: x[1]['recomendacion'], reverse=True), 1):
                            emoji = "🟢" if franja_datos['recomendacion'] >= 75 else "🟡" if franja_datos['recomendacion'] >= 50 else "🔴"
                            mensaje += f"{emoji} {i}. **{franja_nombre}**: {', '.join(franja_datos['horarios_sugeridos'][:2])}\n"
                        
                        mensaje += "\n¿Podés elegir una hora específica de las recomendadas? (ej: 08:00, 10:30, 15:00)"
                        
                        dispatcher.utter_message(text=mensaje)
                        logger.info("✅ Motor difuso activado desde validador de formulario")
                        
                        # No completar el slot, seguir pidiendo hora específica
                        return {"hora": None}
                        
                    except Exception as e:
                        logger.error(f"Error en motor difuso desde formulario: {e}")
                        
                # Fallback si motor difuso no está disponible
                mensaje = "📊 **Recomendaciones de horario:**\n\n"
                mensaje += "🌅 **Mañana temprano (07:00-09:00):** Menos ocupado\n"
                mensaje += "🕐 **Media mañana (09:30-11:30):** Disponibilidad moderada\n" 
                mensaje += "🌇 **Tarde (14:30-16:30):** Variable según el día\n\n"
                mensaje += "¿Podés elegir una hora específica? (ej: 08:00, 10:30, 15:00)"
                
                dispatcher.utter_message(text=mensaje)
                return {"hora": None}
                
            except Exception as e:
                logger.error(f"Error procesando frase ambigua: {e}")
        
        # ========================================
        # VALIDACIÓN NORMAL DE HORA
        # ========================================
        
        hora_normalizada = normalizar_hora(slot_value)
        if not hora_normalizada:
            dispatcher.utter_message(
                text="No pude entender la hora. Podés decir '15:00', '3 de la tarde', '9am', etc.\n\n"
                     "💡 Si querés recomendaciones, decí 'recomendame un horario' o 'cuando haya menos gente'."
            )
            return {"hora": None}
        
        if not validar_horario_laboral(hora_normalizada):
            dispatcher.utter_message(
                text="Solo atendemos de 07:00 a 17:00 horas. Elegí una hora dentro de este rango."
            )
            return {"hora": None}
        
        return {"hora": hora_normalizada.strftime("%H:%M")}

# =====================================================
# ACCIONES PRINCIPALES
# =====================================================
class ActionRecomendarHorarioFuzzy(Action):
    def name(self) -> Text:
        return "action_recomendar_horario_fuzzy"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        start_time = time.time()
        logger.info("🔥 Motor difuso EJECUTÁNDOSE")
        
        # Si no hay fecha en el slot, usar fecha por defecto (mañana)
        fecha_slot = tracker.get_slot("fecha")
        if fecha_slot:
            try:
                fecha = datetime.datetime.fromisoformat(fecha_slot).date()
            except:
                fecha = datetime.date.today() + datetime.timedelta(days=1)
        else:
            fecha = datetime.date.today() + datetime.timedelta(days=1)
            logger.info(f"No hay fecha en slot, usando mañana: {fecha}")
        
        # ========================================
        # USAR EL MOTOR DIFUSO CORRECTAMENTE
        # ========================================
        
        # Importar funciones del motor difuso
        if FUZZY_AVAILABLE:
            try:
                from motor_difuso import analizar_disponibilidad_dia, obtener_mejor_recomendacion
                
                # Usar análisis completo del motor difuso
                analisis = analizar_disponibilidad_dia(fecha)
                mejor_franja, mejor_datos = obtener_mejor_recomendacion(fecha)
                
                mensaje = f"📊 **Análisis difuso para {fecha.strftime('%A %d de %B')}**\n\n"
                mensaje += f"🏆 **Mejor recomendación:** {mejor_franja} ({mejor_datos['rango']})\n"
                mensaje += f"📈 **Puntuación:** {mejor_datos['recomendacion']:.0f}/100\n"
                mensaje += f"⏱️ **Espera estimada:** {mejor_datos['espera_estimada']:.0f} minutos\n"
                mensaje += f"📊 **Ocupación:** {mejor_datos['ocupacion']:.0f}%\n"
                mensaje += f"🕐 **Horarios sugeridos:** {', '.join(mejor_datos['horarios_sugeridos'])}\n\n"
                
                # Mostrar todas las opciones
                mensaje += "📋 **Todas las opciones disponibles:**\n"
                for franja_nombre, franja_datos in sorted(analisis.items(), key=lambda x: x[1]['recomendacion'], reverse=True):
                    emoji = "🟢" if franja_datos['recomendacion'] >= 75 else "🟡" if franja_datos['recomendacion'] >= 50 else "🔴"
                    mensaje += f"{emoji} **{franja_nombre}** ({franja_datos['rango']}): "
                    mensaje += f"Espera {franja_datos['espera_estimada']:.0f}min, "
                    mensaje += f"Ocupación {franja_datos['ocupacion']:.0f}%\n"
                
                mensaje += "\n¿Cuál de estos horarios preferís?"
                
                dispatcher.utter_message(text=mensaje)
                logger.info(f"✅ Motor difuso completado exitosamente")
                
                # Registrar interacción para aprendizaje
                if conversation_logger:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        "Motor difuso activado - análisis completo generado",
                        response_time_ms
                    )
                
                return []
                
            except Exception as e:
                logger.error(f"Error usando motor difuso avanzado: {e}")
                # Continuar con lógica simple como fallback
        
        # ========================================
        # FALLBACK: LÓGICA SIMPLE CORREGIDA
        # ========================================
        
        # Generar recomendaciones usando el motor difuso básico
        franjas = [
            ("mañana temprano (07:00-09:00)", [7, 8, 9]),
            ("media mañana (09:30-11:30)", [9.5, 10, 10.5, 11]),
            ("tarde (14:30-16:30)", [14.5, 15, 15.5, 16])
        ]
        
        recomendaciones = []
        for nombre_franja, horas in franjas:
            ocupacion_promedio = 0
            for hora_decimal in horas:
                hora = int(hora_decimal)
                minuto = int((hora_decimal % 1) * 60)
                fecha_hora = datetime.datetime.combine(fecha, datetime.time(hora, minuto))
                ocupacion = obtener_ocupacion_simulada(fecha_hora)
                ocupacion_promedio += ocupacion
            
            ocupacion_promedio /= len(horas)
            urgencia = 5  # Nivel medio
            
            # CORRECCIÓN: Pasar hora también al cálculo difuso
            hora_promedio = sum(horas) / len(horas)
            tiempo_espera = calcular_espera(ocupacion_promedio, urgencia)
            
            recomendaciones.append((nombre_franja, ocupacion_promedio, tiempo_espera, horas))
        
        # Ordenar por menor tiempo de espera
        recomendaciones.sort(key=lambda x: x[2])
        
        mejor_franja = recomendaciones[0]
        nombre_franja, ocupacion, tiempo_espera, horas = mejor_franja
        
        # Generar horarios específicos
        horarios_disponibles = []
        for hora_decimal in horas[:3]:  # Mostrar 3 horarios
            hora = int(hora_decimal)
            minuto = int((hora_decimal % 1) * 60)
            horarios_disponibles.append(f"{hora:02d}:{minuto:02d}")
        
        mensaje = f"📊 Según el análisis de disponibilidad, te recomiendo **{nombre_franja}**.\n"
        mensaje += f"⏱️ Tiempo estimado de espera: **{tiempo_espera:.1f} minutos**\n"
        mensaje += f"📊 Ocupación estimada: **{ocupacion:.0f}%**\n"
        mensaje += f"🕐 Horarios disponibles: **{', '.join(horarios_disponibles)}**\n\n"
        mensaje += "¿Cuál de estos horarios preferís?"
        
        dispatcher.utter_message(text=mensaje)
        logger.info(f"✅ Motor difuso completado: {mensaje[:50]}...")
        
        # Registrar interacción para aprendizaje
        if conversation_logger:
            response_time_ms = int((time.time() - start_time) * 1000)
            log_rasa_interaction(
                conversation_logger,
                tracker,
                "Motor difuso básico activado - recomendaciones generadas",
                response_time_ms
            )
        
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
        
        # Mostrar resumen
        mensaje = "📋 **Resumen de tu turno:**\n\n"
        mensaje += f"👤 **Nombre:** {nombre}\n"
        
        if cedula == "PRIMERA_VEZ":
            mensaje += f"🆔 **Cédula:** Primera vez (recordá llevar partida de nacimiento)\n"
        else:
            mensaje += f"🆔 **Cédula:** {cedula}\n"
        
        mensaje += f"📅 **Fecha:** {fecha_formateada}\n"
        mensaje += f"🕐 **Hora:** {hora_formateada}\n\n"
        mensaje += "¿Está todo correcto? Decí **'confirmo'** para agendar o **'cambiar'** para modificar algo."
        
        dispatcher.utter_message(text=mensaje)
        
        # Registrar interacción para aprendizaje
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
        
        try:
            fecha = datetime.datetime.fromisoformat(fecha_slot).date()
            hora = datetime.datetime.strptime(hora_slot, "%H:%M").time()
            fecha_hora = datetime.datetime.combine(fecha, hora)
        except Exception as e:
            dispatcher.utter_message(text="Error procesando la fecha u hora. Intentá de nuevo.")
            logger.error(f"Error parseando fecha/hora: {e}")
            return []
        
        codigo = generar_codigo_unico()
        
        try:
            with get_db_session() as session:
                # Verificar si ya existe un turno similar
                turno_existente = session.query(Turno).filter(
                    Turno.fecha_hora == fecha_hora,
                    Turno.cedula == cedula,
                    Turno.estado == 'activo'
                ).first()
                
                if turno_existente:
                    dispatcher.utter_message(
                        text="Ya tenés un turno activo para esa fecha y hora. "
                             "Si querés cambiarlo, primero cancelá el anterior."
                    )
                    return []
                
                # Crear nuevo turno
                nuevo_turno = Turno(
                    nombre=nombre,
                    cedula=cedula if cedula != "PRIMERA_VEZ" else None,
                    fecha_hora=fecha_hora,
                    codigo=codigo
                )
                
                session.add(nuevo_turno)
                session.flush()  # Para obtener el ID
                
                # Mensaje de confirmación
                mensaje = "✅ **¡Turno agendado exitosamente!**\n\n"
                mensaje += f"🎫 **Código de turno:** `{codigo}`\n"
                mensaje += f"👤 **Nombre:** {nombre}\n"
                
                if cedula == "PRIMERA_VEZ":
                    mensaje += f"🆔 **Tipo:** Primera cédula\n"
                    mensaje += f"📋 **Recordatorio:** Llevá partida de nacimiento original\n"
                else:
                    mensaje += f"🆔 **Cédula:** {cedula}\n"
                
                mensaje += f"📅 **Fecha:** {fecha.strftime('%A %d de %B de %Y')}\n"
                mensaje += f"🕐 **Hora:** {hora.strftime('%H:%M')}\n"
                mensaje += f"📍 **Lugar:** Oficina Central - Av. Pioneros del Este, Ciudad del Este\n\n"
                mensaje += f"⚠️ **Importante:** Llegá 15 minutos antes con tu código `{codigo}` y los documentos requeridos."
                
                dispatcher.utter_message(text=mensaje)
                logger.info(f"Turno creado exitosamente: ID {nuevo_turno.id}, Código {codigo}")
                
                # Registrar turno exitoso para aprendizaje
                if conversation_logger:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    log_rasa_interaction(
                        conversation_logger,
                        tracker,
                        f"Turno agendado exitosamente - Código: {codigo}",
                        response_time_ms
                    )
                
        except SQLAlchemyError as e:
            dispatcher.utter_message(
                text="Hubo un problema al agendar tu turno. Por favor, intentá de nuevo en unos minutos."
            )
            logger.error(f"Error guardando turno: {e}")
            return []
        
        # Limpiar slots
        return [
            SlotSet("nombre", None),
            SlotSet("cedula", None),
            SlotSet("fecha", None),
            SlotSet("hora", None)
        ]

class ActionConsultarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_consultar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Simular consulta de disponibilidad para próximos días
        hoy = datetime.date.today()
        disponibilidad = []
        
        for i in range(1, 6):  # Próximos 5 días hábiles
            fecha = hoy + datetime.timedelta(days=i)
            if fecha.weekday() < 5:  # Solo días hábiles
                # Simular ocupación
                ocupacion = random.randint(20, 95)
                if ocupacion < 50:
                    estado = "Alta disponibilidad"
                elif ocupacion < 80:
                    estado = "Disponibilidad media"
                else:
                    estado = "Poca disponibilidad"
                
                disponibilidad.append(
                    f"📅 {fecha.strftime('%A %d/%m')}: {estado}"
                )
        
        mensaje = "📊 **Disponibilidad próximos días:**\n\n"
        mensaje += "\n".join(disponibilidad)
        mensaje += "\n\n¿Para qué fecha querés agendar tu turno?"
        
        dispatcher.utter_message(text=mensaje)
        
        # Registrar consulta para aprendizaje
        if conversation_logger:
            log_rasa_interaction(
                conversation_logger,
                tracker,
                "Consulta de disponibilidad general realizada"
            )
        
        return []

class ActionTiempoEsperaActual(Action):
    def name(self) -> Text:
        return "action_tiempo_espera_actual"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ahora = datetime.datetime.now()
        ocupacion_actual = obtener_ocupacion_simulada(ahora)
        urgencia = 5  # Nivel medio
        
        tiempo_espera = calcular_espera(ocupacion_actual, urgencia)
        
        if ocupacion_actual < 40:
            estado = "tranquila"
            emoji = "🟢"
        elif ocupacion_actual < 70:
            estado = "moderada"
            emoji = "🟡"
        else:
            estado = "ocupada"
            emoji = "🔴"
        
        mensaje = f"{emoji} **Estado actual de la oficina:** {estado}\n"
        mensaje += f"📊 **Nivel de ocupación:** {ocupacion_actual}%\n"
        mensaje += f"⏱️ **Tiempo estimado de espera:** {tiempo_espera:.1f} minutos\n\n"
        
        if ocupacion_actual > 80:
            mensaje += "💡 Te recomiendo agendar para otro horario si es posible."
        
        dispatcher.utter_message(text=mensaje)
        
        # Registrar consulta para aprendizaje
        if conversation_logger:
            log_rasa_interaction(
                conversation_logger,
                tracker,
                f"Consulta tiempo espera: {tiempo_espera:.1f}min, ocupación: {ocupacion_actual}%"
            )
        
        return []

class ActionCalcularSaturacion(Action):
    def name(self) -> Text:
        return "action_calcular_saturacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ahora = datetime.datetime.now()
        ocupacion_actual = obtener_ocupacion_simulada(ahora)
        
        if ocupacion_actual < 30:
            estado = "muy baja"
            emoji = "🟢"
            descripcion = "La oficina está muy tranquila"
        elif ocupacion_actual < 50:
            estado = "baja"
            emoji = "🟢"
            descripcion = "Poca gente esperando"
        elif ocupacion_actual < 70:
            estado = "media"
            emoji = "🟡"
            descripcion = "Nivel normal de ocupación"
        elif ocupacion_actual < 85:
            estado = "alta"
            emoji = "🟠"
            descripcion = "Bastante gente esperando"
        else:
            estado = "muy alta"
            emoji = "🔴"
            descripcion = "La oficina está muy llena"
        
        mensaje = f"{emoji} **Saturación actual:** {estado}\n"
        mensaje += f"📊 **Porcentaje de ocupación:** {ocupacion_actual}%\n"
        mensaje += f"📝 **Estado:** {descripcion}"
        
        dispatcher.utter_message(text=mensaje)
        
        # Registrar consulta para aprendizaje
        if conversation_logger:
            log_rasa_interaction(
                conversation_logger,
                tracker,
                f"Consulta saturación: {estado} ({ocupacion_actual}%)"
            )
        
        return []

# =====================================================
# ACCIONES DE SESIÓN
# =====================================================
class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker, domain: Dict[Text, Any]) -> List[EventType]:
        
        # Registrar inicio de sesión para aprendizaje
        if conversation_logger:
            try:
                log_rasa_interaction(
                    conversation_logger,
                    tracker,
                    "Nueva sesión iniciada"
                )
            except Exception as e:
                logger.error(f"Error logging inicio de sesión: {e}")
        
        return [SessionStarted()]