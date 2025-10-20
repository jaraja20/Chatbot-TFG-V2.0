
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LM_STUDIO_URL = "http://192.168.3.118:1234/v1/chat/completions"

# =====================================================
# ✅ PROMPT MEJORADO CON CONTEXTO ESPECÍFICO
# =====================================================

CONTEXTO_CHATBOT_MEJORADO = """Eres un asistente virtual especializado en gestión de turnos de cédulas de identidad en Ciudad del Este, Paraguay.

**📋 INFORMACIÓN ESENCIAL DE LA OFICINA:**
• Ubicación: Av. Pioneros del Este, Ciudad del Este, Paraguay
• Horario: Lunes a viernes, 07:00 a 15:00 hs
• Hora de almuerzo: 11:00 (oficina cerrada)
• Costo: 25.000 Guaraníes (SOLO EFECTIVO)
• Sistema de turnos: Cada 15 minutos, máximo 3 personas por horario

**📄 REQUISITOS PARA TRAMITAR:**

Primera vez (nunca tuve cédula):
• Partida de nacimiento ORIGINAL
• Comprobante de pago de 25.000 Gs
• Si sos menor de 18 años: ir con padre/madre/tutor

Renovación (ya tengo cédula):
• Cédula anterior
• Comprobante de pago de 25.000 Gs

Extranjeros:
• Deben tener residencia legal vigente
• Documentos que acrediten residencia

**⚠️ REGLAS IMPORTANTES:**
1. El trámite NO se puede hacer online - es PRESENCIAL obligatorio
2. NO se puede tramitar la cédula de otra persona (excepción: padres/tutores de menores)
3. La cédula se entrega el MISMO DÍA del trámite
4. Solo se acepta efectivo, NO tarjetas
5. El trámite dura aproximadamente 10-15 minutos una vez que te atienden

**🎯 TU MISIÓN:**
Responder preguntas sobre cédulas de forma clara, breve y útil. Siempre redirigir al usuario hacia acciones concretas: agendar turno, consultar disponibilidad, o verificar requisitos.

**✅ EJEMPLOS DE BUENAS RESPUESTAS:**

Usuario: "¿Puedo tramitar la cédula online?"
Vos: "No, la cédula se tramita únicamente de forma presencial en nuestra oficina de Av. Pioneros del Este. Necesitás venir con tus documentos originales. ¿Querés que te ayude a agendar un turno?"

Usuario: "¿Cuánto tiempo demora el trámite?"
Vos: "El trámite en sí toma unos 10-15 minutos una vez que te atienden. Tu cédula estará lista el mismo día. El tiempo total depende de cuánta gente haya. ¿Te ayudo a agendar para un horario con poca gente?"

Usuario: "¿Aceptan tarjeta de crédito?"
Vos: "No, solo aceptamos efectivo. El costo es de 25.000 Guaraníes. Te recomiendo traer el monto exacto. ¿Querés agendar tu turno?"

Usuario: "Mi hermana puede ir a sacar mi cédula?"
Vos: "No, cada persona debe tramitar su propia cédula de forma personal. Es obligatorio que vayas vos. La única excepción son menores de edad que deben ir con su padre/madre/tutor. ¿Necesitás agendar tu turno?"

Usuario: "¿Qué papeles necesito?"
Vos: "Depende si es tu primera cédula o renovación. Para primera vez: partida de nacimiento ORIGINAL. Para renovación: tu cédula anterior. En ambos casos necesitás el comprobante de pago de 25.000 Gs. ¿Cuál es tu caso?"

Usuario: "¿Hay estacionamiento?"
Vos: "Sí, hay estacionamiento público disponible cerca de la oficina en Av. Pioneros del Este. ¿Querés que te ayude a agendar un turno?"

**❌ CUANDO NO SEPAS ALGO:**

Usuario: "¿Cómo está el clima hoy?"
Vos: "No tengo información sobre el clima, pero puedo ayudarte con todo lo relacionado a tu trámite de cédula. ¿Necesitás agendar un turno o consultar algo sobre documentación?"

Usuario: "¿Dónde puedo comer cerca?"
Vos: "No manejo información sobre restaurantes, pero sí puedo ayudarte con tu trámite de cédula. ¿Hay algo sobre documentación o turnos en lo que pueda ayudarte?"

**📝 REGLAS DE ESTILO:**
• Usá lenguaje informal paraguayo: "vos", "querés", "tenés"
• Mantené respuestas CORTAS (máximo 3-4 líneas)
• Siempre TERMINÁ con una pregunta o acción sugerida
• Si la consulta NO es sobre cédulas, redirigí amablemente
• Nunca inventes información - si no sabés, admítelo y redirigí

Ahora respondé la siguiente consulta del usuario de forma útil, clara y breve:"""

# =====================================================
# RESPUESTAS PREDEFINIDAS RÁPIDAS
# =====================================================

RESPUESTAS_RAPIDAS = {
    # Agradecimientos
    "gracias": "¡De nada! 😊 ¿Hay algo más en lo que pueda ayudarte?",
    "muchas gracias": "¡Un placer ayudarte! 😊 ¿Necesitás algo más?",
    
    # Confirmaciones
    "ok": "Perfecto 👍 ¿Necesitás algo más?",
    "entendido": "Genial 👍 Estoy acá para lo que necesites.",
    "perfecto": "¡Excelente! 🎉 ¿Te ayudo con algo más?",
    "esta bien": "Perfecto 😊 Avisame si necesitás algo más.",
    "está bien": "Perfecto 😊 Avisame si necesitás algo más.",
}

# =====================================================
# FUNCIÓN PARA BUSCAR RESPUESTA RÁPIDA
# =====================================================

def buscar_respuesta_rapida(mensaje: str) -> Optional[str]:
    """Busca respuesta predefinida para casos simples"""
    mensaje_lower = mensaje.lower().strip()
    
    for patron, respuesta in RESPUESTAS_RAPIDAS.items():
        if patron == mensaje_lower or patron in mensaje_lower:
            logger.info(f"✅ Respuesta rápida: {patron}")
            return respuesta
    
    return None

# =====================================================
# FUNCIÓN MEJORADA PARA GENERAR RESPUESTA CON LLM
# =====================================================

def generar_respuesta_llm_fallback(mensaje_usuario: str) -> Optional[str]:
    """
    Genera respuesta inteligente usando LLM con prompt mejorado
    
    Args:
        mensaje_usuario: Consulta del usuario
        
    Returns:
        Respuesta del LLM o None si falla
    """
    try:
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": CONTEXTO_CHATBOT_MEJORADO
                },
                {
                    "role": "user",
                    "content": mensaje_usuario
                }
            ],
            "temperature": 0.7,      # Balance entre creatividad y precisión
            "max_tokens": 150,       # Respuestas concisas
            "top_p": 0.9,
            "frequency_penalty": 0.3,  # Evitar repeticiones
            "presence_penalty": 0.3,
            "stream": False
        }
        
        logger.info(f"🤖 Consultando LLM para: '{mensaje_usuario}'")
        
        response = requests.post(
            LM_STUDIO_URL,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            respuesta = result['choices'][0]['message']['content'].strip()
            
            # Validar que la respuesta tenga sentido
            if len(respuesta) > 10:  # Respuesta mínima válida
                logger.info(f"✅ LLM respondió: {respuesta[:60]}...")
                return respuesta
            else:
                logger.warning(f"⚠️ Respuesta del LLM muy corta: '{respuesta}'")
                return None
        else:
            logger.error(f"❌ Error LLM HTTP {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout en LLM")
        return None
    except Exception as e:
        logger.error(f"❌ Error en LLM: {e}")
        return None

# =====================================================
# DETECCIÓN DE INTENCIÓN PARA REDIRECCIÓN
# =====================================================

def detectar_intencion_post_fallback(mensaje: str) -> str:
    """Detecta la intención del mensaje para redirigir adecuadamente"""
    
    mensaje_lower = mensaje.lower()
    
    if any(w in mensaje_lower for w in ["turno", "agendar", "sacar", "reservar"]):
        return "📅 ¿Querés agendar un turno? Decime 'quiero agendar' y te ayudo paso a paso."
    
    if any(w in mensaje_lower for w in ["horario", "disponible", "cuando"]):
        return "🕐 ¿Querés ver los horarios disponibles? Decime 'horarios disponibles'."
    
    if any(w in mensaje_lower for w in ["requisito", "documento", "necesito", "llevar"]):
        return "📋 ¿Querés saber qué documentos necesitás? Decime 'requisitos'."
    
    if any(w in mensaje_lower for w in ["donde", "ubicacion", "direccion", "queda"]):
        return "📍 ¿Necesitás la ubicación? Decime 'dónde queda'."
    
    if any(w in mensaje_lower for w in ["costo", "precio", "cuanto", "vale"]):
        return "💰 El costo es de 25.000 Guaraníes. ¿Querés agendar un turno?"
    
    if any(w in mensaje_lower for w in ["espera", "demora", "tiempo"]):
        return "⏱️ ¿Querés saber el tiempo de espera actual? Decime 'cuánto voy a esperar'."
    
    return "💡 Puedo ayudarte a:\n• Agendar turnos\n• Consultar horarios\n• Ver requisitos\n• Info sobre ubicación y costos\n\n¿Qué necesitás?"

# =====================================================
# FUNCIÓN PRINCIPAL - MANEJO COMPLETO DEL FALLBACK
# =====================================================

def manejar_fallback_inteligente(mensaje_usuario: str) -> str:
    """
    Maneja fallback de forma inteligente con estrategia en capas:
    1. Respuestas rápidas predefinidas
    2. LLM con prompt mejorado
    3. Redirección genérica
    
    Args:
        mensaje_usuario: Mensaje que Rasa no entendió
        
    Returns:
        Respuesta útil para el usuario
    """
    
    # Capa 1: Respuestas instantáneas
    respuesta_rapida = buscar_respuesta_rapida(mensaje_usuario)
    if respuesta_rapida:
        return respuesta_rapida
    
    # Capa 2: LLM con contexto mejorado
    respuesta_llm = generar_respuesta_llm_fallback(mensaje_usuario)
    if respuesta_llm:
        return respuesta_llm
    
    # Capa 3: Fallback final con redirección
    redireccion = detectar_intencion_post_fallback(mensaje_usuario)
    
    return f"Entiendo tu consulta, pero no tengo información específica sobre eso.\n\n{redireccion}"

# =====================================================
# PRUEBAS
# =====================================================

if __name__ == "__main__":
    print("🧪 Probando sistema de fallback con prompt mejorado\n")
    print("=" * 70)
    
    casos_test = [
        "gracias por todo",
        "¿puedo tramitar online?",
        "mi hermana puede ir por mi?",
        "aceptan tarjeta?",
        "hay estacionamiento?",
        "cuanto tiempo demora?",
        "que documentos necesito?",
        "como está el clima hoy?",
        "donde puedo comer cerca?",
    ]
    
    for i, caso in enumerate(casos_test, 1):
        print(f"\n{i}. Usuario: {caso}")
        respuesta = manejar_fallback_inteligente(caso)
        print(f"   Bot: {respuesta[:100]}...")
        print("-" * 70)