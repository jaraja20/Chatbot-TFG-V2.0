from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, SessionStarted, EventType

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import random
import string
import dateparser

# 🔹 Motor difuso externo
from motor_difuso import calcular_espera

# =====================================================
# Configuración de conexión a PostgreSQL
# =====================================================
DATABASE_URL = 'postgresql://botuser:root@localhost:5432/chatbotdb'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# =====================================================
# Tabla de turnos
# =====================================================
class Turno(Base):
    __tablename__ = 'turnos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String)
    cedula = Column(String)
    fecha_hora = Column(DateTime, default=datetime.datetime.utcnow)
    codigo = Column(String)

# =====================================================
# Funciones auxiliares
# =====================================================
def generar_codigo_unico(longitud=6):
    """Genera un código único para cada turno"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=longitud))

def normalizar_fecha(texto: str) -> str:
    """Convierte frases como 'mañana' o 'jueves 22' en dd/mm/YYYY"""
    fecha_parseada = dateparser.parse(
        texto,
        languages=['es'],
        settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.datetime.now()
        }
    )
    if fecha_parseada:
        return fecha_parseada.strftime("%d/%m/%Y")
    return None

def normalizar_hora(texto: str) -> str:
    """Convierte expresiones como '3pm' o '15' en HH:MM"""
    hora_parseada = dateparser.parse(texto, languages=['es'])
    if hora_parseada:
        return hora_parseada.strftime("%H:%M")
    return None

# =====================================================
# ACCIONES PERSONALIZADAS
# =====================================================
class ActionGuardarTurno(Action):
    def name(self) -> Text:
        return "action_guardar_turno"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        session = Session()

        nombre = tracker.get_slot("nombre")
        cedula = tracker.get_slot("cedula")
        fecha = tracker.get_slot("fecha")
        hora = tracker.get_slot("hora")

        # Normalización
        fecha_norm = normalizar_fecha(fecha) if fecha else None
        hora_norm = normalizar_hora(hora) if hora else None

        if not nombre:
            dispatcher.utter_message(text="Por favor, decime tu *nombre completo*.")
            session.close()
            return []

        if not fecha_norm:
            dispatcher.utter_message(text="Indicá la *fecha exacta* para el turno (ej: jueves 22 o mañana).")
            session.close()
            return []

        codigo = generar_codigo_unico()

        try:
            if hora_norm:
                fecha_hora_str = f"{fecha_norm} {hora_norm}"
                fecha_hora = datetime.datetime.strptime(fecha_hora_str, "%d/%m/%Y %H:%M")
            else:
                fecha_hora = datetime.datetime.strptime(fecha_norm, "%d/%m/%Y")
        except Exception:
            fecha_hora = datetime.datetime.utcnow()

        nuevo_turno = Turno(
            nombre=nombre,
            cedula=cedula if cedula else "N/A",
            fecha_hora=fecha_hora,
            codigo=codigo
        )

        session.add(nuevo_turno)
        session.commit()
        session.close()

        # Mensaje al usuario
        if cedula and cedula != "N/A":
            dispatcher.utter_message(
                text=f"✅ Turno confirmado:\n👤 {nombre}\n🪪 C.I: {cedula}\n📅 {fecha_norm} {hora_norm if hora_norm else ''}\n🔑 Código: *{codigo}*"
            )
        else:
            dispatcher.utter_message(
                text=f"✅ Turno confirmado (Primera vez):\n👤 {nombre}\n📅 {fecha_norm} {hora_norm if hora_norm else ''}\n🔑 Código: *{codigo}*"
            )

        return [SlotSet("nombre", None), SlotSet("cedula", None), SlotSet("fecha", None), SlotSet("hora", None)]

# =====================================================
# Normalizar fecha explícitamente
# =====================================================
class ActionNormalizarFecha(Action):
    def name(self) -> Text:
        return "action_normalizar_fecha"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        fecha_texto = tracker.latest_message.get("text")
        fecha_norm = normalizar_fecha(fecha_texto)

        if fecha_norm:
            dispatcher.utter_message(text=f"📅 Entendido, registré la fecha como: {fecha_norm}")
            return [SlotSet("fecha", fecha_norm)]
        else:
            dispatcher.utter_message(text="⚠️ No entendí la fecha, ¿podés repetir?")
            return []

# =====================================================
# Tiempo de espera (simulado con fuzzy)
# =====================================================
class ActionTiempoEsperaFuzzy(Action):
    def name(self) -> Text:
        return "action_tiempo_espera_fuzzy"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        nivel_ocupacion = random.randint(0, 100)

        if nivel_ocupacion < 40:
            tiempo_estimado = "15 minutos aprox."
        elif nivel_ocupacion < 70:
            tiempo_estimado = "30 minutos aprox."
        else:
            tiempo_estimado = "45-60 minutos aprox."

        dispatcher.utter_message(
            text=f"📊 La ocupación actual es del {nivel_ocupacion}%.\n⏳ Tiempo estimado de espera: {tiempo_estimado}"
        )
        return []

# =====================================================
# Saturación (simulado)
# =====================================================
class ActionCalcularSaturacion(Action):
    def name(self) -> Text:
        return "action_calcular_saturacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        capacidad_max = 100
        ocupacion_actual = random.randint(20, 100)
        porcentaje = (ocupacion_actual / capacidad_max) * 100

        if porcentaje < 50:
            estado = "baja"
        elif porcentaje < 80:
            estado = "media"
        else:
            estado = "alta"

        dispatcher.utter_message(
            text=f"📊 Nivel de saturación: *{estado}* ({porcentaje:.1f}% de capacidad usada)."
        )
        return []

# =====================================================
# Recomendación difusa con horarios cada 30 min
# =====================================================
class ActionRecomendarTurnoFuzzy(Action):
    def name(self) -> Text:
        return "action_recomendar_turno_fuzzy"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        franjas = {
            "mañana (07:00–11:00)": random.randint(0, 100),
            "mediodía (11:30–15:00)": random.randint(0, 100),
            "tarde (15:30–17:00)": random.randint(0, 100),
        }

        urgencia_valor = random.choice([3, 5, 8])
        recomendaciones = {f: calcular_espera(o, urgencia_valor) for f, o in franjas.items()}
        mejor_franja = min(recomendaciones, key=recomendaciones.get)

        if "mañana" in mejor_franja:
            horarios = ["07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00"]
        elif "mediodía" in mejor_franja:
            horarios = ["11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00"]
        else:
            horarios = ["15:30", "16:00", "16:30", "17:00"]

        sugerencias = random.sample(horarios, min(3, len(horarios)))

        dispatcher.utter_message(
            text=f"Según la disponibilidad, te recomiendo {mejor_franja}. Horarios posibles: {', '.join(sorted(sugerencias))}."
        )
        return []

# =====================================================
# Sesión
# =====================================================
class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: Dict[Text, Any]) -> List[EventType]:
        return [SessionStarted()]  # el saludo inicial lo maneja tu frontend
