"""
ORQUESTADOR INTELIGENTE
Integra: LLM + Rasa + Motor Difuso + Base de Datos

Este módulo coordina todos los componentes para dar respuestas contextuales
y precisas usando la información real del sistema.
"""

import requests
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, date, timedelta
import psycopg2

# Imports de tus módulos existentes
try:
    from llm_classifier import LLMIntentClassifier
    from llm_fallback_handler import manejar_fallback_inteligente
    from motor_difuso import (
        calcular_espera,
        analizar_disponibilidad_dia,
        obtener_mejor_recomendacion,
        generar_respuesta_recomendacion
    )
    MODULOS_DISPONIBLES = True
except ImportError as e:
    logging.warning(f"⚠️ Algunos módulos no disponibles: {e}")
    MODULOS_DISPONIBLES = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN
# =====================================================

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
LM_STUDIO_URL = "http://192.168.3.118:1234/v1/chat/completions"

DB_CONFIG = {
    'host': 'localhost',
    'database': 'chatbotdb',
    'user': 'botuser',
    'password': 'root'
}

# =====================================================
# CONTEXTO DE SESIONES
# =====================================================

# Almacena contexto de cada sesión
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
        self.datos_difusos = {}  # Para guardar cálculos del motor difuso
        
    def actualizar(self, **kwargs):
        """Actualiza el contexto con nuevos datos"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
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

# =====================================================
# CLASE PRINCIPAL: ORQUESTADOR
# =====================================================

class OrquestadorInteligente:
    """
    Orquesta todos los componentes del sistema para dar
    respuestas inteligentes y contextuales
    """
    
    def __init__(self):
        self.llm_classifier = LLMIntentClassifier() if MODULOS_DISPONIBLES else None
        logger.info("✅ Orquestador inicializado")
    
    def procesar_mensaje(self, user_message: str, session_id: str) -> Dict:
        """
        Función principal que procesa un mensaje del usuario
        
        Args:
            user_message: Mensaje del usuario
            session_id: ID de sesión
            
        Returns:
            Dict con la respuesta y metadata
        """
        
        # 1. Obtener o crear contexto de sesión
        context = self._get_or_create_context(session_id)
        context.ultimo_mensaje = user_message
        
        # 2. Clasificar intent con LLM
        intent, confidence = self._clasificar_intent(user_message, context)
        context.intent_actual = intent
        
        logger.info(f"📊 Intent: {intent} (confianza: {confidence:.2f})")
        
        # 3. Extraer entidades del mensaje
        entities = self._extraer_entidades(user_message, intent)
        context.actualizar(**entities)
        
        # 4. Decidir estrategia de respuesta
        if confidence < 0.6:
            # Baja confianza → Usar fallback con LLM contextual
            response = self._generar_respuesta_llm_contextual(
                user_message, context
            )
        elif intent == "agendar_turno":
            response = self._manejar_agendamiento(context)
        elif intent in ["frase_ambigua", "consultar_disponibilidad"]:
            response = self._manejar_consulta_horarios(user_message, context)
        elif intent == "consulta_tiempo_espera":
            response = self._calcular_tiempo_espera_real(context)
        elif intent in ["consultar_requisitos", "consultar_costo", "consultar_ubicacion"]:
            # Información estática → Enviar a Rasa
            response = self._consultar_rasa(user_message, session_id)
        else:
            # Otros intents → Rasa con enriquecimiento
            response = self._consultar_rasa_enriquecido(
                user_message, session_id, intent, context
            )
        
        # 5. Guardar en historial
        context.conversacion_historial.append({
            'timestamp': datetime.now(),
            'user': user_message,
            'bot': response.get('text', ''),
            'intent': intent,
            'confidence': confidence
        })
        
        return {
            'text': response.get('text', 'Lo siento, hubo un error'),
            'intent': intent,
            'confidence': confidence,
            'context': context.to_dict()
        }
    
    def _get_or_create_context(self, session_id: str) -> SessionContext:
        """Obtiene o crea contexto de sesión"""
        if session_id not in SESSION_CONTEXTS:
            SESSION_CONTEXTS[session_id] = SessionContext(session_id)
        return SESSION_CONTEXTS[session_id]
    
    def _clasificar_intent(self, message: str, context: SessionContext) -> Tuple[str, float]:
        # Si estamos en flujo de agendar, prioriza captura de datos
        if context.intent_actual in ["agendar_turno", "proporcionar_datos_turno"]:
            if not context.nombre and self._parece_nombre(message):
                return "informar_nombre", 0.98
            if not context.cedula and self._parece_cedula(message):
                return "informar_cedula", 0.98
            if not context.fecha and self._parece_fecha(message):
                return "informar_fecha", 0.95
            if not context.hora and self._parece_hora(message):
                return "elegir_horario", 0.95

        if not self.llm_classifier:
            return ("nlu_fallback", 0.3)

        intent, confidence = self.llm_classifier.classify_intent(message)

        # Normaliza nombres del LLM al catálogo local
        normaliza = {
            "consulta_tiempo_espera": "consulta_tiempo_espera",
            "consultar_disponibilidad": "consultar_disponibilidad",
            "consultar_horarios": "consultar_horarios",
            "consultar_requisitos": "consultar_requisitos",
            "consultar_ubicacion": "consultar_ubicacion",
            "consultar_costo": "consultar_costo",
            "cancelar_turno": "cancelar_turno",
            "agendar_turno": "agendar_turno",
            "greet": "greet",
            "goodbye": "goodbye",
            "affirm": "affirm",
            "deny": "deny",
            "agradecimiento": "agradecimiento",
            "nlu_fallback": "nlu_fallback",
            "out_of_scope": "nlu_fallback"
        }
        intent = normaliza.get(intent, "nlu_fallback")
        return intent, float(confidence or 0.6)

    
    def _extraer_entidades(self, message: str, intent: str) -> Dict:
        """Extrae entidades específicas del mensaje"""
        entities = {}
        
        # Nombre
        if intent == "informar_nombre" or "mi nombre es" in message.lower():
            # Extraer todo después de "mi nombre es" o "me llamo"
            for frase in ["mi nombre es", "me llamo", "soy"]:
                if frase in message.lower():
                    nombre = message.lower().split(frase)[-1].strip()
                    entities['nombre'] = nombre.title()
                    break
        
        # Cédula (números)
        if intent in ["informar_cedula", "informar_cedula_primera_vez"]:
            import re
            numeros = re.findall(r'\d+', message)
            if numeros:
                entities['cedula'] = numeros[0]
        
        # Fecha
        if intent == "informar_fecha":
            fecha_parseada = self._parsear_fecha(message)
            if fecha_parseada:
                entities['fecha'] = fecha_parseada
        
        # Hora
        if intent == "elegir_horario":
            hora_parseada = self._parsear_hora(message)
            if hora_parseada:
                entities['hora'] = hora_parseada
        
        # Email
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, message)
        if emails:
            entities['email'] = emails[0]
        
        return entities
    
    def _manejar_agendamiento(self, context: SessionContext) -> Dict:
        """Maneja el flujo de agendamiento paso a paso"""
        
        # Verificar qué falta
        if not context.nombre:
            return {
                'text': "Perfecto, vamos a agendar tu turno. ¿Cuál es tu nombre completo?"
            }
        
        if not context.cedula:
            return {
                'text': f"Gracias {context.nombre}. ¿Cuál es tu número de cédula?"
            }
        
        if not context.fecha:
            # Aquí usar motor difuso para recomendar
            hoy = date.today()
            manana = hoy + timedelta(days=1)
            
            mejor_franja, datos = obtener_mejor_recomendacion(manana)
            
            return {
                'text': f"¿Para qué día necesitás el turno?\n\n"
                        f"💡 Recomendación: Para mañana ({manana.strftime('%d/%m')}) "
                        f"te sugiero {mejor_franja} ({datos['rango']}), "
                        f"menor ocupación estimada ({datos['ocupacion']:.0f}%)."
            }
        
        if not context.hora:
            # Calcular horarios disponibles con motor difuso
            fecha_obj = datetime.strptime(context.fecha, '%Y-%m-%d').date()
            analisis = analizar_disponibilidad_dia(fecha_obj)
            
            # Encontrar mejor franja
            mejor_franja = min(analisis.items(), key=lambda x: x[1]['ocupacion'])
            nombre_franja, datos = mejor_franja
            
            horarios_str = ", ".join(datos['horarios_sugeridos'])
            
            return {
                'text': f"¿Qué horario preferís para el {context.fecha}?\n\n"
                        f"🌟 Mejores horarios (menos ocupación):\n"
                        f"{horarios_str}\n\n"
                        f"O decime tu horario preferido."
            }
        
        # Tiene todos los datos → Confirmar
        return {
            'text': f"✅ Resumen de tu turno:\n\n"
                    f"👤 Nombre: {context.nombre}\n"
                    f"🆔 Cédula: {context.cedula}\n"
                    f"📅 Fecha: {context.fecha}\n"
                    f"🕐 Hora: {context.hora}\n\n"
                    f"¿Está todo correcto? (Decí 'confirmo' o tu email para recibir invitación)"
        }
    
    def _manejar_consulta_horarios(self, message: str, context: SessionContext) -> Dict:
        """Maneja consultas de horarios usando motor difuso"""
        
        # Determinar fecha objetivo
        if context.fecha:
            fecha_obj = datetime.strptime(context.fecha, '%Y-%m-%d').date()
        else:
            # Usar mañana por defecto
            fecha_obj = date.today() + timedelta(days=1)
        
        # Generar respuesta con motor difuso
        respuesta_difusa = generar_respuesta_recomendacion(fecha_obj, message)
        
        return {
            'text': respuesta_difusa + "\n\n¿Te gustaría agendar para alguno de estos horarios?"
        }
    
    def _calcular_tiempo_espera_real(self, context: SessionContext) -> Dict:
        """Calcula tiempo de espera usando motor difuso"""
        
        if not context.fecha or not context.hora:
            # Sin datos específicos, dar estimación general
            ahora = datetime.now()
            hora_actual = ahora.hour + ahora.minute / 60
            
            # Simular ocupación actual (en producción vendría de BD)
            ocupacion = 50  # Valor por defecto
            urgencia = 5  # Media
            
            espera_min = calcular_espera(ocupacion, urgencia, hora_actual)
            
            return {
                'text': f"⏱️ Tiempo de espera estimado actual: {espera_min:.0f} minutos.\n\n"
                        f"📊 Ocupación actual: {ocupacion:.0f}%\n\n"
                        f"¿Querés agendar un turno para evitar la espera?"
            }
        else:
            # Con fecha y hora específica
            fecha_obj = datetime.strptime(context.fecha, '%Y-%m-%d').date()
            hora_decimal = float(context.hora.split(':')[0])
            
            analisis = analizar_disponibilidad_dia(fecha_obj)
            
            # Encontrar la franja correspondiente
            for nombre_franja, datos in analisis.items():
                if hora_decimal >= 7 and hora_decimal < 9:
                    franja_elegida = 'temprano'
                elif hora_decimal >= 9 and hora_decimal < 12:
                    franja_elegida = 'manana'
                elif hora_decimal >= 12 and hora_decimal < 14:
                    franja_elegida = 'mediodia'
                else:
                    franja_elegida = 'tarde'
                
                if nombre_franja == franja_elegida:
                    return {
                        'text': f"⏱️ Para {context.fecha} a las {context.hora}:\n\n"
                                f"📊 Ocupación estimada: {datos['ocupacion']:.0f}%\n"
                                f"⏰ Espera estimada: {datos['espera_estimada']:.0f} minutos\n\n"
                                f"¿Querés confirmar este turno?"
                    }
            
            return {'text': "No pude calcular la espera para ese horario."}
    
    def _generar_respuesta_llm_contextual(self, message: str, context: SessionContext) -> Dict:
        """Genera respuesta usando LLM con TODO el contexto del sistema"""
        
        # Construir prompt con contexto completo
        system_prompt = f"""Eres un asistente para agendar turnos de cédulas en Ciudad del Este.

CONTEXTO DE LA CONVERSACIÓN ACTUAL:
- Nombre: {context.nombre or 'No proporcionado'}
- Cédula: {context.cedula or 'No proporcionado'}
- Fecha deseada: {context.fecha or 'No proporcionado'}
- Hora deseada: {context.hora or 'No proporcionado'}
- Intent actual: {context.intent_actual or 'Desconocido'}

INFORMACIÓN DEL SISTEMA:
- Ubicación: Av. Pioneros del Este, Ciudad del Este
- Horario: Lunes a viernes, 07:00 a 15:00
- Costo: 25.000 Guaraníes (SOLO EFECTIVO)
- Turnos cada 15 minutos, máximo 3 personas por horario

INSTRUCCIONES:
1. Responde de forma útil y natural
2. Si falta información para agendar, pedila específicamente
3. Usa los datos del contexto para personalizar la respuesta
4. Sé breve (máximo 3-4 líneas)
5. Siempre termina con una pregunta o acción sugerida

Usuario pregunta: {message}

Responde de forma útil:"""
        
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7,
                "max_tokens": 150,
                "stream": False
            }
            
            response = requests.post(LM_STUDIO_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                respuesta_llm = result['choices'][0]['message']['content'].strip()
                
                logger.info(f"✅ LLM respondió: {respuesta_llm[:60]}...")
                return {'text': respuesta_llm}
            else:
                # Fallback a handler existente
                return {'text': manejar_fallback_inteligente(message)}
                
        except Exception as e:
            logger.error(f"Error en LLM contextual: {e}")
            return {'text': manejar_fallback_inteligente(message)}
    
    def _consultar_rasa(self, message: str, session_id: str) -> Dict:
        """Consulta directa a Rasa (para info estática)"""
        try:
            response = requests.post(
                RASA_URL,
                json={'sender': session_id, 'message': message},
                timeout=10
            )
            
            if response.status_code == 200:
                bot_responses = response.json()
                if bot_responses:
                    texts = [r.get('text', '') for r in bot_responses if 'text' in r]
                    return {'text': ' '.join(texts)}
            
            return {'text': "Lo siento, hubo un problema al consultar esa información."}
            
        except Exception as e:
            logger.error(f"Error consultando Rasa: {e}")
            return {'text': "Error de conexión con el sistema."}
    
    def _consultar_rasa_enriquecido(self, message: str, session_id: str, 
                                     intent: str, context: SessionContext) -> Dict:
        """Consulta Rasa pero enriquece la respuesta con contexto"""
        
        # Primero obtener respuesta de Rasa
        rasa_response = self._consultar_rasa(message, session_id)
        
        # Enriquecer según el intent
        if intent == "consultar_horarios" and context.fecha:
            # Agregar análisis difuso
            fecha_obj = datetime.strptime(context.fecha, '%Y-%m-%d').date()
            analisis = analizar_disponibilidad_dia(fecha_obj)
            
            mejor_franja = min(analisis.items(), key=lambda x: x[1]['ocupacion'])
            nombre_franja, datos = mejor_franja
            
            rasa_response['text'] += f"\n\n💡 Recomendación: {nombre_franja} " \
                                      f"({datos['rango']}) tiene menor ocupación " \
                                      f"({datos['ocupacion']:.0f}%)."
        
        return rasa_response
    
    # =====================================================
    # FUNCIONES AUXILIARES
    # =====================================================
    
    def _parece_nombre(self, text: str) -> bool:
        """Heurística simple para detectar si es un nombre"""
        words = text.split()
        return len(words) >= 2 and all(w.replace(' ', '').isalpha() for w in words)
    
    def _parece_cedula(self, text: str) -> bool:
        """Detecta si parece número de cédula"""
        import re
        numeros = re.findall(r'\d+', text)
        return len(numeros) > 0 and len(numeros[0]) >= 6
    
    def _parece_fecha(self, text: str) -> bool:
        """Detecta si menciona fecha"""
        palabras_fecha = ['mañana', 'lunes', 'martes', 'miércoles', 'jueves', 
                          'viernes', 'sábado', 'día', 'mes', '/']
        return any(p in text.lower() for p in palabras_fecha)
    
    def _parece_hora(self, text: str) -> bool:
        """Detecta si menciona hora"""
        import re
        # Patrones de hora: "10", "10:00", "a las 10", etc.
        return bool(re.search(r'\d{1,2}(?::\d{2})?', text)) or \
               any(p in text.lower() for p in ['mañana', 'tarde', 'hora'])
    
    def _parsear_fecha(self, text: str) -> Optional[str]:
        """Parsea fecha del texto a formato YYYY-MM-DD"""
        text_lower = text.lower()
        
        hoy = date.today()
        
        if 'mañana' in text_lower or 'manana' in text_lower:
            return (hoy + timedelta(days=1)).strftime('%Y-%m-%d')
        
        dias_semana = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2,
            'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5
        }
        
        for dia_nombre, dia_num in dias_semana.items():
            if dia_nombre in text_lower:
                # Encontrar el próximo día de la semana
                dias_hasta = (dia_num - hoy.weekday()) % 7
                if dias_hasta == 0:
                    dias_hasta = 7
                fecha_resultado = hoy + timedelta(days=dias_hasta)
                return fecha_resultado.strftime('%Y-%m-%d')
        
        # Intentar parsear formato DD/MM o DD-MM
        import re
        match = re.search(r'(\d{1,2})[/-](\d{1,2})', text)
        if match:
            dia = int(match.group(1))
            mes = int(match.group(2))
            try:
                fecha_resultado = date(hoy.year, mes, dia)
                if fecha_resultado < hoy:
                    # Si ya pasó, usar año siguiente
                    fecha_resultado = date(hoy.year + 1, mes, dia)
                return fecha_resultado.strftime('%Y-%m-%d')
            except:
                pass
        
        return None
    
    def _parsear_hora(self, text: str) -> Optional[str]:
        """Parsea hora del texto a formato HH:MM"""
        import re
        
        # Buscar formato HH:MM o HH
        match = re.search(r'(\d{1,2})(?::(\d{2}))?', text)
        if match:
            hora = int(match.group(1))
            minuto = int(match.group(2)) if match.group(2) else 0
            
            # Validar rango
            if 7 <= hora <= 17 and 0 <= minuto < 60:
                return f"{hora:02d}:{minuto:02d}"
        
        # Palabras clave
        text_lower = text.lower()
        if 'primera hora' in text_lower or 'temprano' in text_lower:
            return "07:00"
        elif 'mediodía' in text_lower or 'mediodia' in text_lower:
            return "12:00"
        elif 'tarde' in text_lower:
            return "15:00"
        
        return None

# =====================================================
# INSTANCIA GLOBAL
# =====================================================

orquestador = OrquestadorInteligente()

# =====================================================
# FUNCIÓN PRINCIPAL PARA USAR EN FLASK
# =====================================================

def procesar_mensaje_inteligente(user_message: str, session_id: str) -> Dict:
    """
    Función principal para usar en app.py
    
    Args:
        user_message: Mensaje del usuario
        session_id: ID de sesión
        
    Returns:
        Dict con respuesta y metadata
    """
    return orquestador.procesar_mensaje(user_message, session_id)

# =====================================================
# TESTING
# =====================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TEST DEL ORQUESTADOR INTELIGENTE")
    print("=" * 70)
    print()
    
    # Simular conversación completa
    session_test = "test_session_001"
    
    mensajes_test = [
        "hola",
        "quiero sacar un turno",
        "Juan Pérez",
        "1234567",
        "para mañana",
        "qué horarios me recomendás",
        "a las 9",
        "confirmo"
    ]
    
    for i, mensaje in enumerate(mensajes_test, 1):
        print(f"👤 Usuario: {mensaje}")
        resultado = procesar_mensaje_inteligente(mensaje, session_test)
        print(f"🤖 Bot: {resultado['text'][:100]}...")
        print(f"📊 Intent: {resultado['intent']} (conf: {resultado['confidence']:.2f})")
        print("-" * 70)
        print()