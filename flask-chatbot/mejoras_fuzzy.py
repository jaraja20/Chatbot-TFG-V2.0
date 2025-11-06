"""
Mejoras al Motor Difuso:
1. Corrección ortográfica con FuzzyWuzzy
2. Detección de oraciones compuestas
3. Priorización por contexto
"""

import re
from typing import Dict, List, Tuple, Optional
from fuzzywuzzy import fuzz, process

# =====================================================
# MEJORA 1: CORRECCIÓN ORTOGRÁFICA
# =====================================================

class CorrectOrOrtografico:
    """
    Corrige errores ortográficos usando distancia de edición (Levenshtein)
    """
    
    def __init__(self):
        # Diccionario de palabras clave del sistema
        self.diccionario_base = [
            # Verbos comunes
            'quiero', 'necesito', 'puedo', 'tengo', 'debo', 'quisiera', 'podria', 
            'gustaria', 'hay', 'tienen', 'estan', 'quedan', 'cobran', 'sale', 'cuesta',
            'llevar', 'traer', 'presentar', 'sacar', 'agendar', 'reservar', 'marcar',
            'cancelar', 'confirmo', 'acepto',
            
            # Sustantivos
            'turno', 'cita', 'hora', 'dia', 'horario', 'fecha', 'semana', 'lunes', 'martes',
            'miercoles', 'jueves', 'viernes', 'sabado', 'domingo', 'mañana', 'tarde',
            'cedula', 'documento', 'documentos', 'papel', 'papeles', 'requisito', 'requisitos',
            'tramite', 'tramites', 'servicio', 'servicios',
            'precio', 'costo', 'vale', 'sale', 'dinero', 'plata',
            'ubicacion', 'direccion', 'telefono', 'contacto', 'oficina', 'lugar',
            'disponibilidad', 'perfecto', 'tambien', 'ahora',
            
            # Interrogativos
            'cuando', 'donde', 'como', 'cuanto', 'que', 'cual', 'quien',
            
            # Adjetivos/Adverbios
            'urgente', 'rapido', 'pronto', 'temprano', 'disponible', 'libre', 'gratis',
            'gratuito', 'mejor', 'intermedio', 'apurado',
            
            # Conectores (importantes para oraciones compuestas)
            'pero', 'entonces', 'porque', 'ademas', 'tambien', 'solo', 'aunque',
        ]
        
        # Mapeo de errores comunes conocidos
        self.correcciones_manuales = {
            'kiero': 'quiero',
            'nesecito': 'necesito',
            'nesesito': 'necesito',
            'bale': 'vale',
            'ba': 'va',
            'aser': 'hacer',
            'aya': 'haya',
            'serca': 'cerca',
            'ubiacion': 'ubicacion',
            'telofono': 'telefono',
            'haser': 'hacer',
            'ay': 'hay',
            'ahy': 'hay',
            'ahi': 'hay',
            'hoy': 'hoy',
            'oi': 'hoy',
            'aora': 'ahora',
            'k': 'que',
            'q': 'que',
            'ke': 'que',
            'xq': 'porque',
            'xk': 'porque',
            'xfa': 'favor',
            'xfavor': 'favor',
            'tmb': 'tambien',
            'tb': 'tambien',
            'bn': 'bien',
            'rekisitos': 'requisitos',
            'disponivilidad': 'disponibilidad',
            'cosultar': 'consultar',
            'presio': 'precio',
            'dokumentos': 'documentos',
            'perfekto': 'perfecto',
            'konfirmo': 'confirmo',
            'kuando': 'cuando',
            'ajendarme': 'agendar',
        }
    
    def corregir_palabra(self, palabra: str, umbral: int = 80) -> str:
        """
        Corrige una palabra usando distancia de Levenshtein.
        
        Args:
            palabra: Palabra a corregir
            umbral: Umbral de similitud (0-100)
        
        Returns:
            Palabra corregida o la original si no hay match
        """
        palabra_lower = palabra.lower()
        
        # 1. Revisar correcciones manuales primero
        if palabra_lower in self.correcciones_manuales:
            return self.correcciones_manuales[palabra_lower]
        
        # 2. Si la palabra está en el diccionario, no corregir
        if palabra_lower in self.diccionario_base:
            return palabra
        
        # 3. Buscar la palabra más similar
        resultado = process.extractOne(
            palabra_lower, 
            self.diccionario_base,
            scorer=fuzz.ratio
        )
        
        if resultado and resultado[1] >= umbral:
            palabra_corregida = resultado[0]
            return palabra_corregida
        
        # 4. Si no hay match, devolver original
        return palabra
    
    def corregir_mensaje(self, mensaje: str, umbral: int = 75) -> Tuple[str, List[str]]:
        """
        Corrige todas las palabras de un mensaje.
        
        Args:
            mensaje: Mensaje a corregir
            umbral: Umbral de similitud
        
        Returns:
            (mensaje_corregido, lista_de_correcciones)
        """
        palabras = mensaje.split()
        palabras_corregidas = []
        correcciones = []
        
        for palabra in palabras:
            # Preservar puntuación
            puntuacion_final = ''
            palabra_limpia = palabra
            
            if palabra and palabra[-1] in '.,;:!?':
                puntuacion_final = palabra[-1]
                palabra_limpia = palabra[:-1]
            
            palabra_corregida = self.corregir_palabra(palabra_limpia, umbral)
            
            if palabra_corregida != palabra_limpia.lower():
                correcciones.append(f"{palabra_limpia} → {palabra_corregida}")
            
            palabras_corregidas.append(palabra_corregida + puntuacion_final)
        
        mensaje_corregido = ' '.join(palabras_corregidas)
        
        return mensaje_corregido, correcciones


# =====================================================
# MEJORA 2: DETECCIÓN DE ORACIONES COMPUESTAS
# =====================================================

class DetectorOracionesCompuestas:
    """
    Detecta y procesa oraciones compuestas con múltiples intents
    """
    
    def __init__(self):
        # Patrones de conectores que indican oraciones compuestas
        self.conectores = [
            r'\s+y\s+',           # "cuanto cuesta y que documentos"
            r'\s*,\s*',           # "hola, quiero turno"
            r'\s+pero\s+',        # "quiero turno pero solo tarde"
            r'\s+entonces\s+',    # "bueno, entonces cuando hay"
            r'\s+ademas\s+',      # "necesito saber ademas donde"
            r'\s+tambien\s+',     # "quiero saber tambien cuando"
        ]
        
        # Patrones de priorización por palabra inicial
        self.patrones_prioritarios = {
            'consultar_costo': [
                r'^(cuanto|cuánto|precio|costo|vale|bale|sale)',
                r'(caro|barato|cuesta|cobran|pagar|plata|dinero)',
            ],
            'consultar_disponibilidad': [
                r'^(cuando|cuándo|que dia|que hora|horarios)',
                r'(hoy|mañana|manana|lunes|martes|miercoles|jueves|viernes)',
                r'(disponible|hueco|libre|lugar|atienden|cierran|abren|abiertos)',
                r'(puedo.*hoy|puedo.*mañana|cuando.*puedo)',
            ],
            'consultar_requisitos': [
                r'^(que necesito|que documentos|requisitos|papeles|que.*requisitos)',
                r'(llevar|traer|presentar|documentos|papeles)',
                r'(que necesito|que.*llevar)',
            ],
            'consultar_ubicacion': [
                r'^(donde|dónde|como llego|ubicacion)',
                r'(llegar|quedan|ubicacion|direccion)',
                r'(como.*llegar|como.*para llegar|como hago)',
            ],
            'agendar_turno': [
                r'^(quiero|kiero|necesito|nesecito).*(turno|cita)',
                r'(sacar turno|agendar|reservar|marcar)',
            ],
            'consultar_tramites': [
                r'(tramites|servicios|ofrecen|hacen)',
            ],
        }
    
    def es_oracion_compuesta(self, mensaje: str) -> bool:
        """
        Detecta si un mensaje es una oración compuesta.
        
        Returns:
            True si contiene múltiples intents
        """
        mensaje_lower = mensaje.lower()
        
        for patron in self.conectores:
            if re.search(patron, mensaje_lower):
                return True
        
        return False
    
    def dividir_oracion(self, mensaje: str) -> List[str]:
        """
        Divide una oración compuesta en fragmentos.
        
        Returns:
            Lista de fragmentos (mínimo 1)
        """
        fragmentos = [mensaje]
        
        # Dividir por cada tipo de conector
        for patron in self.conectores:
            nuevos_fragmentos = []
            for fragmento in fragmentos:
                partes = re.split(patron, fragmento)
                nuevos_fragmentos.extend([p.strip() for p in partes if p.strip()])
            fragmentos = nuevos_fragmentos
        
        return fragmentos
    
    def detectar_intent_prioritario(self, mensaje: str) -> Optional[str]:
        """
        Detecta si hay un intent con prioridad basado en palabras clave iniciales.
        
        Returns:
            Intent prioritario o None
        """
        mensaje_lower = mensaje.lower()
        
        for intent, patrones in self.patrones_prioritarios.items():
            for patron in patrones:
                if re.search(patron, mensaje_lower):
                    return intent
        
        return None


# =====================================================
# MEJORA 3: CLASIFICADOR MEJORADO
# =====================================================

class ClasificadorMejorado:
    """
    Clasificador que integra corrección ortográfica y manejo de oraciones compuestas
    """
    
    def __init__(self, clasificador_base):
        """
        Args:
            clasificador_base: Función clasificar_con_logica_difusa original
        """
        self.clasificador_base = clasificador_base
        self.corrector = CorrectOrOrtografico()
        self.detector_compuestas = DetectorOracionesCompuestas()
    
    def clasificar_mejorado(
        self, 
        mensaje: str, 
        threshold: float = 0.3,
        corregir_ortografia: bool = True,
        manejar_compuestas: bool = True
    ) -> Tuple[str, float, Dict]:
        """
        Clasificación mejorada con corrección ortográfica y oraciones compuestas.
        
        Returns:
            (intent, confianza, metadata)
            metadata contiene: {
                'mensaje_original': str,
                'mensaje_corregido': str,
                'correcciones': List[str],
                'es_compuesta': bool,
                'fragmentos': List[str],
                'intent_prioritario': Optional[str]
            }
        """
        metadata = {
            'mensaje_original': mensaje,
            'mensaje_corregido': mensaje,
            'correcciones': [],
            'es_compuesta': False,
            'fragmentos': [mensaje],
            'intent_prioritario': None,
            'metodo_usado': 'clasificacion_simple'
        }
        
        mensaje_procesado = mensaje
        
        # PASO 1: Corrección ortográfica
        if corregir_ortografia:
            mensaje_corregido, correcciones = self.corrector.corregir_mensaje(mensaje)
            if correcciones:
                metadata['correcciones'] = correcciones
                metadata['mensaje_corregido'] = mensaje_corregido
                mensaje_procesado = mensaje_corregido
        
        # PASO 2: Detección de oraciones compuestas
        if manejar_compuestas and self.detector_compuestas.es_oracion_compuesta(mensaje_procesado):
            metadata['es_compuesta'] = True
            fragmentos = self.detector_compuestas.dividir_oracion(mensaje_procesado)
            metadata['fragmentos'] = fragmentos
            
            # PASO 2A: Verificar si hay intent prioritario (por palabra inicial)
            intent_prioritario = self.detector_compuestas.detectar_intent_prioritario(mensaje_procesado)
            
            if intent_prioritario:
                # Si hay palabra clave prioritaria, usar ese intent directamente
                metadata['intent_prioritario'] = intent_prioritario
                metadata['metodo_usado'] = 'priorizacion_contextual'
                intent, conf = self.clasificador_base(mensaje_procesado, threshold)
                
                # Si el intent detectado coincide con el prioritario, boost de confianza
                if intent == intent_prioritario:
                    conf = min(conf * 1.3, 1.0)  # Boost 30%
                else:
                    # Forzar el intent prioritario si la palabra clave es muy clara
                    intent = intent_prioritario
                    conf = 0.75
                
                return intent, conf, metadata
            
            # PASO 2B: Clasificar cada fragmento y tomar el de mayor confianza
            resultados = []
            for fragmento in fragmentos:
                if len(fragmento.split()) >= 2:  # Solo fragmentos con al menos 2 palabras
                    intent_frag, conf_frag = self.clasificador_base(fragmento, threshold)
                    resultados.append((intent_frag, conf_frag, fragmento))
            
            if resultados:
                # Tomar el fragmento con mayor confianza
                mejor_resultado = max(resultados, key=lambda x: x[1])
                metadata['metodo_usado'] = 'fragmentacion_multiple'
                return mejor_resultado[0], mejor_resultado[1], metadata
        
        # PASO 3: Clasificación normal (simple)
        intent, conf = self.clasificador_base(mensaje_procesado, threshold)
        
        return intent, conf, metadata


# =====================================================
# FUNCIÓN DE INTEGRACIÓN
# =====================================================

def crear_clasificador_mejorado(clasificador_base):
    """
    Factory para crear el clasificador mejorado.
    
    Usage:
        from razonamiento_difuso import clasificar_con_logica_difusa
        from mejoras_fuzzy import crear_clasificador_mejorado
        
        clasificador = crear_clasificador_mejorado(clasificar_con_logica_difusa)
        intent, conf, metadata = clasificador.clasificar_mejorado("kiero un turno")
    """
    return ClasificadorMejorado(clasificador_base)


# =====================================================
# TESTS
# =====================================================

if __name__ == "__main__":
    print("="*80)
    print("🧪 TESTS DE MEJORAS AL MOTOR DIFUSO")
    print("="*80)
    
    # TEST 1: Corrección Ortográfica
    print("\n" + "="*80)
    print("TEST 1: CORRECCIÓN ORTOGRÁFICA")
    print("="*80)
    
    corrector = CorrectOrOrtografico()
    
    test_ortografia = [
        "kiero un turno",
        "nesecito saber cuanto bale",
        "k documentos tengo q llevar",
        "ay turnos para oi?",
        "ubiacion de la oficina",
    ]
    
    for mensaje in test_ortografia:
        corregido, correcciones = corrector.corregir_mensaje(mensaje)
        print(f"\n❌ Original:   '{mensaje}'")
        print(f"✅ Corregido:  '{corregido}'")
        if correcciones:
            print(f"   Cambios: {', '.join(correcciones)}")
    
    # TEST 2: Detección de Oraciones Compuestas
    print("\n" + "="*80)
    print("TEST 2: DETECCIÓN DE ORACIONES COMPUESTAS")
    print("="*80)
    
    detector = DetectorOracionesCompuestas()
    
    test_compuestas = [
        "cuanto cuesta y que documentos necesito?",
        "hola, quiero un turno para mañana",
        "necesito turno pero solo puedo por la tarde",
        "cuando hay disponible y donde quedan?",
    ]
    
    for mensaje in test_compuestas:
        es_compuesta = detector.es_oracion_compuesta(mensaje)
        fragmentos = detector.dividir_oracion(mensaje)
        prioritario = detector.detectar_intent_prioritario(mensaje)
        
        print(f"\n📝 '{mensaje}'")
        print(f"   Compuesta: {es_compuesta}")
        print(f"   Fragmentos: {fragmentos}")
        print(f"   Intent prioritario: {prioritario}")
    
    print("\n" + "="*80)
    print("✅ Tests completados")
    print("="*80)
