

import requests
import logging
from typing import Tuple, Optional, List
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN
# =====================================================

LM_STUDIO_URL = "http://192.168.3.118:1234/v1/chat/completions"

INTENTS_DISPONIBLES = [
    "greet",
    "goodbye",
    "affirm",
    "deny",
    "agradecimiento",
    "agendar_turno",
    "cancelar_turno",
    "confirmar_turno",
    "proporcionar_datos_turno",
    "informar_fecha",
    "informar_nombre",
    "informar_cedula",
    "informar_cedula_primera_vez",
    "elegir_horario",
    "frase_ambigua",
    "solicitar_cambio_datos",
    "consultar_requisitos",
    "consultar_requisitos_primera_vez",
    "consultar_menor_edad",
    "consultar_extranjeros",
    "consultar_si_necesita_turno",
    "consultar_tramite_online",
    "consultar_tramite_para_terceros",
    "consultar_tolerancia_horaria",
    "consultar_sin_qr",
    "consultar_disponibilidad",
    "consultar_horarios",
    "consultar_ubicacion",
    "consultar_costo",
    "estado_tramite",
    "ayuda_tecnica",
    "consulta_tiempo_espera",
    "calcular_saturacion",
    "proporcionar_email",
    "consultar_turno",
    "nlu_fallback",
    "out_of_scope"
]

# =====================================================
# MAPEO DE PALABRAS CLAVE (FALLBACK)
# =====================================================

KEYWORD_MAPPING = {
    # Saludos
    "hola": "greet",
    "buenas": "greet",
    "buenos dias": "greet",
    "buen dia": "greet",
    "que tal": "greet",
    
    # Despedidas
    "chau": "goodbye",
    "adios": "goodbye",
    "hasta luego": "goodbye",
    "nos vemos": "goodbye",
    "bye": "goodbye",
    
    # Afirmaciones
    "confirmo": "affirm",
    "confirmar": "affirm",
    "acepto": "affirm",
    "correcto": "affirm",
    "exacto": "affirm",
    "si esta bien": "affirm",
    
    # Negaciones
    "no quiero": "deny",
    "no gracias": "deny",
    "cancelar": "deny",
    
    # Agendar turno (alta prioridad)
    "quiero turno": "agendar_turno",
    "sacar turno": "agendar_turno",
    "agendar turno": "agendar_turno",
    "reservar turno": "agendar_turno",
    "necesito turno": "agendar_turno",
    "quiero agendar": "agendar_turno",
    "quiero sacar": "agendar_turno",
    "quiero marcar": "agendar_turno",
    "marcar turno": "agendar_turno",
    "kmiero": "agendar_turno",  # error ortográfico común
    
    # Información personal
    "mi nombre es": "informar_nombre",
    "me llamo": "informar_nombre",
    "soy ": "informar_nombre",
    
    # Fecha
    "para mañana": "informar_fecha",
    "mañana": "informar_fecha",
    "para el": "informar_fecha",
    "ese martes": "informar_fecha",
    "ese dia": "informar_fecha",
    "esa fecha": "informar_fecha",
    
    # Hora - ✅ NUEVAS FRASES AGREGADAS
    "a las": "elegir_horario",
    "las ": "elegir_horario",
    "primera hora": "elegir_horario",
    "a primera hora": "elegir_horario",
    
    # Requisitos
    "requisitos": "consultar_requisitos",
    "que necesito": "consultar_requisitos",
    "documentos": "consultar_requisitos",
    
    # Ubicación
    "donde queda": "consultar_ubicacion",
    "donde esta": "consultar_ubicacion",
    "ubicacion": "consultar_ubicacion",
    "direccion": "consultar_ubicacion",
    "como llego": "consultar_ubicacion",
    
    # Costo
    "cuanto cuesta": "consultar_costo",
    "cuanto sale": "consultar_costo",
    "precio": "consultar_costo",
    "costo": "consultar_costo",
    "kuesta": "consultar_costo",  # error ortográfico
    
    # Horarios ambiguos - ✅ AMPLIADO
    "que horarios": "frase_ambigua",
    "horarios disponible": "frase_ambigua",
    "recomenda": "frase_ambigua",
    "mejor horario": "frase_ambigua",
    "mas temprano posible": "frase_ambigua",
    "lo mas temprano": "frase_ambigua",
    "lo antes posible": "frase_ambigua",
    "cuando puedo": "frase_ambigua",
    "horario temprano": "frase_ambigua",
    
    # Tiempo de espera
    "cuanto voy a esperar": "consulta_tiempo_espera",
    "tiempo de espera": "consulta_tiempo_espera",
    "cuanto demora": "consulta_tiempo_espera",
    "cuanta espera": "consulta_tiempo_espera",
    
    # Cancelar
    "cancelar turno": "cancelar_turno",
    "anular": "cancelar_turno",
}

# =====================================================
# PROMPT MEJORADO
# =====================================================

def generar_system_prompt() -> str:
    """Genera prompt ultra-simple para modelos pequeños"""
    intents_str = ", ".join(INTENTS_DISPONIBLES[:20])  # Solo los más importantes
    
    return f"""Eres un clasificador de intenciones. Responde SOLO con una palabra: el nombre del intent.

INTENTS VÁLIDOS: {intents_str}

REGLAS:
- Responde SOLO con el nombre del intent
- NO agregues explicaciones
- NO uses mayúsculas innecesarias
- NO uses símbolos como →, -, *

EJEMPLOS:
Usuario: "hola" → greet
Usuario: "quiero un turno" → agendar_turno
Usuario: "donde queda" → consultar_ubicacion
Usuario: "cuanto cuesta" → consultar_costo
Usuario: "confirmo" → affirm
Usuario: "chau" → goodbye"""

# =====================================================
# CLASE PRINCIPAL MEJORADA
# =====================================================

class LLMIntentClassifier:
    """Clasificador de intents usando LM Studio con fallback inteligente"""
    
    def __init__(self, model_url: str = LM_STUDIO_URL, temperature: float = 0.1):
        self.model_url = model_url
        self.temperature = temperature
        self.system_prompt = generar_system_prompt()
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Verifica si LM Studio está disponible"""
        try:
            base_url = self.model_url.replace("/v1/chat/completions", "")
            response = requests.get(f"{base_url}/v1/models", timeout=2)
            
            if response.status_code == 200:
                logger.info("✅ LM Studio está disponible")
                return True
            else:
                logger.warning("⚠️ LM Studio no responde correctamente")
                return False
        except Exception as e:
            logger.warning(f"⚠️ LM Studio no disponible: {e}")
            return False
    
    def classify_intent(self, user_message: str) -> Tuple[str, float]:
        """
        Clasifica el intent con estrategia híbrida: Keywords > LLM > Fallback
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Tuple (intent_name, confidence)
        """
        # Primero intentar con keywords (rápido y confiable)
        keyword_intent = self._classify_by_keywords(user_message)
        if keyword_intent:
            logger.info(f"🔑 Keywords clasificaron: {user_message} → {keyword_intent[0]}")
            return keyword_intent
        
        # Si no hay keyword match, usar LLM
        if not self.available:
            logger.warning("LM Studio no disponible, usando fallback")
            return "nlu_fallback", 0.3
        
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": self.temperature,
                "max_tokens": 10,  # Más corto para forzar respuesta simple
                "stop": ["\n", "Usuario:", "Explicación:"],  # Detener en saltos de línea
                "stream": False
            }
            
            response = requests.post(self.model_url, json=payload, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Error en LM Studio: {response.status_code}")
                return self._classify_by_keywords(user_message) or ("nlu_fallback", 0.3)
            
            result = response.json()
            llm_response = result['choices'][0]['message']['content'].strip()
            
            # NUEVA: Limpieza agresiva de respuesta
            intent_detected = self._extract_intent_aggressively(llm_response)
            
            if intent_detected in INTENTS_DISPONIBLES:
                logger.info(f"✅ LLM clasificó '{user_message}' → {intent_detected}")
                return intent_detected, 0.90
            else:
                logger.warning(f"⚠️ LLM falló: '{llm_response}'. Usando keywords como fallback")
                keyword_fallback = self._classify_by_keywords(user_message)
                return keyword_fallback if keyword_fallback else ("nlu_fallback", 0.4)
            
        except Exception as e:
            logger.error(f"❌ Error en LLM: {e}")
            keyword_fallback = self._classify_by_keywords(user_message)
            return keyword_fallback if keyword_fallback else ("nlu_fallback", 0.3)
    
    def _extract_intent_aggressively(self, llm_output: str) -> str:
        """
        Extrae el intent de forma agresiva, incluso si viene con texto extra
        
        Args:
            llm_output: Respuesta cruda del LLM
            
        Returns:
            Intent limpio o None
        """
        # Paso 1: Limpiar formato básico
        cleaned = llm_output.strip().lower()
        
        # Paso 2: Si contiene "→", extraer lo de después
        if "→" in cleaned:
            cleaned = cleaned.split("→")[-1].strip()
        
        # Paso 3: Si contiene "**", extraer lo del medio
        if "**" in cleaned:
            match = re.search(r'\*\*([a-z_]+)\*\*', cleaned)
            if match:
                cleaned = match.group(1)
        
        # Paso 4: Remover símbolos comunes
        cleaned = re.sub(r'["\'\.,\-\(\)\*\[\]:]', '', cleaned)
        
        # Paso 5: Si tiene múltiples líneas, tomar la primera
        if '\n' in cleaned:
            lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
            cleaned = lines[0] if lines else cleaned
        
        # Paso 6: Si tiene espacios, buscar palabras que coincidan con intents
        words = cleaned.split()
        for word in words:
            if word in INTENTS_DISPONIBLES:
                return word
        
        # Paso 7: Tomar solo la primera palabra
        first_word = words[0] if words else cleaned
        
        # Paso 8: Verificar si es un intent válido
        return first_word if first_word in INTENTS_DISPONIBLES else None
    
    def _classify_by_keywords(self, user_message: str) -> Optional[Tuple[str, float]]:
        """
        Clasificación por palabras clave como fallback
        Busca coincidencias de mayor a menor especificidad
        
        Args:
            user_message: Mensaje del usuario
            
        Returns:
            Tuple (intent, confidence) o None
        """
        message_lower = user_message.lower()
        
        # Ordenar keywords por longitud (más específicas primero)
        sorted_keywords = sorted(KEYWORD_MAPPING.items(), key=lambda x: len(x[0]), reverse=True)
        
        for keyword, intent in sorted_keywords:
            if keyword in message_lower:
                return (intent, 0.85)
        
        return None
    
    def batch_classify(self, messages: List[str]) -> List[Tuple[str, float]]:
        """Clasifica múltiples mensajes"""
        results = []
        for message in messages:
            intent, confidence = self.classify_intent(message)
            results.append((intent, confidence))
        return results

# =====================================================
# FUNCIONES DE UTILIDAD
# =====================================================

def test_classifier():
    """Función de prueba mejorada"""
    print("=" * 70)
    print("🧪 TEST DEL CLASIFICADOR LLM MEJORADO")
    print("=" * 70)
    print()
    
    classifier = LLMIntentClassifier()
    
    if not classifier.available:
        print("❌ LM Studio no está disponible")
        print("⚠️ Usando solo clasificación por keywords")
        print()
    
    test_cases = [
        "hola",
        "quiero sacar un turno",
        "kmiero un turno",
        "q horarios ai",
        "mi nombre es Juan Perez",
        "1234567",
        "para mañana",
        "a las 10",
        "confirmo",
        "donde queda la oficina",
        "cuanto cuesta",
        "que requisitos necesito",
        "cuanto voy a esperar",
        "recomendame un horario",
        "lo mas temprano posible",
        "chau"
    ]
    
    print("📋 Probando casos de prueba:\n")
    
    correctos = 0
    total = len(test_cases)
    
    for i, message in enumerate(test_cases, 1):
        intent, confidence = classifier.classify_intent(message)
        
        # Determinar si es correcto (heurística simple)
        correcto = intent != "nlu_fallback"
        if correcto:
            correctos += 1
            emoji = "✅"
        else:
            emoji = "❌"
        
        print(f"{emoji} {i}. '{message}'")
        print(f"   → {intent} (confianza: {confidence:.2f})")
        print()
    
    print("=" * 70)
    accuracy = (correctos / total) * 100
    print(f"✅ Test completado: {correctos}/{total} correctos ({accuracy:.1f}%)")
    print()
    
    if accuracy < 70:
        print("⚠️ Precisión baja. Recomendaciones:")
        print("   1. Verifica que LM Studio esté corriendo")
        print("   2. Prueba con un modelo más grande (ej: llama-3.2-3b)")
        print("   3. Ajusta la temperatura a 0.0 para más determinismo")

if __name__ == "__main__":
    test_classifier()